# This file should be located at: DiffRhythm/gradio/app.py

import gradio as gr
from openai import OpenAI
import requests
import json
# from volcenginesdkarkruntime import Ark
import torch
import torchaudio
from einops import rearrange
import argparse
import json
import os
import spaces # Make sure 'spaces' is importable if needed for decorators
from tqdm import tqdm
import random
import numpy as np
import sys

# Assuming the 'diffrhythm' package is installed or the project root is in PYTHONPATH
# If running 'python gradio/app.py' from the project root, these should work.
from diffrhythm.infer.infer_utils import (
    get_reference_latent,
    get_lrc_token,
    get_audio_style_prompt,
    get_text_style_prompt,
    prepare_model,
    get_negative_style_prompt
)
from diffrhythm.infer.infer import inference

MAX_SEED = np.iinfo(np.int32).max
device='cuda' # Or dynamically detect
# Ensure prepare_model finds models correctly - it likely uses paths relative to its own location.
cfm, cfm_full, tokenizer, muq, vae = prepare_model(device)
# Consider compiling only if performance boost is needed and stable
# cfm = torch.compile(cfm)
# cfm_full = torch.compile(cfm_full)

# Decorator requires spaces library if running on Hugging Face Spaces
# Remove or comment out if running locally without the library or needing the decorator functionality
# @spaces.GPU(duration=40)
def infer_music(lrc, ref_audio_path, text_prompt, current_prompt_type, seed=42, randomize_seed=False, steps=32, cfg_strength=4.0, file_type='wav', odeint_method='euler', Music_Duration='95s', device='cuda'):
    if Music_Duration == '95s':
        max_frames = 2048
        cfm_model = cfm
    else:
        max_frames = 6144
        cfm_model = cfm_full
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    torch.manual_seed(seed)
    sway_sampling_coef = -1 if steps < 32 else None
    vocal_flag = False
    try:
        lrc_prompt, start_time = get_lrc_token(max_frames, lrc, tokenizer, device)
        if current_prompt_type == 'audio':
            style_prompt, vocal_flag = get_audio_style_prompt(muq, ref_audio_path)
        else:
            style_prompt = get_text_style_prompt(muq, text_prompt)
    except Exception as e:
        raise gr.Error(f"Error parsing inputs: {str(e)}") # More specific error if possible

    negative_style_prompt = get_negative_style_prompt(device)
    latent_prompt = get_reference_latent(device, max_frames)

    try:
        generated_song = inference(cfm_model=cfm_model,
                                   vae_model=vae,
                                   cond=latent_prompt,
                                   text=lrc_prompt,
                                   duration=max_frames,
                                   style_prompt=style_prompt,
                                   negative_style_prompt=negative_style_prompt,
                                   steps=steps,
                                   cfg_strength=cfg_strength,
                                   sway_sampling_coef=sway_sampling_coef,
                                   start_time=start_time,
                                   file_type=file_type,
                                   vocal_flag=vocal_flag,
                                   odeint_method=odeint_method,
                                   )
    except Exception as e:
         raise gr.Error(f"Error during inference: {str(e)}") # More specific error if possible

    return generated_song

