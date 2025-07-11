# 视频字幕生成器

使用 OpenAI Whisper 为视频自动生成字幕的 Streamlit 应用程序。

## 功能特点

- 🎬 支持多种视频格式（MP4, AVI, MOV, MKV, WMV, FLV）
- 🤖 使用 OpenAI Whisper 进行高质量语音转录
- ✂️ 智能字幕分段：
  - 在句号和感叹号后自动分段
  - 每段最多 26 个字符（可自定义）
  - 保持单词完整性，避免截断
- 📁 生成两种 SRT 文件：
  - 标准字幕文件（优化后的段落）
  - 原始字幕文件（每个单词一段，便于调试）
- 🖥️ 简洁的 Web 界面
- 📥 一键下载字幕文件

## 安装

1. 克隆或下载此项目
2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动应用：

```bash
streamlit run app.py
```

2. 在浏览器中打开显示的 URL（通常是 http://localhost:8501）

3. 在侧边栏输入你的 OpenAI API Key

4. 上传视频文件

5. 点击"开始生成字幕"

6. 等待处理完成后下载 SRT 字幕文件

## 字幕分段规则

- **标点符号分段**：遇到句号和感叹号后面跟空格（". " 或 "! "）时，会强制分成两个字幕段
- **长度限制**：每个字幕段最多包含 26 个字符（可在侧边栏调整）
- **单词完整性**：如果添加下一个单词会超过字符限制，该单词会移到下一个字幕段

## 输出文件

1. **标准 SRT 文件**：按照上述规则优化分段的字幕文件，适合实际使用
2. **原始 SRT 文件**：每个单词单独一个字幕段，主要用于调试和精确时间定位

## 技术实现

- 使用 `client.audio.translations.create()` 调用 OpenAI Whisper API
- 使用 MoviePy 提取视频中的音频
- 智能文本分割算法确保字幕质量
- Streamlit 提供简洁的用户界面

## 注意事项

- 需要有效的 OpenAI API Key
- 处理大文件可能需要较长时间
- 确保网络连接稳定

## 依赖项

- streamlit: Web 应用框架
- openai: OpenAI API 客户端
- moviepy: 视频处理库
