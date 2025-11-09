import gradio as gr
import os
import subprocess
import shutil
from pathlib import Path

def generate_from_prompt(lrc_file, prompt, audio_length, output_dir):
    """Generate song based on LRC and text prompt."""
    try:
        # Ensure output directory is within project
        if not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        if lrc_file is None:
            return "❌ Error: Please upload an LRC file first", None, None
        
        lrc_path = lrc_file.name if hasattr(lrc_file, 'name') else lrc_file
        cmd = f"python3 infer/infer.py --lrc-path {lrc_path} --ref-prompt \"{prompt}\" --audio-length {audio_length} --output-dir {output_dir} --chunked --batch-infer-num 5"
        
        print(f"Running command: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Command output: {result.stdout}")
        
        wav_file = os.path.join(output_dir, "output.wav")
        mp3_file = os.path.join(output_dir, "output.mp3")
        
        # Verify the WAV file exists and is not empty
        if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
            wav_size = os.path.getsize(wav_file)
            print(f"WAV file generated at: {wav_file}")
            print(f"WAV file size: {wav_size} bytes")
            
            # Convert WAV to MP3 using ffmpeg
            try:
                ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libmp3lame -qscale:a 2 \"{mp3_file}\""
                print(f"Converting to MP3: {ffmpeg_cmd}")
                subprocess.run(ffmpeg_cmd, shell=True, check=True, capture_output=True, text=True)
                
                if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 0:
                    mp3_size = os.path.getsize(mp3_file)
                    print(f"MP3 file created at: {mp3_file}")
                    print(f"MP3 file size: {mp3_size} bytes")
                    
                    # Return both for Audio preview and File download
                    msg_parts = [
                        "✅ Song generated successfully!",
                        f"📁 File: {mp3_file}",
                        f"📊 Size: {mp3_size:,} bytes ({mp3_size / 1024 / 1024:.2f} MB)"
                    ]
                    msg = "\n".join(msg_parts)
                    return msg, mp3_file, mp3_file
                else:
                    print("Warning: MP3 conversion failed, returning WAV file")
                    msg_parts = [
                        "⚠️ Song generated (WAV only, MP3 conversion failed)",
                        f"📁 WAV File: {wav_file}",
                        f"📊 Size: {wav_size:,} bytes ({wav_size / 1024 / 1024:.2f} MB)"
                    ]
                    msg = "\n".join(msg_parts)
                    return msg, wav_file, wav_file
                    
            except Exception as conv_error:
                print(f"MP3 conversion error: {conv_error}")
                print("Returning WAV file instead")
                msg_parts = [
                    "⚠️ Song generated (WAV only, MP3 conversion failed)",
                    f"📁 WAV File: {wav_file}",
                    f"📊 Size: {wav_size:,} bytes ({wav_size / 1024 / 1024:.2f} MB)"
                ]
                msg = "\n".join(msg_parts)
                return msg, wav_file, wav_file
        else:
            error_msg = "❌ Error: Generated audio file is empty or missing"
            print(error_msg)
            return error_msg, None, None
            
    except subprocess.CalledProcessError as e:
        error_msg = "❌ Error during generation:\n" + str(e.stderr)
        print(error_msg)
        return error_msg, None, None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_msg = "❌ Error: " + str(e) + "\n" + tb
        print(error_msg)
        return error_msg, None, None

