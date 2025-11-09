import gradio as gr
import os
import subprocess
import shutil
from pathlib import Path

def generate_from_prompt(lrc_file, prompt, audio_length, output_dir):
    """Generate song based on LRC and text prompt."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        if lrc_file is None:
            return "Error: Please upload an LRC file first", None
        
        lrc_path = lrc_file.name if hasattr(lrc_file, 'name') else lrc_file
        cmd = f"python3 infer/infer.py --lrc-path {lrc_path} --ref-prompt \"{prompt}\" --audio-length {audio_length} --output-dir {output_dir} --chunked --batch-infer-num 5"
        
        print(f"Running command: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Command output: {result.stdout}")
        
        audio_file = os.path.join(output_dir, "output.wav")
        
        # Verify the audio file exists and is not empty
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
            abs_path = os.path.abspath(audio_file)
            file_size = os.path.getsize(audio_file)
            print(f"Audio file generated at: {abs_path}")
            print(f"Audio file size: {file_size} bytes")
            
            # Return the path - Gradio will handle it
            msg_parts = [
                "Song generated successfully!",
                f"File: {abs_path}",
                f"Size: {file_size:,} bytes"
            ]
            msg = "\n".join(msg_parts)
            return msg, abs_path
        else:
            error_msg = "Error: Generated audio file is empty or missing"
            print(error_msg)
            return error_msg, None
            
    except subprocess.CalledProcessError as e:
        error_msg = "Error during generation:\n" + str(e.stderr)
        print(error_msg)
        return error_msg, None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_msg = "Error: " + str(e) + "\n" + tb
        print(error_msg)
        return error_msg, None

def generate_from_audio(lrc_file, audio_file, audio_length, output_dir):
    """Generate song based on LRC and reference audio."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        if lrc_file is None:
            return "Error: Please upload an LRC file first", None
        if audio_file is None:
            return "Error: Please upload a reference audio file first", None
        
        lrc_path = lrc_file.name if hasattr(lrc_file, 'name') else lrc_file
        audio_path = audio_file.name if hasattr(audio_file, 'name') else audio_file
        cmd = f"python3 infer/infer.py --lrc-path {lrc_path} --ref-audio-path {audio_path} --audio-length {audio_length} --output-dir {output_dir} --chunked --batch-infer-num 5"
        
        print(f"Running command: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Command output: {result.stdout}")
        
        # Verify the audio file exists and is not empty
        audio_file_path = os.path.join(output_dir, "output.wav")
        
        if os.path.exists(audio_file_path) and os.path.getsize(audio_file_path) > 0:
            abs_path = os.path.abspath(audio_file_path)
            file_size = os.path.getsize(audio_file_path)
            print(f"Audio file generated at: {abs_path}")
            print(f"Audio file size: {file_size} bytes")
            
            msg_parts = [
                "Song generated successfully!",
                f"File: {abs_path}",
                f"Size: {file_size:,} bytes"
            ]
            msg = "\n".join(msg_parts)
            return msg, abs_path
        else:
            error_msg = "Error: Generated audio file is empty or missing"
            print(error_msg)
            return error_msg, None
            
    except subprocess.CalledProcessError as e:
        error_msg = "Error during generation:\n" + str(e.stderr)
        print(error_msg)
        return error_msg, None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_msg = "Error: " + str(e) + "\n" + tb
        print(error_msg)
        return error_msg, None

if __name__ == "__main__":
    with gr.Blocks(theme="soft", title="DiffRhythm V1.2 WebUI") as demo:
        gr.Markdown("# DiffRhythm V1.2 WebUI")
        with gr.Tab("Generate from Prompt"):
            lrc_input_prompt = gr.File(label="Upload LRC File")
            prompt_input = gr.Textbox(label="Reference Prompt", value="folk, acoustic guitar, harmonica, touching.")
            length_prompt = gr.Slider(label="Audio Length (seconds)", minimum=95, maximum=285, value=180, step=1)
            output_dir_prompt = gr.Textbox(label="Output Directory", value="infer/example/output")
            generate_prompt_btn = gr.Button("Generate")
            output_prompt = gr.Textbox(label="Output")
            audio_preview_prompt = gr.Audio(
                label="Preview and Download Generated Song",
                type="filepath",
                interactive=False,
                autoplay=False,
                show_download_button=True,
                show_share_button=False
            )
            generate_prompt_btn.click(
                fn=generate_from_prompt,
                inputs=[lrc_input_prompt, prompt_input, length_prompt, output_dir_prompt],
                outputs=[output_prompt, audio_preview_prompt]
            )
        with gr.Tab("Generate from Audio"):
            lrc_input_audio = gr.File(label="Upload LRC File")
            audio_input = gr.Audio(label="Upload and Preview Reference Audio (WAV/MP3)", type="filepath", interactive=True)
            length_audio = gr.Slider(label="Audio Length (seconds)", minimum=95, maximum=285, value=180, step=1, interactive=True)
            output_dir_audio = gr.Textbox(label="Output Directory", value="infer/example/output")
            generate_audio_btn = gr.Button("Generate")
            output_audio = gr.Textbox(label="Output")
            audio_preview_audio = gr.Audio(
                label="Preview and Download Generated Song",
                type="filepath",
                interactive=False,
                autoplay=False,
                show_download_button=True,
                show_share_button=False
            )
            generate_audio_btn.click(
                fn=generate_from_audio,
                inputs=[lrc_input_audio, audio_input, length_audio, output_dir_audio],
                outputs=[output_audio, audio_preview_audio]
            )
    # Get the absolute paths for allowed directories
    project_root = os.path.abspath(".")
    infer_dir = os.path.abspath("infer")
    
    print(f"Project root: {project_root}")
    print(f"Infer directory: {infer_dir}")
    print(f"Allowed paths: {[project_root, infer_dir]}")
    
    # Launch with allowed_paths to enable file access
    demo.launch(
        allowed_paths=[project_root, infer_dir],
        share=False,
        server_name="127.0.0.1",
        server_port=7860
    )
