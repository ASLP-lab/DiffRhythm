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

import argparse
import os
import time

import torch
import torchaudio
from einops import rearrange

print("Current working directory:", os.getcwd())

from infer_utils import (
    decode_audio,
    get_lrc_token,
    get_negative_style_prompt,
    get_reference_latent,
    get_style_prompt,
    prepare_model,
)


def inference(
    cfm_model,
    vae_model,
    cond,
    text,
    duration,
    style_prompt,
    negative_style_prompt,
    start_time,
    chunked=False,
):
    with torch.inference_mode():
        generated, _ = cfm_model.sample(
            cond=cond,
            text=text,
            duration=duration,
            style_prompt=style_prompt,
            negative_style_prompt=negative_style_prompt,
            steps=32,
            cfg_strength=4.0,
            start_time=start_time,
        )

        generated = generated.to(torch.float32)
        latent = generated.transpose(1, 2)  # [b d t]

        output = decode_audio(latent, vae_model, chunked=chunked)

        # Rearrange audio batch to a single sequence
        output = rearrange(output, "b d n -> d (b n)")
        # Peak normalize, clip, convert to int16, and save to file
        output = (
            output.to(torch.float32)
            .div(torch.max(torch.abs(output)))
            .clamp(-1, 1)
            .mul(32767)
            .to(torch.int16)
            .cpu()
        )

        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lrc-path",
        type=str,
        help="lyrics of target song",
    )  # lyrics of target song
    parser.add_argument(
        "--ref-prompt",
        type=str,
        help="reference prompt as style prompt for target song",
        required=False,
    )  # reference prompt as style prompt for target song
    parser.add_argument(
        "--ref-audio-path",
        type=str,
        help="reference audio as style prompt for target song",
        required=False,
    )  # reference audio as style prompt for target song
    parser.add_argument(
        "--chunked",
        action="store_true",
        help="whether to use chunked decoding",
    )  # whether to use chunked decoding
    parser.add_argument(
        "--audio-length",
        type=int,
        default=95,
        choices=[95],
        help="length of generated song",
    )  # length of target song
    parser.add_argument(
        "--repo_id", type=str, default="ASLP-lab/DiffRhythm-base", help="target model"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="infer/example/output",
        help="output directory fo generated song",
    )  # output directory fo target song
    args = parser.parse_args()

    assert (
        args.ref_prompt or args.ref_audio_path
    ), "either ref_prompt or ref_audio_path should be provided"
    assert not (
        args.ref_prompt and args.ref_audio_path
    ), "only one of them should be provided"

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.mps.is_available():
        device = "mps"

    audio_length = args.audio_length
    if audio_length == 95:
        max_frames = 2048
    elif audio_length == 285:  # current not available
        max_frames = 6144

    cfm, tokenizer, muq, vae = prepare_model(device)

    if args.lrc_path:
        with open(args.lrc_path, "r", encoding='utf-8') as f:
            lrc = f.read()
    else:
        lrc = ""
    lrc_prompt, start_time = get_lrc_token(lrc, tokenizer, device)

    if args.ref_audio_path:
        style_prompt = get_style_prompt(muq, args.ref_audio_path)
    else:
        style_prompt = get_style_prompt(muq, prompt=args.ref_prompt)

    negative_style_prompt = get_negative_style_prompt(device)

    latent_prompt = get_reference_latent(device, max_frames)

    s_t = time.time()
    generated_song = inference(
        cfm_model=cfm,
        vae_model=vae,
        cond=latent_prompt,
        text=lrc_prompt,
        duration=max_frames,
        style_prompt=style_prompt,
        negative_style_prompt=negative_style_prompt,
        start_time=start_time,
        chunked=args.chunked,
    )
    e_t = time.time() - s_t
    print(f"inference cost {e_t} seconds")

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "output.wav")
    torchaudio.save(output_path, generated_song, sample_rate=44100)
