# MP3转换更新说明

## 🎵 更新内容

已将WebUI输出格式从WAV改为MP3，以提高浏览器兼容性和下载便利性。

## ✨ 主要改进

### 1. 自动WAV到MP3转换
- 生成的WAV文件会自动转换为MP3格式
- 使用ffmpeg进行高质量转换 (VBR quality 2)
- 如果ffmpeg转换失败，会回退到WAV文件

### 2. 文件位置
- **输出路径**: `infer/example/output/output.mp3`
- 文件保存在项目内部，确保Gradio可以访问
- 同时保留原始WAV文件 (output.wav)

### 3. 错误处理
- 完善的ffmpeg错误捕获
- 转换失败时自动降级到WAV
- 详细的日志输出便于调试

## 🔧 技术细节

### ffmpeg命令
```bash
ffmpeg -y -i "output.wav" -codec:a libmp3lame -qscale:a 2 "output.mp3"
```

**参数说明**:
- `-y`: 自动覆盖已存在文件
- `-codec:a libmp3lame`: 使用LAME MP3编码器
- `-qscale:a 2`: VBR质量等级2 (范围0-9，2为高质量)

### 输出示例
```
WAV file generated at: D:\vscode\temp\DiffRhythm-WebUI\infer\example\output\output.wav
WAV file size: 15,234,432 bytes
Converting to MP3: ffmpeg -y -i "..." -codec:a libmp3lame -qscale:a 2 "..."
MP3 file created at: D:\vscode\temp\DiffRhythm-WebUI\infer\example\output\output.mp3
MP3 file size: 1,456,789 bytes
Song generated successfully!
MP3 File: D:\vscode\temp\DiffRhythm-WebUI\infer\example\output\output.mp3
Size: 1,456,789 bytes
```

## 📦 依赖要求

### 必需软件
- **ffmpeg**: 必须安装并在系统PATH中

### 安装ffmpeg

**Windows**:
```bash
# 使用chocolatey
choco install ffmpeg

# 或下载预编译版本
# https://ffmpeg.org/download.html
```

**Linux**:
```bash
sudo apt-get install ffmpeg  # Debian/Ubuntu
sudo yum install ffmpeg      # CentOS/RHEL
```

**macOS**:
```bash
brew install ffmpeg
```

### 验证ffmpeg安装
```bash
ffmpeg -version
```

## 🎯 使用方法

### 正常流程
1. 上传LRC文件
2. 选择推理模式 (文本提示词 或 参考音频)
3. 点击Generate按钮
4. 等待生成完成
5. **自动转换为MP3**
6. 在Audio组件中预览
7. 点击下载按钮下载MP3文件

### 转换失败的情况
如果ffmpeg不可用或转换失败:
- 会显示警告消息
- 自动回退到WAV文件
- 仍然可以预览和下载 (WAV格式)

## 🔍 故障排除

### 问题1: MP3转换失败
**症状**: 看到消息 "Song generated (WAV only, MP3 conversion failed)"

**可能原因**:
1. ffmpeg未安装或不在PATH中
2. ffmpeg版本过旧，不支持libmp3lame
3. 磁盘空间不足

**解决方案**:
```bash
# 1. 检查ffmpeg是否可用
ffmpeg -version

# 2. 检查是否支持MP3
ffmpeg -encoders | grep mp3

# 3. 重新安装ffmpeg
# 按上述安装说明操作
```

### 问题2: 仍然无法预览
**可能原因**:
1. Gradio无法访问文件路径
2. 浏览器不支持音频预览
3. 文件损坏

**解决方案**:
1. 检查文件是否真的存在:
   ```
   infer/example/output/output.mp3
   ```
2. 手动用播放器打开文件测试
3. 查看浏览器F12控制台的错误信息
4. 尝试不同的浏览器

### 问题3: 下载仍然失败
**症状**: 点击下载按钮显示"无法安全下载"

**解决方案**:
1. 确保文件在项目目录内
2. 检查Gradio的allowed_paths配置
3. 尝试在浏览器中禁用下载安全检查 (仅用于测试)
4. 手动从文件夹复制文件

## 📊 文件大小对比

典型180秒歌曲:
- **WAV** (44.1kHz, 16bit): ~15-20 MB
- **MP3** (VBR Q2, ~190kbps): ~1.5-2.5 MB

**压缩比**: 约 8:1 到 10:1

## ⚙️ 高级配置

### 自定义MP3质量

编辑 `src/webui.py`，修改 `-qscale:a` 参数:

```python
# 当前 (高质量)
ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libmp3lame -qscale:a 2 \"{mp3_file}\""

# 最高质量
ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libmp3lame -qscale:a 0 \"{mp3_file}\""

# 标准质量 (更小文件)
ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libmp3lame -qscale:a 4 \"{mp3_file}\""

# 固定比特率 320kbps
ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libmp3lame -b:a 320k \"{mp3_file}\""
```

### 更改输出格式为其他格式

如果想要OGG或AAC:

```python
# OGG Vorbis
ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a libvorbis -qscale:a 5 \"{ogg_file}\""

# AAC
ffmpeg_cmd = f"ffmpeg -y -i \"{wav_file}\" -codec:a aac -b:a 192k \"{m4a_file}\""
```

## 🧪 测试清单

- [ ] ffmpeg已安装
- [ ] 可以生成WAV文件
- [ ] WAV自动转换为MP3
- [ ] MP3文件可以手动播放
- [ ] Gradio Audio组件显示音频长度
- [ ] 可以在浏览器中播放预览
- [ ] 下载按钮可以下载MP3文件
- [ ] 下载的MP3文件可以正常播放

## 📝 更新日志

### 2025-11-09
- ✅ 添加自动WAV到MP3转换
- ✅ 确保输出文件在项目目录内
- ✅ 添加转换失败的回退机制
- ✅ 改进错误处理和日志输出

## 🔗 相关文档

- [AUDIO_FIX_GUIDE.md](./AUDIO_FIX_GUIDE.md) - 音频修复指南
- [DEBUG_AUDIO_ISSUE.md](./DEBUG_AUDIO_ISSUE.md) - 调试指南
- [test_audio_player.py](./test_audio_player.py) - 测试工具