# Function for OpenAI API call - Method 1
def R1_infer1(theme, tags_gen, language):
    try:
        # Ensure API key environment variable is set
        api_key = os.getenv('HS_DP_API')
        if not api_key:
            raise gr.Error("OpenAI API Key (HS_DP_API) not found in environment variables.")

        client = OpenAI(api_key=api_key, base_url = "https://ark.cn-beijing.volces.com/api/v3")

        llm_prompt = """
        请围绕"{theme}"主题生成一首符合"{tags}"风格的语言为{language}的完整歌词。严格遵循以下要求：

        ### **强制格式规则**
        1. **仅输出时间戳和歌词**，禁止任何括号、旁白、段落标记（如副歌、间奏、尾奏等注释）。
        2. 每行格式必须为 `[mm:ss.xx]歌词内容`，时间戳与歌词间无空格，歌词内容需完整连贯。
        3. 时间戳需自然分布，**第一句歌词起始时间不得为 [00:00.00]**，需考虑前奏空白。

        ### **内容与结构要求**
        1. 歌词应富有变化，使情绪递进，整体连贯有层次感。**每行歌词长度应自然变化**，切勿长度一致，导致很格式化。
        2. **时间戳分配应根据歌曲的标签、歌词的情感、节奏来合理推测**，而非机械地按照歌词长度分配。
        3. 间奏/尾奏仅通过时间空白体现（如从 [02:30.00] 直接跳至 [02:50.00]），**无需文字描述**。

        ### **负面示例（禁止出现）**
        - 错误：[01:30.00](钢琴间奏)
        - 错误：[02:00.00][副歌]
        - 错误：空行、换行符、注释
        """

        response = client.chat.completions.create(
            model="ep-20250304144033-nr9wl", # Consider making model name configurable
            messages=[
                {"role": "system", "content": "You are a professional musician who has been invited to make music-related comments."},
                {"role": "user", "content": llm_prompt.format(theme=theme, tags=tags_gen, language=language)},
            ],
            stream=False
        )

        info = response.choices[0].message.content
        return info

    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        print(f'Request Exception during Lyrics Generation (Method 1): {e}')
        raise gr.Error(f"Network error during lyrics generation: {e}")
    except Exception as e:
        # Log the error for debugging
        print(f'General Exception during Lyrics Generation (Method 1): {e}')
        raise gr.Error(f"An error occurred during lyrics generation: {e}")


# Function for OpenAI API call - Method 2
def R1_infer2(tags_lyrics, lyrics_input):
    try:
        # Ensure API key environment variable is set
        api_key = os.getenv('HS_DP_API')
        if not api_key:
            raise gr.Error("OpenAI API Key (HS_DP_API) not found in environment variables.")

        client = OpenAI(api_key=api_key, base_url = "https://ark.cn-beijing.volces.com/api/v3")

        llm_prompt = """
        {lyrics_input}这是一首歌的歌词,每一行是一句歌词,{tags_lyrics}是我希望这首歌的风格，我现在想要给这首歌的每一句歌词打时间戳得到LRC，我希望时间戳分配应根据歌曲的标签、歌词的情感、节奏来合理推测，而非机械地按照歌词长度分配。第一句歌词的时间戳应考虑前奏长度，避免歌词从 `[00:00.00]` 直接开始。严格按照 LRC 格式输出歌词，每行格式为 `[mm:ss.xx]歌词内容`。最后的结果只输出LRC,不需要其他的解释。
        """

        response = client.chat.completions.create(
            model="ep-20250304144033-nr9wl", # Consider making model name configurable
            messages=[
                {"role": "system", "content": "You are a professional musician who has been invited to make music-related comments."},
                {"role": "user", "content": llm_prompt.format(lyrics_input=lyrics_input, tags_lyrics=tags_lyrics)},
            ],
            stream=False
        )

        info = response.choices[0].message.content
        return info

    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        print(f'Request Exception during Lyrics Generation (Method 2): {e}')
        raise gr.Error(f"Network error during lyrics generation: {e}")
    except Exception as e:
        # Log the error for debugging
        print(f'General Exception during Lyrics Generation (Method 2): {e}')
        raise gr.Error(f"An error occurred during lyrics generation: {e}")


css = """
/* Fixed text area height and forced scroll bar */
.lyrics-scroll-box textarea {
    height: 405px !important;  /* Fixed height */
    max-height: 500px !important;  /* Max height */
    overflow-y: auto !important;  /* Vertical scroll */
    white-space: pre-wrap;  /* Preserve line breaks */
    line-height: 1.5;  /* Optimize line height */
}

.gr-examples {
    background: transparent !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px;
    margin: 1rem 0 !important;
    padding: 1rem !important;
}

/* Optional: Style for the output LRC box */
.lrc-output textarea {
     height: 600px !important; /* Adjust height as needed */
     overflow-y: auto !important;
     white-space: pre-wrap;
     line-height: 1.5;
}
"""


