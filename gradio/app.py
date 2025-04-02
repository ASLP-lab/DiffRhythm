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
import spaces
from tqdm import tqdm
import random
import numpy as np
import sys
import base64

# --- Start Modification: Adjust Python Path ---
# Get the directory containing this script (gradio/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from gradio/)
project_root = os.path.abspath(os.path.join(current_dir, '..'))
# Add the project root to the Python path so imports like 'diffrhythm' work
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End Modification ---

# Now the imports should work correctly
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
device='cuda' if torch.cuda.is_available() else 'cpu' # Use CPU if CUDA not available
print(f"Using device: {device}")

# Check if models can be prepared
try:
    cfm, cfm_full, tokenizer, muq, vae = prepare_model(device)
    cfm = torch.compile(cfm) if device == 'cuda' else cfm # Compile only if using CUDA
    cfm_full = torch.compile(cfm_full) if device == 'cuda' else cfm_full # Compile only if using CUDA
except Exception as e:
    print(f"Error preparing models: {e}")
    print("Please ensure model files are downloaded and accessible.")
    # Optionally, exit or disable parts of the UI if models fail to load
    # sys.exit(1) # Uncomment to exit if models are essential

# Define paths relative to the project root
SRC_PROMPT_DIR = os.path.join(project_root, 'gradio', 'src', 'prompt') # Adjusted path for prompts within gradio/src
DEFAULT_PROMPT_PATH = os.path.join(SRC_PROMPT_DIR, 'default.wav')

@spaces.GPU(duration=40)
def infer_music(lrc, ref_audio_path, text_prompt, current_prompt_type, seed=42, randomize_seed=False, steps=32, cfg_strength=4.0, file_type='wav', odeint_method='euler', Music_Duration='95s', device=device):
    # Ensure models are loaded before inference
    if 'cfm' not in globals() or 'cfm_full' not in globals():
         raise gr.Error("Models are not loaded. Cannot perform inference.")

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
             if ref_audio_path is None:
                  raise gr.Error("Audio prompt is selected, but no audio file provided or default path is invalid.")
             style_prompt, vocal_flag = get_audio_style_prompt(muq, ref_audio_path)
        else:
             if not text_prompt:
                  raise gr.Error("Text prompt is selected, but no text provided.")
             style_prompt = get_text_style_prompt(muq, text_prompt)
    except Exception as e:
        raise gr.Error(f"Error processing prompts: {str(e)}")

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
                                   device=device # Pass device explicitly
                                  )
    except Exception as e:
         raise gr.Error(f"Error during inference: {str(e)}")

    return generated_song

def R1_infer1(theme, tags_gen, language):
    # Check for API key existence
    api_key = os.getenv('HS_DP_API')
    if not api_key:
         return "Error: HS_DP_API environment variable not set. Cannot generate lyrics from theme."
    try:
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
            model="ep-20250304144033-nr9wl", # Consider making model configurable or checking its availability
            messages=[
                {"role": "system", "content": "You are a professional musician who has been invited to make music-related comments."},
                {"role": "user", "content": llm_prompt.format(theme=theme, tags=tags_gen, language=language)},
            ],
            stream=False
        )

        info = response.choices[0].message.content
        return info

    except requests.exceptions.RequestException as e:
        print(f'LLM Request Error (R1_infer1): {e}')
        return f"Error: Could not connect to the lyrics generation service. {e}"
    except Exception as e:
        print(f'LLM General Error (R1_infer1): {e}')
        return f"Error: An unexpected error occurred during lyrics generation. {e}"