def generate_from_audio(lrc_file, audio_file, audio_length, output_dir):
    """Generate song based on LRC and reference audio."""
    try:
        # Ensure output directory is within project
        if not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        if lrc_file is None:
            return "❌ Error: Please upload an LRC file first", None, None
        if audio_file is None:
            return "Error: Please upload a reference audio file first", None
        
        lrc_path = lrc_file.name if hasattr(lrc_file, 'name') else lrc_file
        audio_path = audio_file.name if hasattr(audio_file, 'name') else audio_file
        cmd = f"python3 infer/infer.py --lrc-path {lrc_path} --ref-audio-path {audio_path} --audio-length {audio_length} --output-dir {output_dir} --chunked --batch-infer-num 5"
        
        print(f"Running command: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Command output: {result.stdout}")
        
        wav_file = os.path.join(output_dir, "output.wav")
        mp3_file = os.path.join(output_dir, "output.mp3")
        
        # Verify the WAV file exists and is not empty
        if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
            wav_size = os.path.getsize(wav_file)
            print(f"WAV file generated at: {wav_file}")
            print(f"WAV file size: {wav_size} bytes")
            
            # Convert WAV to MP3 using ffmpeg
            try:
                ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libmp3lame -qscale:a 2 \"{mp3_file}\""
                print(f"Converting to MP3: {ffmpeg_cmd}")
                subprocess.run(ffmpeg_cmd, shell=True, check=True, capture_output=True, text=True)
                
                if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 0:
                    mp3_size = os.path.getsize(mp3_file)
                    print(f"MP3 file created at: {mp3_file}")
                    print(f"MP3 file size: {mp3_size} bytes")
                    
                    # Return both for Audio preview and File download
                    msg_parts = [
                        "✅ Song generated successfully!",
                        f"📁 File: {mp3_file}",
                        f"📊 Size: {mp3_size:,} bytes ({mp3_size / 1024 / 1024:.2f} MB)"
                    ]
                    msg = "\n".join(msg_parts)
                    return msg, mp3_file, mp3_file
                else:
                    print("Warning: MP3 conversion failed, returning WAV file")
                    msg_parts = [
                        "⚠️ Song generated (WAV only, MP3 conversion failed)",
                        f"📁 WAV File: {wav_file}",
                        f"📊 Size: {wav_size:,} bytes ({wav_size / 1024 / 1024:.2f} MB)"
                    ]
                    msg = "\n".join(msg_parts)
                    return msg, wav_file, wav_file
                    
            except Exception as conv_error:
                print(f"MP3 conversion error: {conv_error}")
                print("Returning WAV file instead")
                msg_parts = [
                    "⚠️ Song generated (WAV only, MP3 conversion failed)",
                    f"📁 WAV File: {wav_file}",
                    f"📊 Size: {wav_size:,} bytes ({wav_size / 1024 / 1024:.2f} MB)"
                ]
                msg = "\n".join(msg_parts)
                return msg, wav_file, wav_file
        else:
            error_msg = "❌ Error: Generated audio file is empty or missing"
            print(error_msg)
            return error_msg, None, None
            
    except subprocess.CalledProcessError as e:
        error_msg = "❌ Error during generation:\n" + str(e.stderr)
        print(error_msg)
        return error_msg, None, None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_msg = "❌ Error: " + str(e) + "\n" + tb
        print(error_msg)
        return error_msg, None, None

if __name__ == "__main__":
    with gr.Blocks(theme="soft", title="DiffRhythm V1.2 WebUI") as demo:
        gr.Markdown("# DiffRhythm V1.2 WebUI")
        with gr.Tab("Generate from Prompt"):
            lrc_input_prompt = gr.File(label="Upload LRC File")
            prompt_input = gr.Textbox(label="Reference Prompt", value="folk, acoustic guitar, harmonica, touching.")
            length_prompt = gr.Slider(label="Audio Length (seconds)", minimum=95, maximum=285, value=180, step=1)
            output_dir_prompt = gr.Textbox(label="Output Directory", value="infer/example/output")
            generate_prompt_btn = gr.Button("Generate", variant="primary")
            output_prompt = gr.Textbox(label="Status", lines=3)
            
            with gr.Row():
                with gr.Column():
                    audio_preview_prompt = gr.Audio(
                        label="🎧 Audio Preview (if browser supports)",
                        type="filepath",
                        interactive=False,
                        show_label=True
                    )
                with gr.Column():
                    download_file_prompt = gr.File(
                        label="📥 Download Generated Song (Right-click → Save As)",
                        show_label=True
                    )
            
            generate_prompt_btn.click(
                fn=generate_from_prompt,
                inputs=[lrc_input_prompt, prompt_input, length_prompt, output_dir_prompt],
                outputs=[output_prompt, audio_preview_prompt, download_file_prompt]
            )
        with gr.Tab("Generate from Audio"):
            lrc_input_audio = gr.File(label="Upload LRC File")
            audio_input = gr.Audio(label="Upload Reference Audio (WAV/MP3)", type="filepath", interactive=True)
            length_audio = gr.Slider(label="Audio Length (seconds)", minimum=95, maximum=285, value=180, step=1)
            output_dir_audio = gr.Textbox(label="Output Directory", value="infer/example/output")
            generate_audio_btn = gr.Button("Generate", variant="primary")
            output_audio = gr.Textbox(label="Status", lines=3)
            
            with gr.Row():
                with gr.Column():
                    audio_preview_audio = gr.Audio(
                        label="🎧 Audio Preview (if browser supports)",
                        type="filepath",
                        interactive=False,
                        show_label=True
                    )
                with gr.Column():
                    download_file_audio = gr.File(
                        label="📥 Download Generated Song (Right-click → Save As)",
                        show_label=True
                    )
            
            generate_audio_btn.click(
                fn=generate_from_audio,
                inputs=[lrc_input_audio, audio_input, length_audio, output_dir_audio],
                outputs=[output_audio, audio_preview_audio, download_file_audio]
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
