# Copyright (c) 2025 ASLP-LAB
#               2025 Huakang Chen  (huakang@mail.nwpu.edu.cn)
#               2025 Guobin Ma     (guobin.ma@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import librosa
import random
import json
from muq import MuQMuLan
from mutagen.mp3 import MP3
import os
import numpy as np
from huggingface_hub import hf_hub_download

from sys import path
path.append(os.getcwd())

from model import DiT, CFM


def decode_audio(latents, vae_model, chunked=False, overlap=32, chunk_size=128):
    downsampling_ratio = 2048
    io_channels = 2
    if not chunked:
        return vae_model.decode_export(latents)
    else:
        # chunked decoding
        hop_size = chunk_size - overlap
        total_size = latents.shape[2]
        batch_size = latents.shape[0]
        chunks = []
        i = 0
        for i in range(0, total_size - chunk_size + 1, hop_size):
            chunk = latents[:, :, i : i + chunk_size]
            chunks.append(chunk)
        if i + chunk_size != total_size:
            # Final chunk
            chunk = latents[:, :, -chunk_size:]
            chunks.append(chunk)
        chunks = torch.stack(chunks)
        num_chunks = chunks.shape[0]
        # samples_per_latent is just the downsampling ratio
        samples_per_latent = downsampling_ratio
        # Create an empty waveform, we will populate it with chunks as decode them
        y_size = total_size * samples_per_latent
        y_final = torch.zeros((batch_size, io_channels, y_size)).to(latents.device)
        for i in range(num_chunks):
            x_chunk = chunks[i, :]
            # decode the chunk
            y_chunk = vae_model.decode_export(x_chunk)
            # figure out where to put the audio along the time domain
            if i == num_chunks - 1:
                # final chunk always goes at the end
                t_end = y_size
                t_start = t_end - y_chunk.shape[2]
            else:
                t_start = i * hop_size * samples_per_latent
                t_end = t_start + chunk_size * samples_per_latent
            #  remove the edges of the overlaps
            ol = (overlap // 2) * samples_per_latent
            chunk_start = 0
            chunk_end = y_chunk.shape[2]
            if i > 0:
                # no overlap for the start of the first chunk
                t_start += ol
                chunk_start += ol
            if i < num_chunks - 1:
                # no overlap for the end of the last chunk
                t_end -= ol
                chunk_end -= ol
            # paste the chunked audio into our y_final output audio
            y_final[:, :, t_start:t_end] = y_chunk[:, :, chunk_start:chunk_end]
        return y_final


def prepare_model(device, repo_id="ASLP-lab/DiffRhythm-base"):
    # prepare cfm model
    dit_ckpt_path = hf_hub_download(
        repo_id=repo_id, filename="cfm_model.pt", cache_dir="./pretrained"
    )
    dit_config_path = "./config/diffrhythm-1b.json"
    with open(dit_config_path) as f:
        model_config = json.load(f)
    dit_model_cls = DiT
    cfm = CFM(
        transformer=dit_model_cls(**model_config["model"]),
        num_channels=model_config["model"]["mel_dim"],
    )
    cfm = cfm.to(device)
    cfm = load_checkpoint(cfm, dit_ckpt_path, device=device, use_ema=False)

    # prepare tokenizer
    tokenizer = CNENTokenizer()

    # prepare muq
    muq = MuQMuLan.from_pretrained("OpenMuQ/MuQ-MuLan-large", cache_dir="./pretrained")
    muq = muq.to(device).eval()

    # prepare vae
    vae_ckpt_path = hf_hub_download(
        repo_id="ASLP-lab/DiffRhythm-vae",
        filename="vae_model.pt",
        cache_dir="./pretrained",
    )
    vae = torch.jit.load(vae_ckpt_path, map_location="cpu").to(device)

    return cfm, tokenizer, muq, vae


# for song edit, will be added in the future
def get_reference_latent(device, max_frames):
    return torch.zeros(1, max_frames, 64).to(device)


def get_negative_style_prompt(device):
    file_path = "infer/example/vocal.npy"
    vocal_stlye = np.load(file_path)

    vocal_stlye = torch.from_numpy(vocal_stlye).to(device)  # [1, 512]
    vocal_stlye = vocal_stlye.half()

    return vocal_stlye


@torch.no_grad()
def get_style_prompt(model, wav_path=None, prompt=None):
    mulan = model

    if prompt is not None:
        return mulan(texts=prompt).half()

    ext = os.path.splitext(wav_path)[-1].lower()
    if ext == ".mp3":
        meta = MP3(wav_path)
        audio_len = meta.info.length
    elif ext in [".wav", ".flac"]:
        audio_len = librosa.get_duration(path=wav_path)
    else:
        raise ValueError("Unsupported file format: {}".format(ext))

    if audio_len < 10:
        print(
            f"Warning: The audio file {wav_path} is too short ({audio_len:.2f} seconds). Expected at least 10 seconds."
        )

    assert audio_len >= 10

    mid_time = audio_len // 2
    start_time = mid_time - 5
    wav, _ = librosa.load(wav_path, sr=24000, offset=start_time, duration=10)

    wav = torch.tensor(wav).unsqueeze(0).to(model.device)

    with torch.no_grad():
        audio_emb = mulan(wavs=wav)  # [1, 512]

    audio_emb = audio_emb
    audio_emb = audio_emb.half()

    return audio_emb


def parse_lyrics(lyrics: str):
    lyrics_with_time = []
    lyrics = lyrics.strip()
    for line in lyrics.split("\n"):
        try:
            time, lyric = line[1:9], line[10:]
            lyric = lyric.strip()
            mins, secs = time.split(":")
            secs = int(mins) * 60 + float(secs)
            lyrics_with_time.append((secs, lyric))
        except:
            continue
    return lyrics_with_time


class CNENTokenizer:
    def __init__(self):
        with open("./g2p/g2p/vocab.json", "r", encoding='utf-8') as file:
            self.phone2id: dict = json.load(file)["vocab"]
        self.id2phone = {v: k for (k, v) in self.phone2id.items()}
        from g2p.g2p_generation import chn_eng_g2p

        self.tokenizer = chn_eng_g2p

    def encode(self, text):
        phone, token = self.tokenizer(text)
        token = [x + 1 for x in token]
        return token

    def decode(self, token):
        return "|".join([self.id2phone[x - 1] for x in token])


def get_lrc_token(text, tokenizer, device):

    max_frames = 2048
    lyrics_shift = 0
    sampling_rate = 44100
    downsample_rate = 2048
    max_secs = max_frames / (sampling_rate / downsample_rate)

    comma_token_id = 1
    period_token_id = 2

    lrc_with_time = parse_lyrics(text)

    modified_lrc_with_time = []
    for i in range(len(lrc_with_time)):
        time, line = lrc_with_time[i]
        line_token = tokenizer.encode(line)
        modified_lrc_with_time.append((time, line_token))
    lrc_with_time = modified_lrc_with_time

    lrc_with_time = [
        (time_start, line)
        for (time_start, line) in lrc_with_time
        if time_start < max_secs
    ]
    lrc_with_time = lrc_with_time[:-1] if len(lrc_with_time) >= 1 else lrc_with_time

    normalized_start_time = 0.0

    lrc = torch.zeros((max_frames,), dtype=torch.long)

    tokens_count = 0
    last_end_pos = 0
    for time_start, line in lrc_with_time:
        tokens = [
            token if token != period_token_id else comma_token_id for token in line
        ] + [period_token_id]
        tokens = torch.tensor(tokens, dtype=torch.long)
        num_tokens = tokens.shape[0]

        gt_frame_start = int(time_start * sampling_rate / downsample_rate)

        frame_shift = random.randint(int(lyrics_shift), int(lyrics_shift))

        frame_start = max(gt_frame_start - frame_shift, last_end_pos)
        frame_len = min(num_tokens, max_frames - frame_start)

        lrc[frame_start : frame_start + frame_len] = tokens[:frame_len]

        tokens_count += num_tokens
        last_end_pos = frame_start + frame_len

    lrc_emb = lrc.unsqueeze(0).to(device)

    normalized_start_time = torch.tensor(normalized_start_time).unsqueeze(0).to(device)
    normalized_start_time = normalized_start_time.half()

    return lrc_emb, normalized_start_time


def load_checkpoint(model, ckpt_path, device, use_ema=True):
    model = model.half()

    ckpt_type = ckpt_path.split(".")[-1]
    if ckpt_type == "safetensors":
        from safetensors.torch import load_file

        checkpoint = load_file(ckpt_path)
    else:
        checkpoint = torch.load(ckpt_path, weights_only=True)

    if use_ema:
        if ckpt_type == "safetensors":
            checkpoint = {"ema_model_state_dict": checkpoint}
        checkpoint["model_state_dict"] = {
            k.replace("ema_model.", ""): v
            for k, v in checkpoint["ema_model_state_dict"].items()
            if k not in ["initted", "step"]
        }
        model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    else:
        if ckpt_type == "safetensors":
            checkpoint = {"model_state_dict": checkpoint}
        model.load_state_dict(checkpoint["model_state_dict"], strict=False)

    return model.to(device)