with gr.Blocks(css=css) as demo:
    # Using a relative path might be fragile if the image moves relative to the project root.
    # Consider using an absolute URL if possible, or ensure the image path is correct relative to root.
    # If 'src' dir is at the root: '../src/DiffRhythm_logo.jpg' might work if run from gradio/
    # But the URL is more robust.
    gr.HTML(f"""
            <div style="display: flex; align-items: center;">
                <img src='https://raw.githubusercontent.com/ASLP-lab/DiffRhythm/refs/heads/main/src/DiffRhythm_logo.jpg'
                    style='width: 200px; height: 40%; display: block; margin: 0 auto 20px;'>
            </div>

            <div style="flex: 1; text-align: center;">
                <div style="font-size: 2em; font-weight: bold; text-align: center; margin-bottom: 5px">
                    Di♪♪Rhythm (谛韵)
                </div>
                <div style="display:flex; justify-content: center; column-gap:4px;">
                    <a href="https://arxiv.org/abs/2503.01183">
                        <img src='https://img.shields.io/badge/Arxiv-Paper-blue'>
                    </a>
                    <a href="https://github.com/ASLP-lab/DiffRhythm">
                        <img src='https://img.shields.io/badge/GitHub-Repo-green'>
                    </a>
                    <a href="https://aslp-lab.github.io/DiffRhythm.github.io/">
                        <img src='https://img.shields.io/badge/Project-Page-brown'>
                    </a>
                </div>
            </div>
            """)

    with gr.Tabs() as tabs:

        # page 1
        with gr.Tab("Music Generate", id=0):
            with gr.Row():
                with gr.Column():
                    lrc = gr.Textbox(
                        label="Lyrics",
                        placeholder="Input the full lyrics",
                        lines=12,
                        max_lines=50,
                        elem_classes="lyrics-scroll-box",
                        value="""[00:04.34]Tell me that I'm special\n[00:06.57]Tell me I look pretty\n[00:08.46]Tell me I'm a little angel\n[00:10.58]Sweetheart of your city\n[00:13.64]Say what I'm dying to hear\n[00:17.35]Cause I'm dying to hear you\n[00:20.86]Tell me I'm that new thing\n[00:22.93]Tell me that I'm relevant\n[00:24.96]Tell me that I got a big heart\n[00:27.04]Then back it up with evidence\n[00:29.94]I need it and I don't know why\n[00:34.28]This late at night\n[00:36.32]Isn't it lonely\n[00:39.24]I'd do anything to make you want me\n[00:43.40]I'd give it all up if you told me\n[00:47.42]That I'd be\n[00:49.43]The number one girl in your eyes\n[00:52.85]Your one and only\n[00:55.74]So what's it gon' take for you to want me\n[00:59.78]I'd give it all up if you told me\n[01:03.89]That I'd be\n[01:05.94]The number one girl in your eyes\n[01:11.34]Tell me I'm going real big places\n[01:14.32]Down to earth so friendly\n[01:16.30]And even through all the phases\n[01:18.46]Tell me you accept me\n[01:21.56]Well that's all I'm dying to hear\n[01:25.30]Yeah I'm dying to hear you\n[01:28.91]Tell me that you need me\n[01:30.85]Tell me that I'm loved\n[01:32.90]Tell me that I'm worth it\n[01:34.95]And that I'm enough\n[01:37.91]I need it and I don't know why\n[01:42.08]This late at night\n[01:44.24]Isn't it lonely\n[01:47.18]I'd do anything to make you want me\n[01:51.30]I'd give it all up if you told me\n[01:55.32]That I'd be\n[01:57.35]The number one girl in your eyes\n[02:00.72]Your one and only\n[02:03.57]So what's it gon' take for you to want me\n[02:07.78]I'd give it all up if you told me\n[02:11.74]That I'd be\n[02:13.86]The number one girl in your eyes\n[02:17.03]The girl in your eyes\n[02:21.05]The girl in your eyes\n[02:26.30]Tell me I'm the number one girl\n[02:28.44]I'm the number one girl in your eyes\n[02:33.49]The girl in your eyes\n[02:37.58]The girl in your eyes\n[02:42.74]Tell me I'm the number one girl\n[02:44.88]I'm the number one girl in your eyes\n[02:49.91]Well isn't it lonely\n[02:53.19]I'd do anything to make you want me\n[02:57.10]I'd give it all up if you told me\n[03:01.15]That I'd be\n[03:03.31]The number one girl in your eyes\n[03:06.57]Your one and only\n[03:09.42]So what's it gon' take for you to want me\n[03:13.50]I'd give it all up if you told me\n[03:17.56]That I'd be\n[03:19.66]The number one girl in your eyes\n[03:25.74]The number one girl in your eyes"""
                    )

                    current_prompt_type = gr.State(value="audio")
                    with gr.Tabs() as inside_tabs:
                        with gr.Tab("Audio Prompt"):
                            # --- PATH MODIFIED ---
                            audio_prompt = gr.Audio(label="Audio Prompt", type="filepath", value="../src/prompt/default.wav")
                        with gr.Tab("Text Prompt"):
                            text_prompt = gr.Textbox(
                            label="Text Prompt",
                            placeholder="Enter the Text Prompt, eg: emotional piano pop",
                            )
                        def update_prompt_type(evt: gr.SelectData):
                            return "audio" if evt.index == 0 else "text"

                        inside_tabs.select(
                            fn=update_prompt_type,
                            outputs=current_prompt_type
                        )

                with gr.Column():
                    with gr.Accordion("Best Practices Guide", open=True):
                        gr.Markdown("""
1. **Lyrics Format Requirements**
    - Each line must follow: `[mm:ss.xx]Lyric content`
    - Example of valid format:
    ```
    [00:10.00]Moonlight spills through broken blinds
    [00:13.20]Your shadow dances on the dashboard shrine
    ```

2. **Audio Prompt Requirements**
    - Reference audio should be ≥ 1 second, audio >10 seconds will be randomly clipped into 10 seconds
    - For optimal results, the 10-second clips should be carefully selected
    - Shorter clips may lead to incoherent generation
3. **Supported Languages**
    - **Chinese and English**
    - More languages comming soon

4. **Others**
    - If loading audio result is slow, you can select Output Format as mp3 in Advanced Settings.

                        """)
                    Music_Duration = gr.Radio(["95s", "285s"], label="Music Duration", value="95s")

                    lyrics_btn = gr.Button("Generate", variant="primary")
                    audio_output = gr.Audio(label="Audio Result", type="filepath", elem_id="audio_output")
                    with gr.Accordion("Advanced Settings", open=False):
                        seed = gr.Slider(
                            label="Seed",
                            minimum=0,
                            maximum=MAX_SEED,
                            step=1,
                            value=0,
                        )
                        randomize_seed = gr.Checkbox(label="Randomize seed", value=True)

                        steps = gr.Slider(
                                    minimum=10,
                                    maximum=100,
                                    value=32,
                                    step=1,
                                    label="Diffusion Steps",
                                    interactive=True,
                                    elem_id="step_slider"
                                )
                        cfg_strength = gr.Slider(
                                    minimum=1,
                                    maximum=10,
                                    value=4.0,
                                    step=0.5,
                                    label="CFG Strength",
                                    interactive=True,
                                    elem_id="step_slider"
                                )
                        odeint_method = gr.Radio(["euler", "midpoint", "rk4","implicit_adams"], label="ODE Solver", value="euler")
                        file_type = gr.Dropdown(["wav", "mp3", "ogg"], label="Output Format", value="wav")

            # --- PATHS MODIFIED for all examples ---
            gr.Examples(
                examples=[
                    ["../src/prompt/pop_cn.wav"],
                    ["../src/prompt/pop_en.wav"],
                    ["../src/prompt/rock_cn.wav"],
                    ["../src/prompt/rock_en.wav"],
                    ["../src/prompt/country_cn.wav"],
                    ["../src/prompt/country_en.wav"],
                    ["../src/prompt/classic_cn.wav"],
                    ["../src/prompt/classic_en.wav"],
                    ["../src/prompt/jazz_cn.wav"],
                    ["../src/prompt/jazz_en.wav"],
                    ["../src/prompt/rap_cn.wav"],
                    ["../src/prompt/rap_en.wav"],
                    ["../src/prompt/default.wav"]
                ],
                inputs=[audio_prompt],
                label="Audio Examples",
                examples_per_page=13,
                elem_id="audio-examples-container"
            )

            gr.Examples(
                examples=[
                    ["Pop Emotional Piano"],
                    ["流行 情感 钢琴"],
                    ["Indie folk ballad, coming-of-age themes, acoustic guitar picking with harmonica interludes"],
                    ["独立民谣, 成长主题, 原声吉他弹奏与口琴间奏"]
                ],
                inputs=[text_prompt],
                label="Text Examples",
                examples_per_page=4,
                elem_id="text-examples-container"
            )

            gr.Examples(
                examples=[
                    ["""[00:04.34]Tell me that I'm special\n[00:06.57]Tell me I look pretty\n[00:08.46]Tell me I'm a little angel\n[00:10.58]Sweetheart of your city\n[00:13.64]Say what I'm dying to hear\n[00:17.35]Cause I'm dying to hear you\n[00:20.86]Tell me I'm that new thing\n[00:22.93]Tell me that I'm relevant\n[00:24.96]Tell me that I got a big heart\n[00:27.04]Then back it up with evidence\n[00:29.94]I need it and I don't know why\n[00:34.28]This late at night\n[00:36.32]Isn't it lonely\n[00:39.24]I'd do anything to make you want me\n[00:43.40]I'd give it all up if you told me\n[00:47.42]That I'd be\n[00:49.43]The number one girl in your eyes\n[00:52.85]Your one and only\n[00:55.74]So what's it gon' take for you to want me\n[00:59.78]I'd give it all up if you told me\n[01:03.89]That I'd be\n[01:05.94]The number one girl in your eyes\n[01:11.34]Tell me I'm going real big places\n[01:14.32]Down to earth so friendly\n[01:16.30]And even through all the phases\n[01:18.46]Tell me you accept me\n[01:21.56]Well that's all I'm dying to hear\n[01:25.30]Yeah I'm dying to hear you\n[01:28.91]Tell me that you need me\n[01:30.85]Tell me that I'm loved\n[01:32.90]Tell me that I'm worth it\n[01:34.95]And that I'm enough\n[01:37.91]I need it and I don't know why\n[01:42.08]This late at night\n[01:44.24]Isn't it lonely\n[01:47.18]I'd do anything to make you want me\n[01:51.30]I'd give it all up if you told me\n[01:55.32]That I'd be\n[01:57.35]The number one girl in your eyes\n[02:00.72]Your one and only\n[02:03.57]So what's it gon' take for you to want me\n[02:07.78]I'd give it all up if you told me\n[02:11.74]That I'd be\n[02:13.86]The number one girl in your eyes\n[02:17.03]The girl in your eyes\n[02:21.05]The girl in your eyes\n[02:26.30]Tell me I'm the number one girl\n[02:28.44]I'm the number one girl in your eyes\n[02:33.49]The girl in your eyes\n[02:37.58]The girl in your eyes\n[02:42.74]Tell me I'm the number one girl\n[02:44.88]I'm the number one girl in your eyes\n[02:49.91]Well isn't it lonely\n[02:53.19]I'd do anything to make you want me\n[02:57.10]I'd give it all up if you told me\n[03:01.15]That I'd be\n[03:03.31]The number one girl in your eyes\n[03:06.57]Your one and only\n[03:09.42]So what's it gon' take for you to want me\n[03:13.50]I'd give it all up if you told me\n[03:17.56]That I'd be\n[03:19.66]The number one girl in your eyes\n[03:25.74]The number one girl in your eyes"""],
                    ["""[00:00.52]Abracadabra abracadabra\n[00:03.97]Ha\n[00:04.66]Abracadabra abracadabra\n[00:12.02]Yeah\n[00:15.80]Pay the toll to the angels\n[00:19.08]Drawin' circles in the clouds\n[00:23.31]Keep your mind on the distance\n[00:26.67]When the devil turns around\n[00:30.95]Hold me in your heart tonight\n[00:34.11]In the magic of the dark moonlight\n[00:38.44]Save me from this empty fight\n[00:43.83]In the game of life\n[00:45.84]Like a poem said by a lady in red\n[00:49.45]You hear the last few words of your life\n[00:53.15]With a haunting dance now you're both in a trance\n[00:56.90]It's time to cast your spell on the night\n[01:01.40]Abracadabra ama-ooh-na-na\n[01:04.88]Abracadabra porta-ooh-ga-ga\n[01:08.92]Abracadabra abra-ooh-na-na\n[01:12.30]In her tongue she's sayin'\n[01:14.76]Death or love tonight\n[01:18.61]Abracadabra abracadabra\n[01:22.18]Abracadabra abracadabra\n[01:26.08]Feel the beat under your feet\n[01:27.82]The floor's on fire\n[01:29.90]Abracadabra abracadabra\n[01:33.78]Choose the road on the west side\n[01:37.09]As the dust flies watch it burn\n[01:41.45]Don't waste time on feeling\n[01:44.64]Your depression won't return\n[01:49.15]Hold me in your heart tonight\n[01:52.21]In the magic of the dark moonlight\n[01:56.54]Save me from this empty fight\n[02:01.77]In the game of life\n[02:03.94]Like a poem said by a lady in red\n[02:07.52]You hear the last few words of your life\n[02:11.19]With a haunting dance now you're both in a trance\n[02:14.95]It's time to cast your spell on the night\n[02:19.53]Abracadabra ama-ooh-na-na\n[02:22.71]Abracadabra porta-ooh-ga-ga\n[02:26.94]Abracadabra abra-ooh-na-na\n[02:30.42]In her tongue she's sayin'\n[02:32.83]Death or love tonight\n[02:36.55]Abracadabra abracadabra\n[02:40.27]Abracadabra abracadabra\n[02:44.19]Feel the beat under your feet\n[02:46.14]The floor's on fire\n[02:47.95]Abracadabra abracadabra\n[02:51.17]Phantom of the dance floor come to me\n[02:58.46]Sing for me a sinful melody\n[03:06.51]Ah-ah-ah-ah-ah ah-ah ah-ah\n[03:13.76]Ah-ah-ah-ah-ah ah-ah ah-ah\n[03:22.39]Abracadabra ama-ooh-na-na\n[03:25.66]Abracadabra porta-ooh-ga-ga\n[03:29.87]Abracadabra abra-ooh-na-na\n[03:33.16]In her tongue she's sayin'\n[03:35.55]Death or love tonight"""],
                    ["""[00:00.27]只因你太美 baby 只因你太美 baby\n[00:08.95]只因你实在是太美 baby\n[00:13.99]只因你太美 baby\n[00:18.89]迎面走来的你让我如此蠢蠢欲动\n[00:20.88]这种感觉我从未有\n[00:21.79]Cause I got a crush on you who you\n[00:25.74]你是我的我是你的谁\n[00:28.09]再多一眼看一眼就会爆炸\n[00:30.31]再近一点靠近点快被融化\n[00:32.49]想要把你占为己有 baby bae\n[00:34.60]不管走到哪里\n[00:35.44]都会想起的人是你 you you\n[00:38.12]我应该拿你怎样\n[00:39.61]Uh 所有人都在看着你\n[00:42.36]我的心总是不安\n[00:44.18]Oh 我现在已病入膏肓\n[00:46.63]Eh oh\n[00:47.84]难道真的因你而疯狂吗\n[00:51.57]我本来不是这种人\n[00:53.59]因你变成奇怪的人\n[00:55.77]第一次呀变成这样的我\n[01:01.23]不管我怎么去否认\n[01:03.21]只因你太美 baby 只因你太美 baby\n[01:11.46]只因你实在是太美 baby\n[01:16.75]只因你太美 baby\n[01:21.09]Oh eh oh\n[01:22.82]现在确认地告诉我\n[01:25.26]Oh eh oh\n[01:27.31]你到底属于谁\n[01:29.98]Oh eh oh\n[01:31.70]现在确认地告诉我\n[01:34.45]Oh eh oh\n[01:36.35]你到底属于谁\n[01:37.65]就是现在告诉我\n[01:40.00]跟着那节奏 缓缓 make wave\n[01:42.42]甜蜜的奶油 it's your birthday cake\n[01:44.66]男人们的 game call me 你恋人\n[01:46.83]别被欺骗愉快的 I wanna play\n[01:48.83]我的脑海每分每秒为你一人沉醉\n[01:50.90]最迷人让我神魂颠倒是你身上香水\n[01:53.30]Oh right baby I'm fall in love with you\n[01:55.20]我的一切你都拿走\n[01:56.40]只要有你就已足够\n[01:58.56]我到底应该怎样\n[02:00.37]Uh 我心里一直很不安\n[02:03.12]其他男人们的视线\n[02:04.84]Oh 全都只看着你的脸\n[02:07.33]Eh oh\n[02:08.39]难道真的因你而疯狂吗\n[02:12.43]我本来不是这种人\n[02:14.35]因你变成奇怪的人\n[02:16.59]第一次呀变成这样的我\n[02:21.76]不管我怎么去否认\n[02:24.03]只因你太美 baby 只因你太美 baby\n[02:32.37]只因你实在是太美 baby\n[02:37.49]只因你太美 baby\n[02:43.66]我愿意把我的全部都给你\n[02:47.19]我每天在梦里都梦见你\n[02:49.13]还有我闭着眼睛也能看到你\n[02:52.58]现在开始我只准你看我\n[02:56.28]I don't wanna wake up in dream\n[02:57.92]我只想看你这是真心话\n[02:59.86]只因你太美 baby 只因你太美 baby\n[03:08.20]只因你实在是太美 baby\n[03:13.22]只因你太美 baby\n[03:17.69]Oh eh oh\n[03:19.36]现在确认的告诉我\n[03:21.91]Oh eh oh\n[03:23.85]你到底属于谁\n[03:26.58]Oh eh oh\n[03:28.32]现在确认的告诉我\n[03:30.95]Oh eh oh\n[03:32.82]你到底属于谁就是现在告诉我"""]
                ],

                inputs=[lrc],
                label="Lrc Examples",
                examples_per_page=3,
                elem_id="lrc-examples-container",
            )


        # page 2
        with gr.Tab("Lyrics Generate", id=1):
            with gr.Row():
                with gr.Column():
                    with gr.Accordion("Notice", open=False):
                        gr.Markdown("**Two Generation Modes:**\n1. Generate from theme & tags\n2. Add timestamps to existing lyrics")

                    with gr.Group():
                        gr.Markdown("### Method 1: Generate from Theme")
                        theme = gr.Textbox(label="theme", placeholder="Enter song theme, e.g: Love and Heartbreak")
                        tags_gen = gr.Textbox(label="tags", placeholder="Enter song tags, e.g: pop confidence healing")
                        language = gr.Radio(["cn", "en"], label="Language", value="en")
                        gen_from_theme_btn = gr.Button("Generate LRC (From Theme)", variant="primary")

                        gr.Examples(
                            examples=[
                                [
                                    "Love and Heartbreak",
                                    "vocal emotional piano pop",
                                    "en"
                                ],
                                [
                                    "Heroic Epic",
                                    "choir orchestral powerful",
                                    "cn"
                                ]
                            ],
                            inputs=[theme, tags_gen, language],
                            label="Examples: Generate from Theme"
                        )

                    with gr.Group(visible=True):
                        gr.Markdown("### Method 2: Add Timestamps to Lyrics")
                        tags_lyrics = gr.Textbox(label="tags", placeholder="Enter song tags, e.g: ballad piano slow")
                        lyrics_input = gr.Textbox(
                            label="Raw Lyrics (without timestamps)",
                            placeholder="Enter plain lyrics (without timestamps), e.g:\nYesterday\nAll my troubles...",
                            lines=10,
                            max_lines=50,
                            elem_classes="lyrics-scroll-box"
                        )

                        gen_from_lyrics_btn = gr.Button("Generate LRC (From Lyrics)", variant="primary")

                        gr.Examples(
                            examples=[
                                [
                                    "acoustic folk happy",
                                    """I'm sitting here in the boring room\nIt's just another rainy Sunday afternoon"""
                                ],
                                [
                                    "electronic dance energetic",
                                    """We're living in a material world\nAnd I am a material girl"""
                                ]
                            ],
                            inputs=[tags_lyrics, lyrics_input],
                            label="Examples: Generate from Lyrics"
                        )


                with gr.Column():
                    lrc_output = gr.Textbox(
                        label="Generated LRC",
                        placeholder="Timed lyrics will appear here",
                        lines=57, # Consider making this flexible or using the CSS class
                        elem_classes="lrc-output", # Use CSS class for styling
                        show_copy_button=True
                    )

            # Bind functions
            gen_from_theme_btn.click(
                fn=R1_infer1,
                inputs=[theme, tags_gen, language],
                outputs=lrc_output
            )

            gen_from_lyrics_btn.click(
                fn=R1_infer2,
                inputs=[tags_lyrics, lyrics_input],
                outputs=lrc_output
            )

    # This select seems redundant? Removing unless it serves a specific purpose.
    # tabs.select(
    # lambda s: None,
    # None,
    # None
    # )

    lyrics_btn.click(
        fn=infer_music,
        inputs=[lrc, audio_prompt, text_prompt, current_prompt_type, seed, randomize_seed, steps, cfg_strength, file_type, odeint_method, Music_Duration],
        outputs=audio_output
    )


if __name__ == "__main__":
    # Consider adding argparse for host/port/share options
    demo.launch()
