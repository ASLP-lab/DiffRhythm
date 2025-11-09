# 🚀 快速测试指南

## 前置要求

### 1. 安装ffmpeg
```bash
# Windows (PowerShell 管理员模式)
choco install ffmpeg

# 或从官网下载: https://ffmpeg.org/download.html
# 解压后将bin目录添加到系统PATH
```

### 2. 验证ffmpeg
```bash
ffmpeg -version
```
应该看到版本信息和 `libmp3lame` 支持。

## 🧪 测试步骤

### 步骤1: 启动WebUI
```bash
cd D:\vscode\temp\DiffRhythm-WebUI
python src/webui.py
```

**期望输出**:
```
Project root: D:\vscode\temp\DiffRhythm-WebUI
Infer directory: D:\vscode\temp\DiffRhythm-WebUI\infer
Allowed paths: [...]
Running on local URL:  http://127.0.0.1:7860
```

### 步骤2: 访问Web界面
在浏览器中打开: http://127.0.0.1:7860

### 步骤3: 测试音频播放器（独立测试）
在另一个终端:
```bash
python test_audio_player.py
```
访问 http://127.0.0.1:7861

点击 "Load Test Audio" 按钮，查看是否能:
- ✅ 显示音频长度（不是0）
- ✅ 播放音频
- ✅ 下载文件

**如果测试脚本可以工作**，说明Gradio配置正确。

### 步骤4: 测试完整生成流程

**使用已存在的示例文件**:
1. 上传 LRC: `infer/example/eg_cn.lrc`
2. 模式1: 使用默认提示词
3. 输出目录: `infer/example/output`
4. 点击 Generate

**查看终端输出**，应该看到:
```
Running command: python3 infer/infer.py ...
Command output: ...
WAV file generated at: D:\vscode\temp\DiffRhythm-WebUI\infer\example\output\output.wav
WAV file size: 15234432 bytes
Converting to MP3: ffmpeg -y -i "..." ...
MP3 file created at: D:\vscode\temp\DiffRhythm-WebUI\infer\example\output\output.mp3
MP3 file size: 1456789 bytes
```

**在UI中应该看到**:
- Output文本框显示成功消息和文件路径
- Audio组件显示音频波形（不是空白）
- 显示正确的音频长度（约3分钟）

### 步骤5: 测试预览和下载

**预览**:
- 点击Audio组件的播放按钮 ▶️
- 应该可以听到音频

**下载**:
- 点击Audio组件右侧的下载按钮 📥
- 文件应该下载到浏览器默认下载目录
- 文件名: `output.mp3`

**验证下载的文件**:
- 双击下载的MP3文件
- 应该可以在本地播放器中播放

## ✅ 成功标准

- [ ] ffmpeg可用
- [ ] WebUI成功启动
- [ ] test_audio_player.py可以播放音频
- [ ] 生成过程完成无错误
- [ ] WAV成功转换为MP3
- [ ] Audio组件显示正确的长度
- [ ] 可以在浏览器中播放预览
- [ ] 可以下载MP3文件
- [ ] 下载的文件可以播放

## ❌ 如果失败

### 问题: ffmpeg不可用
```
Error: ffmpeg 不是内部或外部命令
```
**解决**: 安装ffmpeg并添加到PATH

### 问题: MP3转换失败但WAV成功
```
Song generated (WAV only, MP3 conversion failed)
```
**解决**: 
1. 检查ffmpeg是否支持libmp3lame
2. 查看终端的详细错误信息
3. 手动测试: `ffmpeg -i infer/example/eg_cn.wav test.mp3`

### 问题: 音频长度显示0
**可能原因**:
1. 文件路径Gradio无法访问
2. 文件格式问题
3. Gradio版本问题

**调试**:
1. 打开F12开发者工具 → Console标签
2. 查看是否有错误
3. 切换到Network标签，查看文件请求状态
4. 手动打开文件: `infer/example/output/output.mp3`

### 问题: 仍然无法下载
**临时解决方案**:
1. 手动从文件夹复制文件
2. 使用右键 → 另存为
3. 检查浏览器下载设置

## 📝 报告问题

如果测试失败，请提供:
1. **Python版本**: `python --version`
2. **Gradio版本**: `pip show gradio`
3. **ffmpeg版本**: `ffmpeg -version`
4. **操作系统**: Windows版本
5. **浏览器**: 名称和版本
6. **终端输出**: 完整的错误信息
7. **浏览器F12**: Console中的错误
8. **测试结果**: 哪些步骤失败了

## 🔄 回滚方案

如果新版本不工作，可以回退到之前的版本:

```bash
# 查看提交历史
git log --oneline

# 回退到上一个版本
git checkout <commit-hash>

# 或切换回main分支
git checkout main
```

## 🎯 预期结果

如果一切正常，你应该能够:
1. ✅ 生成歌曲（WAV → MP3）
2. ✅ 在浏览器中预览MP3
3. ✅ 下载MP3到本地
4. ✅ 播放下载的MP3文件

文件位置: `infer/example/output/output.mp3`
