"""
测试Gradio Audio组件的预览和下载功能
"""
import gradio as gr
import os

def test_audio_display():
    """测试音频显示功能"""
    # 使用项目中已存在的音频文件
    test_file = os.path.abspath("infer/example/eg_cn.wav")
    
    if os.path.exists(test_file):
        file_size = os.path.getsize(test_file)
        return f"✓ Test file loaded!\nPath: {test_file}\nSize: {file_size:,} bytes", test_file
    else:
        return "✗ Test file not found", None

if __name__ == "__main__":
    # 获取项目根目录和infer目录的绝对路径
    project_root = os.path.abspath(".")
    infer_dir = os.path.abspath("infer")
    
    print(f"Project root: {project_root}")
    print(f"Infer directory: {infer_dir}")
    print(f"Test file: {os.path.abspath('infer/example/eg_cn.wav')}")
    
    with gr.Blocks(title="Audio Player Test") as demo:
        gr.Markdown("# 🎵 Gradio Audio Component Test")
        gr.Markdown("This test loads an existing audio file to verify preview and download functionality.")
        
        with gr.Row():
            with gr.Column():
                test_btn = gr.Button("🔄 Load Test Audio", variant="primary")
                status_text = gr.Textbox(label="Status", lines=3)
            
            with gr.Column():
                # 测试方法1: type="filepath" + interactive=False
                audio_player_1 = gr.Audio(
                    label="Method 1: filepath + non-interactive",
                    type="filepath",
                    interactive=False,
                    autoplay=False,
                    show_download_button=True,
                    show_share_button=False
                )
        
        with gr.Row():
            with gr.Column():
                # 测试方法2: 不指定type
                audio_player_2 = gr.Audio(
                    label="Method 2: auto type + non-interactive",
                    interactive=False,
                    autoplay=False,
                    show_download_button=True,
                    show_share_button=False
                )
            
            with gr.Column():
                # 测试方法3: type="numpy"
                audio_player_3 = gr.Audio(
                    label="Method 3: numpy type + non-interactive",
                    type="numpy",
                    interactive=False,
                    autoplay=False,
                    show_download_button=True,
                    show_share_button=False
                )
        
        # 绑定事件
        test_btn.click(
            fn=test_audio_display,
            inputs=[],
            outputs=[status_text, audio_player_1]
        )
        
        # 也尝试更新其他播放器
        test_btn.click(
            fn=test_audio_display,
            inputs=[],
            outputs=[status_text, audio_player_2]
        )
    
    # 启动时允许访问项目目录
    demo.launch(
        allowed_paths=[project_root, infer_dir],
        share=False,
        server_name="127.0.0.1",
        server_port=7861  # 使用不同的端口避免冲突
    )
