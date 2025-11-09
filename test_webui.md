# WebUI 修复说明

## 🔧 修复内容

### 问题 1: 音频无法预览
**原因**: `gr.Audio` 组件设置了 `interactive=True`，导致组件进入上传模式而非播放模式
**修复**: 将输出音频组件设置为 `interactive=False`

### 问题 2: 点击下载按钮跳转到新标签页
**原因**: 
1. 旧版本使用了过时的 `format="mp3"` 参数
2. 使用绝对路径可能导致浏览器直接打开而非下载
**修复**: 
1. 移除 `format` 参数，直接返回 WAV 文件路径
2. 启用 `show_download_button=True`，禁用 `show_share_button=False`
3. Gradio 会自动处理下载逻辑

### 问题 3: Windows 兼容性
**原因**: 硬编码使用 `python3` 命令，在 Windows 上不存在
**修复**: 添加 `get_python_cmd()` 函数自动检测操作系统

### 问题 4: 错误处理不完善
**原因**: 未检查文件上传状态，未捕获子进程错误输出
**修复**: 
1. 添加输入验证（检查 LRC 和音频文件是否上传）
2. 使用 `capture_output=True` 捕获错误信息
3. 添加详细的错误追踪（traceback）

### 问题 5: generate_from_audio 函数缺少 WAV 转换
**原因**: 第二个标签页的函数直接查找 MP3 文件，但 infer.py 只生成 WAV
**修复**: 统一返回 WAV 文件，移除 ffmpeg 转换步骤

## ✨ 新增功能

1. **美化界面**: 
   - 添加 emoji 图标
   - 使用双列布局
   - 添加使用提示
   - 显示生成文件大小

2. **更好的状态反馈**:
   - 显示详细的错误信息
   - 显示成功消息和文件大小
   - 保留命令行输出用于调试

3. **配置优化**:
   - 服务器监听所有接口 (`0.0.0.0`)
   - 固定端口 7860
   - 自动创建输出目录

## 🚀 使用方法

启动 WebUI:
```bash
python src/webui.py
```

访问地址: http://localhost:7860

## 📋 核心修改对比

### 旧代码问题:
```python
audio_preview_prompt = gr.Audio(
    label="Preview and Download Generated Song",
    type="filepath",
    interactive=True,  # ❌ 错误: 会变成上传模式
    visible=True,
    format="mp3"  # ❌ 过时参数
)
```

### 新代码:
```python
audio_preview_prompt = gr.Audio(
    label="🎧 Preview & Download",
    interactive=False,  # ✅ 正确: 只播放不上传
    show_download_button=True,  # ✅ 显示下载按钮
    show_share_button=False  # ✅ 隐藏分享按钮
)
# 返回 WAV 文件路径，Gradio 自动处理播放和下载
```

## ⚠️ 注意事项

1. **文件格式**: 现在返回 WAV 格式（原生格式），无需 ffmpeg 转换
2. **下载方式**: 点击音频播放器右侧的下载图标按钮即可下载
3. **预览功能**: 音频会自动加载到播放器中，可以直接播放
4. **路径处理**: 确保在项目根目录运行 `python src/webui.py`

## 🧪 测试清单

- [ ] 上传 LRC 文件
- [ ] 输入风格提示词 / 上传参考音频
- [ ] 点击生成按钮
- [ ] 等待生成完成
- [ ] 查看状态信息（是否显示成功消息和文件大小）
- [ ] 播放音频（点击播放按钮）
- [ ] 下载音频（点击下载图标）
- [ ] 验证下载的文件可以正常播放
