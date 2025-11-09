# 🔍 音频预览和下载问题调试指南

## 问题现状

1. **音频无法预览**: 生成后的WAV文件不能在浏览器中播放
2. **下载显示安全错误**: 点击下载按钮时浏览器提示"无法安全下载"

## 已实施的修复

### 第一轮修复 (已完成)
- ✅ 添加 `type="filepath"` 参数
- ✅ 设置 `interactive=False`
- ✅ 添加 `allowed_paths` 到 `demo.launch()`
- ✅ 使用绝对路径返回音频文件

### 第二轮修复 (当前版本)
- ✅ 添加详细的错误处理和日志
- ✅ 添加输入验证
- ✅ 添加 `autoplay=False` 参数
- ✅ 添加 `waveform_options` 参数
- ✅ 明确指定 `server_name` 和 `server_port`
- ✅ 打印 allowed_paths 用于调试

## 🧪 测试步骤

### 1. 测试单独的音频播放器

运行测试脚本来验证Gradio Audio组件本身是否工作：

```bash
python test_audio_player.py
```

访问 http://127.0.0.1:7861 并：
1. 点击 "Load Test Audio" 按钮
2. 查看是否能在三个不同配置的播放器中预览音频
3. 尝试点击下载按钮

**如果测试脚本可以正常工作**，说明问题在于生成流程；如果也不行，说明是Gradio配置或浏览器问题。

### 2. 测试完整的WebUI

```bash
python src/webui.py
```

查看终端输出，应该会显示：
```
Project root: D:\vscode\temp\DiffRhythm-WebUI
Infer directory: D:\vscode\temp\DiffRhythm-WebUI\infer
Allowed paths: [...]
```

## 🔍 可能的原因分析

### A. Gradio 版本兼容性问题

**检查方法**:
```bash
pip show gradio
```

当前项目使用 `gradio==5.24.0`，这是一个较新的版本。

**可能的解决方案**:
1. 尝试降级到稳定版本:
   ```bash
   pip install gradio==4.44.0
   ```

2. 或者升级到最新版本:
   ```bash
   pip install --upgrade gradio
   ```

### B. 浏览器安全策略

**问题**: 现代浏览器对本地文件下载有严格的安全限制

**检查方法**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 Console 标签
3. 查看是否有安全相关的错误信息
4. 切换到 Network 标签
5. 尝试播放/下载，查看请求状态

**可能看到的错误**:
- CORS 错误
- Mixed Content 错误
- CSP (Content Security Policy) 错误

**解决方案**:
- 使用 Chrome/Edge: 启动时添加 `--disable-web-security` 标志（仅用于测试）
- 检查文件路径是否包含特殊字符
- 确保使用 http://127.0.0.1 而不是 localhost

### C. WAV文件本身的问题

**检查方法**:
1. 手动打开生成的WAV文件:
   ```
   D:\vscode\temp\DiffRhythm-WebUI\infer\example\output\output.wav
   ```
2. 使用VLC、Windows Media Player等播放器测试
3. 检查文件是否损坏

**如果文件无法在本地播放器中打开**，说明生成过程有问题。

### D. Gradio 文件服务问题

**可能的问题**:
- Gradio 的内部文件服务器可能不正确处理某些路径
- `allowed_paths` 配置可能不够

**解决方案 1**: 使用相对路径而非绝对路径
```python
# 在函数中返回相对于项目根目录的路径
rel_path = os.path.relpath(abs_path, start=os.getcwd())
return message, rel_path
```

**解决方案 2**: 完全禁用路径限制（仅用于调试）
```python
demo.launch(
    allowed_paths=None,  # 禁用路径限制
    share=False
)
```

**解决方案 3**: 使用Gradio的临时文件目录
```python
import tempfile

# 复制文件到Gradio临时目录
temp_dir = tempfile.gettempdir()
temp_file = os.path.join(temp_dir, "output.wav")
shutil.copy(audio_file, temp_file)
return message, temp_file
```

## 🛠️ 备选方案

### 方案1: 使用Base64编码

将音频文件转换为Base64字符串：

