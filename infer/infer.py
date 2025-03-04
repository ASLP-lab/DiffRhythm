# Copyright (c) 2025 ASLP-LAB
#               2025 Huakang Chen  (huakang@mail.nwpu.edu.cn)
#               2025 Guobin Ma     (guobin.ma@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import torchaudio
from einops import rearrange
import argparse
import os
import time

import os
print("Current working directory:", os.getcwd())

from infer_utils import (
    get_reference_latent,
    get_lrc_token,
    get_style_prompt,
    prepare_model,
    get_negative_style_prompt,
    decode_audio
)

def inference(cfm_model, vae_model, cond, text, duration, style_prompt, negative_style_prompt, start_time):
    with torch.inference_mode():
        generated, _ = cfm_model.sample(
            cond=cond,
            text=text,
            duration=duration,
            style_prompt=style_prompt,
            negative_style_prompt=negative_style_prompt,
            steps=32,
            cfg_strength=4.0,
            start_time=start_time
        )
        
        generated = generated.to(torch.float32)
        latent = generated.transpose(1, 2) # [b d t]
    
        output = decode_audio(latent, vae_model, chunked=False)

        # Rearrange audio batch to a single sequence
        output = rearrange(output, "b d n -> d (b n)")
        # Peak normalize, clip, convert to int16, and save to file
        output = output.to(torch.float32).div(torch.max(torch.abs(output))).clamp(-1, 1).mul(32767).to(torch.int16).cpu()
        
        return output
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--lrc-path', type=str, default="infer/example/eg.lrc") # lyrics of target song
    parser.add_argument('--ref-audio-path', type=str, default="infer/example/eg.mp3") # reference audio as style prompt for target song
    parser.add_argument('--audio-length', type=int, default=95) # length of target song
    parser.add_argument('--output-dir', type=str, default="infer/example/output") # output directory fo target song
    args = parser.parse_args()
    
    device = 'cuda'
    
    audio_length = args.audio_length
    if audio_length == 95:
        max_frames = 2048
    elif audio_length == 285:
        max_frames = 6144
    
    cfm, tokenizer, muq, vae = prepare_model(device)
    
    with open(args.lrc_path, 'r') as f:
        lrc = f.read()
    lrc_prompt, start_time = get_lrc_token(lrc, tokenizer, device)
    
    style_prompt = get_style_prompt(muq, args.ref_audio_path)
    
    negative_style_prompt = get_negative_style_prompt(device)
    
    latent_prompt = get_reference_latent(device, max_frames)
    
    s_t = time.time()
    generated_song = inference(cfm_model=cfm, 
                               vae_model=vae, 
                               cond=latent_prompt, 
                               text=lrc_prompt, 
                               duration=max_frames, 
                               style_prompt=style_prompt,
                               negative_style_prompt=negative_style_prompt,
                               start_time=start_time
                               )
    e_t = time.time() - s_t
    print(f"inference cost {e_t} seconds")
    
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "output.wav")
    torchaudio.save(output_path, generated_song, sample_rate=44100)
    