def R1_infer2(tags_lyrics, lyrics_input):
    # Check for API key existence
    api_key = os.getenv('HS_DP_API')
    if not api_key:
         return "Error: HS_DP_API environment variable not set. Cannot add timestamps."
    try:
        client = OpenAI(api_key=api_key, base_url = "https://ark.cn-beijing.volces.com/api/v3")

        llm_prompt = """
        {lyrics_input}

        The text above is a song's lyrics, with each line being one phrase. The desired style is "{tags_lyrics}".
        Please add timestamps to each line to create an LRC file.
        Requirements:
        1. Distribute timestamps naturally based on the song's style ({tags_lyrics}), lyrics' emotion, and rhythm. Do NOT assign timestamps mechanically based only on line length.
        2. The first line's timestamp must account for intro length; do NOT start at `[00:00.00]`.
        3. Strictly follow the LRC format: `[mm:ss.xx]Lyric content`.
        4. Output ONLY the LRC formatted lyrics. Do NOT include any other explanations, notes, or commentary.
        """

        response = client.chat.completions.create(
            model="ep-20250304144033-nr9wl", # Consider making model configurable or checking its availability
            messages=[
                {"role": "system", "content": "You are a professional musician specialized in creating LRC timestamped lyrics."},
                {"role": "user", "content": llm_prompt.format(lyrics_input=lyrics_input, tags_lyrics=tags_lyrics)},
            ],
            stream=False
        )

        info = response.choices[0].message.content
        # Basic validation: Check if the output looks like LRC
        if info and info.strip().startswith("[") and ":" in info and "]" in info:
             return info
        else:
             print(f"LLM returned non-LRC format (R1_infer2): {info}")
             return "Error: The generation service returned an invalid format. Please try again or check the input lyrics."


    except requests.exceptions.RequestException as e:
        print(f'LLM Request Error (R1_infer2): {e}')
        return f"Error: Could not connect to the lyrics generation service. {e}"
    except Exception as e:
        print(f'LLM General Error (R1_infer2): {e}')
        return f"Error: An unexpected error occurred during timestamp generation. {e}"


css = """
/* 固定文本域高度并强制滚动条 */
.lyrics-scroll-box textarea {
    height: 405px !important;  /* 固定高度 */
    max-height: 500px !important;  /* 最大高度 */
    overflow-y: auto !important;  /* 垂直滚动 */
    white-space: pre-wrap;  /* 保留换行 */
    line-height: 1.5;  /* 行高优化 */
}

/* Style for LRC output box */
.lrc-output textarea {
    height: calc(405px + 140px) !important; /* Match combined height of other elements for alignment */
    max-height: 600px !important;
    overflow-y: auto !important;
    white-space: pre-wrap;
    line-height: 1.5;
    font-family: monospace; /* Use monospace for better alignment */
}


.gr-examples {
    background: transparent !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px;
    margin: 1rem 0 !important;
    padding: 1rem !important;
}

"""

# --- Start Modification: Use absolute path for logo if needed, or adjust relative ---
# Using the raw GitHub URL is generally safer for web deployment.
# If running locally and need local files, ensure paths are correct relative to project_root
# logo_path = os.path.join(project_root, 'src', 'DiffRhythm_logo.jpg') # Example local path if needed
logo_url = 'https://raw.githubusercontent.com/ASLP-lab/DiffRhythm/refs/heads/main/src/DiffRhythm_logo.jpg'
# --- End Modification ---