```python
import base64

def audio_to_base64(file_path):
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    audio_base64 = base64.b64encode(audio_bytes).decode()
    return f"data:audio/wav;base64,{audio_base64}"

# 在函数中使用
audio_data = audio_to_base64(abs_path)
return message, audio_data
```

配合修改Audio组件:
```python
audio_preview = gr.Audio(
    type="numpy",  # 或不指定type
    ...
)
```

### 方案2: 使用外部静态文件服务器

启动一个简单的HTTP服务器：

```python
import http.server
import socketserver
import threading

def start_file_server(directory, port=8000):
    Handler = http.server.SimpleHTTPRequestHandler
    os.chdir(directory)
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving files at http://localhost:{port}")
        httpd.serve_forever()

# 在后台启动文件服务器
threading.Thread(
    target=start_file_server,
    args=(os.path.abspath("infer/example/output"), 8000),
    daemon=True
).start()

# 返回HTTP URL而非文件路径
return message, "http://localhost:8000/output.wav"
```

### 方案3: 转换为MP3格式

某些浏览器对MP3的支持可能比WAV更好：

```python
import subprocess

def convert_to_mp3(wav_path):
    mp3_path = wav_path.replace('.wav', '.mp3')
    subprocess.run([
        'ffmpeg', '-i', wav_path,
        '-codec:a', 'libmp3lame',
        '-qscale:a', '2',
        mp3_path
    ], check=True)
    return mp3_path

# 使用
mp3_file = convert_to_mp3(audio_file)
return message, mp3_file
```

### 方案4: 添加手动下载按钮

除了Audio组件的下载按钮，添加一个独立的File组件：

```python
# 在UI中添加
download_file = gr.File(label="Download Generated Song")

# 在函数中返回
return message, abs_path, abs_path  # 同时更新Audio和File组件
```

## 📋 推荐的调试顺序

1. **运行测试脚本** (`test_audio_player.py`)
   - 如果成功 → 问题在生成流程
   - 如果失败 → 继续下一步

2. **检查浏览器控制台**
   - 打开F12开发者工具
   - 查看Console和Network标签
   - 记录所有错误信息

3. **测试手动打开音频文件**
   - 在文件资源管理器中找到生成的WAV文件
   - 双击打开
   - 确认文件本身没问题

4. **尝试降级/升级Gradio**
   - 先试 `gradio==4.44.0`（稳定版本）
   - 如果不行，试最新版

5. **尝试备选方案**
   - 方案2: 外部HTTP服务器（最简单）
   - 方案4: 添加File组件（最可靠）
   - 方案3: 转换为MP3（兼容性最好）

## 💡 立即可尝试的快速修复

### 快速修复1: 使用File组件代替Audio组件

```python
# 修改 webui.py
download_file = gr.File(label="Download Generated Song")
audio_preview = gr.Audio(label="Preview (if supported)")

# 返回两个组件
return message, abs_path, abs_path
```

这样即使预览失败，至少下载功能是可用的。

### 快速修复2: 完全移除allowed_paths限制

```python
demo.launch(
    share=False,
    server_name="127.0.0.1",
    server_port=7860
    # 不设置 allowed_paths
)
```

如果这样可以工作，说明是路径权限问题。

### 快速修复3: 使用相对路径

```python
# 在返回时使用相对路径
rel_path = os.path.relpath(abs_path, start=project_root)
return message, rel_path
```

## 📞 需要提供的调试信息

如果以上方法都不行，请提供：

1. **Python版本**: `python --version`
2. **Gradio版本**: `pip show gradio`
3. **操作系统**: Windows版本
4. **浏览器**: 名称和版本
5. **控制台错误**: F12开发者工具中的所有错误信息
6. **终端输出**: WebUI启动后的完整输出
7. **测试结果**: `test_audio_player.py` 的运行结果
8. **文件检查**: 手动打开 `output.wav` 是否可以播放

## 🎯 下一步行动

1. 运行 `test_audio_player.py` 测试
2. 查看浏览器F12控制台
3. 根据结果选择对应的解决方案
