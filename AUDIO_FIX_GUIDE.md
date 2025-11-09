# 音频预览和下载修复指南

## 🔧 修复的问题

### 1. 音频无法预览和播放
**原因**: 
- `gr.Audio` 组件缺少 `type="filepath"` 参数
- 文件路径处理不正确

**解决方案**:
```python
audio_preview = gr.Audio(
    label="Preview and Download Generated Song",
    type="filepath",          # ✅ 必须指定类型
    interactive=False,        # ✅ 禁用上传模式，启用播放模式
    show_download_button=True,
    show_share_button=False
)
```

### 2. 下载时显示安全性错误
**原因**: Gradio 5.x 版本引入了文件访问安全限制，默认不允许访问项目外的文件

**解决方案**:
```python
demo.launch(
    allowed_paths=[
        os.path.abspath("infer"),  # 允许访问 infer 目录
        os.path.abspath(".")       # 允许访问项目根目录
    ],
    share=False
)
```

### 3. 路径处理问题
**修改前**:
```python
return f"Song generated successfully", audio_file  # 相对路径可能导致问题
```

**修改后**:
```python
abs_path = os.path.abspath(audio_file)
return f"Song generated successfully! File size: {size} bytes", abs_path  # 使用绝对路径
```

## 📋 完整修改列表

### 1. `generate_from_prompt()` 函数
- ✅ 添加输出目录自动创建
- ✅ 返回绝对路径
- ✅ 改进状态消息（显示文件大小）

### 2. `generate_from_audio()` 函数
- ✅ 添加输出目录自动创建
- ✅ 返回绝对路径
- ✅ 改进状态消息（显示文件大小）

### 3. Audio 组件配置
- ✅ 添加 `type="filepath"` 参数
- ✅ 设置 `interactive=False`
- ✅ 启用 `show_download_button=True`
- ✅ 禁用 `show_share_button=False`

### 4. Launch 配置
- ✅ 添加 `allowed_paths` 参数
- ✅ 设置 `share=False`

## 🚀 使用方法

### 启动 WebUI
```bash
cd d:\vscode\temp\DiffRhythm-WebUI
python src/webui.py
```

### 测试步骤
1. **上传 LRC 文件**
2. **选择推理模式**:
   - 模式1: 输入文本提示词
   - 模式2: 上传参考音频
3. **点击 Generate 按钮**
4. **等待生成完成**（查看状态消息）
5. **预览音频**: 
   - 音频会自动加载到播放器
   - 点击播放按钮试听
6. **下载音频**:
   - 点击音频播放器右侧的下载图标 📥
   - 文件会下载到浏览器默认下载目录

## ⚠️ 注意事项

### Gradio 版本要求
- 当前版本: `gradio==5.24.0`
- 最低版本: `gradio>=5.0.0`

### 文件格式
- 输出格式: **WAV** (原始格式，无损)
- 输入格式: LRC (歌词), WAV/MP3 (参考音频)

### 路径配置
- 默认输出目录: `infer/example/output`
- 可以在 UI 中自定义输出目录
- 所有路径都会自动转换为绝对路径

### 常见问题

**Q1: 仍然显示安全性错误？**
```
A: 确保启动时包含 allowed_paths 参数。如果修改了输出目录，
   需要在 allowed_paths 中添加该目录的绝对路径。
```

**Q2: 音频播放器显示空白？**
```
A: 检查生成是否成功完成，查看状态消息是否显示文件大小。
   如果显示错误，请查看终端输出的详细错误信息。
```

**Q3: 点击下载后没有反应？**
```
A: 检查浏览器的下载设置，可能被拦截了。
   也可以右键点击播放器，选择"另存为"手动保存。
```

**Q4: Windows 上 python3 命令不存在？**
```
A: 代码中使用了 python3，在 Windows 上可能需要改为 python。
   建议修改为自动检测系统的 Python 命令。
```

## 🔄 Git 分支

当前修改在 **test** 分支上：
```bash
git checkout test
git pull origin test
```

测试无误后可以合并到 main 分支：
```bash
git checkout main
git merge test
git push origin main
```

## 📝 技术细节

### Gradio Audio 组件参数说明

| 参数 | 值 | 说明 |
|-----|-----|------|
| `type` | `"filepath"` | 指定返回文件路径而非音频数据 |
| `interactive` | `False` | 只读模式，禁用上传功能 |
| `show_download_button` | `True` | 显示下载按钮 |
| `show_share_button` | `False` | 隐藏分享按钮 |

### 安全性机制

Gradio 5.x 引入了文件访问白名单机制：
- 默认只允许访问临时目录中的文件
- 需要通过 `allowed_paths` 明确授权其他目录
- 使用绝对路径避免路径遍历攻击

## 📚 参考文档

- [Gradio Audio Component](https://www.gradio.app/docs/gradio/audio)
- [Gradio Security](https://www.gradio.app/guides/security-and-file-access)
- [Gradio 5.0 Migration Guide](https://www.gradio.app/guides/v5-migration)