with gr.Blocks(css=css) as demo:
    gr.HTML(f"""
            <div style="display: flex; justify-content: center; align-items: center;">
                <img src='{logo_url}'
                    style='width: 200px; height: auto; display: block; margin-bottom: 20px;'>
            </div>

            <div style="flex: 1; text-align: center;">
                <div style="font-size: 2em; font-weight: bold; text-align: center; margin-bottom: 5px">
                    Di♪♪Rhythm (谛韵)
                </div>
                <div style="display:flex; justify-content: center; column-gap:4px;">
                    <a href="https://arxiv.org/abs/2503.01183" target="_blank">
                        <img src='https://img.shields.io/badge/Arxiv-Paper-blue'>
                    </a>
                    <a href="https://github.com/ASLP-lab/DiffRhythm" target="_blank">
                        <img src='https://img.shields.io/badge/GitHub-Repo-green'>
                    </a>
                    <a href="https://aslp-lab.github.io/DiffRhythm.github.io/" target="_blank">
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
                        label="Lyrics (LRC Format)",
                        placeholder="Input the full lyrics in [mm:ss.xx] format",
                        lines=12,
                        max_lines=50,
                        elem_classes="lyrics-scroll-box",
                        value="""[00:04.34]Tell me that I'm special\n[00:06.57]Tell me I look pretty\n[00:08.46]Tell me I'm a little angel\n[00:10.58]Sweetheart of your city\n[00:13.64]Say what I'm dying to hear\n[00:17.35]Cause I'm dying to hear you\n[00:20.86]Tell me I'm that new thing\n[00:22.93]Tell me that I'm relevant\n[00:24.96]Tell me that I got a big heart\n[00:27.04]Then back it up with evidence\n[00:29.94]I need it and I don't know why\n[00:34.28]This late at night\n[00:36.32]Isn't it lonely\n[00:39.24]I'd do anything to make you want me\n[00:43.40]I'd give it all up if you told me\n[00:47.42]That I'd be\n[00:49.43]The number one girl in your eyes\n[00:52.85]Your one and only\n[00:55.74]So what's it gon' take for you to want me\n[00:59.78]I'd give it all up if you told me\n[01:03.89]That I'd be\n[01:05.94]The number one girl in your eyes\n[01:11.34]Tell me I'm going real big places\n[01:14.32]Down to earth so friendly\n[01:16.30]And even through all the phases\n[01:18.46]Tell me you accept me\n[01:21.56]Well that's all I'm dying to hear\n[01:25.30]Yeah I'm dying to hear you\n[01:28.91]Tell me that you need me\n[01:30.85]Tell me that I'm loved\n[01:32.90]Tell me that I'm worth it\n[01:34.95]And that I'm enough\n[01:37.91]I need it and I don't know why\n[01:42.08]This late at night\n[01:44.24]Isn't it lonely\n[01:47.18]I'd do anything to make you want me\n[01:51.30]I'd give it all up if you told me\n[01:55.32]That I'd be\n[01:57.35]The number one girl in your eyes\n[02:00.72]Your one and only\n[02:03.57]So what's it gon' take for you to want me\n[02:07.78]I'd give it all up if you told me\n[02:11.74]That I'd be\n[02:13.86]The number one girl in your eyes\n[02:17.03]The girl in your eyes\n[02:21.05]The girl in your eyes\n[02:26.30]Tell me I'm the number one girl\n[02:28.44]I'm the number one girl in your eyes\n[02:33.49]The girl in your eyes\n[02:37.58]The girl in your eyes\n[02:42.74]Tell me I'm the number one girl\n[02:44.88]I'm the number one girl in your eyes\n[02:49.91]Well isn't it lonely\n[02:53.19]I'd do anything to make you want me\n[02:57.10]I'd give it all up if you told me\n[03:01.15]That I'd be\n[03:03.31]The number one girl in your eyes\n[03:06.57]Your one and only\n[03:09.42]So what's it gon' take for you to want me\n[03:13.50]I'd give it all up if you told me\n[03:17.56]That I'd be\n[03:19.66]The number one girl in your eyes\n[03:25.74]The number one girl in your eyes"""
                    )

                    current_prompt_type = gr.State(value="audio")
                    with gr.Tabs() as inside_tabs:
                        with gr.Tab("Audio Prompt"):
                            # --- Start Modification: Update relative path ---
                            audio_prompt = gr.Audio(label="Audio Prompt", type="filepath", value=DEFAULT_PROMPT_PATH)
                            # --- End Modification ---
                        with gr.Tab("Text Prompt"):
                            text_prompt = gr.Textbox(
                            label="Text Prompt",
                            placeholder="Enter the Text Prompt, eg: emotional piano pop",
                            )
                        def update_prompt_type(evt: gr.SelectData):
                            # Return 'audio' or 'text' based on the selected tab index
                            return "audio" if evt.index == 0 else "text"

                        inside_tabs.select(
                            fn=update_prompt_type,
                            inputs=None, # No direct input needed, event data is passed automatically
                            outputs=current_prompt_type
                        )

                with gr.Column():
                    with gr.Accordion("Best Practices Guide", open=True):
                        gr.Markdown("""
1. **Lyrics Format Requirements**
    - Each line must follow: `[mm:ss.xx]Lyric content` (no space after timestamp).
    - Timestamps should be reasonably distributed.
    - Example: `[00:10.00]Moonlight spills`

2. **Audio Prompt Requirements**
    - Use audio ≥ 1 second. Audio > 10s will be randomly clipped to 10s.
    - Carefully selected 10s clips give better results. Shorter clips (< 1s) might cause issues.

3. **Supported Languages**
    - Currently **Chinese** and **English**. More coming soon!

4. **Tips**
    - If audio loading is slow, try selecting 'mp3' in Advanced Settings > Output Format.
    - Ensure your LRC lyrics accurately reflect the timing you desire.
    - Use the "Lyrics Generate" tab if you need help creating LRC format lyrics.
                        """)
                    Music_Duration = gr.Radio(["95s", "285s"], label="Max Music Duration", value="95s", info="Selects the model variant (standard or full). Actual duration depends on LRC.")

                    lyrics_btn = gr.Button("Generate Music", variant="primary")
                    audio_output = gr.Audio(label="Generated Music", type="filepath", elem_id="audio_output")
                    with gr.Accordion("Advanced Settings", open=False):
                        seed = gr.Slider(
                            label="Seed",
                            minimum=0,
                            maximum=MAX_SEED,
                            step=1,
                            value=42, # Use a default fixed seed
                        )
                        randomize_seed = gr.Checkbox(label="Randomize seed", value=True)

                        steps = gr.Slider(
                                    minimum=10,
                                    maximum=100,
                                    value=32,
                                    step=1,
                                    label="Diffusion Steps",
                                    interactive=True,
                                )
                        cfg_strength = gr.Slider(
                                    minimum=1.0,
                                    maximum=10.0,
                                    value=4.0,
                                    step=0.5,
                                    label="CFG Strength (Guidance Scale)",
                                    interactive=True,
                                )
                        odeint_method = gr.Radio(["euler", "midpoint", "rk4","implicit_adams"], label="ODE Solver", value="euler", info="Affects generation process.")
                        file_type = gr.Dropdown(["wav", "mp3", "ogg"], label="Output Format", value="wav", info="wav is lossless, mp3/ogg are smaller.")

            # --- Start Modification: Update relative paths in examples ---
            audio_example_paths = [
                os.path.join(SRC_PROMPT_DIR, fname) for fname in [
                    "pop_cn.wav", "pop_en.wav", "rock_cn.wav", "rock_en.wav",
                    "country_cn.wav", "country_en.wav", "classic_cn.wav", "classic_en.wav",
                    "jazz_cn.wav", "jazz_en.wav", "rap_cn.wav", "rap_en.wav",
                    "default.wav"
                ]
            ]
            # Check if example files exist, warn if not
            missing_audio_examples = [p for p in audio_example_paths if not os.path.exists(p)]
            if missing_audio_examples:
                print(f"Warning: Missing audio example files: {missing_audio_examples}")

            gr.Examples(
                examples=[[p] for p in audio_example_paths if os.path.exists(p)], # Only show existing examples
                inputs=[audio_prompt],
                label="Audio Prompt Examples (Click to Load)",
                examples_per_page=13,
                elem_id="audio-examples-container"
            )
            # --- End Modification ---

            gr.Examples(
                examples=[
                    ["Pop Emotional Piano"],
                    ["流行 情感 钢琴"],
                    ["Indie folk ballad, coming-of-age themes, acoustic guitar picking with harmonica interludes"],
                    ["独立民谣, 成长主题, 原声吉他弹奏与口琴间奏"]
                ],
                inputs=[text_prompt],
                label="Text Prompt Examples (Click to Load)",
                examples_per_page=4,
                elem_id="text-examples-container"
            )

            # --- Start Modification: No path changes needed here, just long text ---
            gr.Examples(
                examples=[
                     # Example 1 (English Pop) - Shortened for brevity
                    ["""[00:04.34]Tell me that I'm special
[00:06.57]Tell me I look pretty
[00:08.46]Tell me I'm a little angel
[00:10.58]Sweetheart of your city
... (rest of lyrics) ...
[03:19.66]The number one girl in your eyes
[03:25.74]The number one girl in your eyes"""],
                    # Example 2 (English Dance/Pop) - Shortened for brevity
                    ["""[00:00.52]Abracadabra abracadabra
[00:03.97]Ha
[00:04.66]Abracadabra abracadabra
... (rest of lyrics) ...
[03:33.16]In her tongue she's sayin'
[03:35.55]Death or love tonight"""],
                    # Example 3 (Chinese Pop/Rap) - Shortened for brevity
                    ["""[00:00.27]只因你太美 baby 只因你太美 baby
[00:08.95]只因你实在是太美 baby
... (rest of lyrics) ...
[03:30.95]Oh eh oh
[03:32.82]你到底属于谁就是现在告诉我"""]
                ],
                inputs=[lrc],
                label="LRC Examples (Click to Load)",
                examples_per_page=3,
                elem_id="lrc-examples-container",
            )
             # --- End Modification ---


        # page 2
        with gr.Tab("Lyrics Generate", id=1):
            with gr.Row():
                with gr.Column(scale=1): # Make left column slightly smaller
                    with gr.Accordion("Notice", open=False):
                        gr.Markdown("**Requires OpenAI Compatible API Key**\nSet the `HS_DP_API` environment variable.\n\n**Two Generation Modes:**\n1. **Generate from theme & tags:** Creates full LRC lyrics based on your idea.\n2. **Add timestamps to existing lyrics:** Takes your plain text lyrics and adds timing based on tags.")

                    with gr.Group():
                        gr.Markdown("### Method 1: Generate LRC from Theme")
                        theme = gr.Textbox(label="Theme", placeholder="e.g., Love and Heartbreak, City at Night")
                        tags_gen = gr.Textbox(label="Tags / Style", placeholder="e.g., pop emotional piano, jazz upbeat saxophone")
                        language = gr.Radio(["en", "cn"], label="Language", value="en")
                        gen_from_theme_btn = gr.Button("Generate LRC (From Theme)", variant="primary")

                        gr.Examples(
                            examples=[
                                ["Love and Heartbreak", "vocal emotional piano pop", "en"],
                                ["City at Night", "jazz saxophone slow contemplative", "en"],
                                ["Heroic Epic", "choir orchestral powerful", "cn"],
                                ["校园里的夏天", "民谣 吉他 清新", "cn"]
                            ],
                            inputs=[theme, tags_gen, language],
                            label="Examples: Generate from Theme"
                        )

                    with gr.Group(visible=True):
                        gr.Markdown("### Method 2: Add Timestamps to Lyrics")
                        tags_lyrics = gr.Textbox(label="Tags / Style", placeholder="e.g., ballad piano slow, rock energetic guitar")
                        lyrics_input = gr.Textbox(
                            label="Raw Lyrics (One line per phrase, no timestamps)",
                            placeholder="Paste your lyrics here, like:\nYesterday\nAll my troubles seemed so far away\nNow it looks as though they're here to stay...",
                            lines=10,
                            max_lines=50,
                            elem_classes="lyrics-scroll-box" # Reuse class for consistent height
                        )

                        gen_from_lyrics_btn = gr.Button("Generate LRC (From Lyrics)", variant="primary")

                        gr.Examples(
                            examples=[
                                ["acoustic folk happy", "I'm sitting here in the boring room\nIt's just another rainy Sunday afternoon\nI'm wasting my time\nI got nothing to do"],
                                ["electronic dance energetic", "We're living in a material world\nAnd I am a material girl\nYou know that we are living in a material world\nAnd I am a material girl"]
                            ],
                            inputs=[tags_lyrics, lyrics_input],
                            label="Examples: Generate from Lyrics"
                        )


                with gr.Column(scale=1): # Make right column slightly smaller
                    lrc_output = gr.Textbox(
                        label="Generated LRC",
                        placeholder="Timed lyrics (LRC format) will appear here.",
                        lines=30, # Adjusted line count based on new CSS height
                        max_lines=100,
                        elem_classes="lrc-output", # Use specific class for styling
                        show_copy_button=True
                    )

            # Bind functions
            gen_from_theme_btn.click(
                fn=R1_infer1,
                inputs=[theme, tags_gen, language],
                outputs=lrc_output,
                api_name="generate_lrc_from_theme"
            )

            gen_from_lyrics_btn.click(
                fn=R1_infer2,
                inputs=[tags_lyrics, lyrics_input],
                outputs=lrc_output,
                api_name="add_timestamps_to_lyrics"
            )

    # Main generation button click action
    lyrics_btn.click(
        fn=infer_music,
        inputs=[
            lrc, audio_prompt, text_prompt, current_prompt_type,
            seed, randomize_seed, steps, cfg_strength, file_type,
            odeint_method, Music_Duration
        ],
        outputs=audio_output,
        api_name="generate_music"
    )

if __name__ == "__main__":
    # Check for essential environment variables or configurations if needed
    if not os.getenv('HS_DP_API'):
         print("Warning: HS_DP_API environment variable is not set. Lyrics generation tab will show errors.")

    # Launch the Gradio app
    demo.launch()
