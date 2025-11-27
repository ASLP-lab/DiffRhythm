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
import random
from datetime import datetime

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
    pred_frames,
    batch_infer_num,
    song_duration,
    chunked=False,
):
    with torch.inference_mode():
        latents, _ = cfm_model.sample(
            cond=cond,
            text=text,
            duration=duration,
            style_prompt=style_prompt,
            max_duration=duration,
            song_duration=song_duration, 
            negative_style_prompt=negative_style_prompt,
            steps=32,
            cfg_strength=4.0,
            start_time=start_time,
            latent_pred_segments=pred_frames,
            batch_infer_num=batch_infer_num
        )

        outputs = []
        for latent in latents:
            latent = latent.to(torch.float32)
            latent = latent.transpose(1, 2)  # [b d t]

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
            outputs.append(output)

        return outputs


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
        # choices=[95, 285],
        help="length of generated song, upported values are exactly 95 or any value between 96 and 285 (inclusive).",
    )  # length of target song
    # parser.add_argument(
    #     "--repo-id", type=str, default="ASLP-lab/DiffRhythm-base", help="target model"
    # )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="infer/example/output",
        help="output directory fo generated song",
    )  # output directory of target song
    parser.add_argument(
        "--edit",
        action="store_true",
        help="whether to open edit mode",
    )  # edit flag
    parser.add_argument(
        "--ref-song",
        type=str,
        required=False,
        help="reference prompt as latent prompt for editing",
    )  # reference prompt as latent prompt for editing
    parser.add_argument(
        "--edit-segments",
        type=str,
        required=False,
        help="Time segments to edit (in seconds). Format: `[[start1,end1],...]`. "
             "Use `-1` for audio start/end (e.g., `[[-1,25], [50.0,-1]]`)."
    )  # edit segments of target song
    parser.add_argument(
        "--batch-infer-num",
        type=int,
        default=1,
        required=False,
        help="number of songs per batch",
    )  # number of songs per batch
    args = parser.parse_args()

    assert (
        args.ref_prompt or args.ref_audio_path
    ), "either ref_prompt or ref_audio_path should be provided"
    assert not (
        args.ref_prompt and args.ref_audio_path
    ), "only one of them should be provided"
    if args.edit:
        assert (
            args.ref_song and args.edit_segments
        ), "reference song and edit segments should be provided for editing"

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.mps.is_available():
        device = "mps"

    audio_length = args.audio_length
    if audio_length == 95:
        max_frames = 2048
    elif 95 < audio_length <= 285:
        max_frames = 6144
    else:
        raise ValueError(
            f"Invalid audio_length: {audio_length}. "
            "Supported values are exactly 95 or any value between 96 and 285 (inclusive)."
        )

    cfm, tokenizer, muq, vae = prepare_model(max_frames, device)

    if args.lrc_path:
        with open(args.lrc_path, "r", encoding='utf-8') as f:
            lrc = f.read()
    else:
        lrc = ""
    lrc_prompt, start_time, end_frame, song_duration = get_lrc_token(max_frames, lrc, tokenizer, audio_length, device)

    if args.ref_audio_path:
        style_prompt = get_style_prompt(muq, args.ref_audio_path)
    else:
        style_prompt = get_style_prompt(muq, prompt=args.ref_prompt)

    negative_style_prompt = get_negative_style_prompt(device)

    latent_prompt, pred_frames = get_reference_latent(device, max_frames, args.edit, args.edit_segments, args.ref_song, vae)

    s_t = time.time()
    generated_songs = inference(
        cfm_model=cfm,
        vae_model=vae,
        cond=latent_prompt,
        text=lrc_prompt,
        duration=end_frame,
        style_prompt=style_prompt,
        negative_style_prompt=negative_style_prompt,
        start_time=start_time,
        pred_frames=pred_frames,
        chunked=args.chunked,
        batch_infer_num=args.batch_infer_num,
        song_duration=song_duration
    )
    e_t = time.time() - s_t
    print(f"inference cost {e_t:.2f} seconds")
    
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # 循环遍历所有生成的歌曲并保存
    for idx, generated_song in enumerate(generated_songs):
        # 生成基于当前时间的文件名：年月日-时分秒-毫秒-序号.wav
        current_time = datetime.now()
        timestamp = current_time.strftime("%Y%m%d-%H%M%S")
        millisecond = current_time.microsecond // 1000
        filename = f"{timestamp}-{millisecond:03d}-{idx+1:02d}.wav"
        
        output_path = os.path.join(output_dir, filename)
        torchaudio.save(output_path, generated_song, sample_rate=44100)
        print(f"Generated song saved to: {output_path}")
