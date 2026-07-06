# Smart Scribe

Smart Scribe 把短视频、音频、图片和链接整理成可追溯的数字知识卡片，并导出为适合 Obsidian 的 Markdown。

它的核心定位不是会议录制，也不是通用网盘转写工具，而是：

> 短视频/素材 -> 证据化整理 -> AI 总结 -> Obsidian 知识基础

## 为什么做

很多有价值的信息藏在短视频里：项目介绍、工具教程、课程片段、评论区截图、演示画面。普通总结工具常常只能处理语音，容易漏掉画面里的项目名、链接、术语和关键截图。

Smart Scribe 的思路是先把素材拆成可追溯证据块，再让 AI 基于证据生成总结。每个结论都能回到原始语音时间点或画面帧。

## 核心能力

### 1. 链接和本地素材都能处理

- 粘贴抖音、Bilibili、YouTube 或直链。
- 上传本地视频、音频、图片。
- 同一个会话可以继续追加素材。
- 追加素材后会自动重新生成总结，不需要用户手动点“重新生成”。

### 2. 画面 OCR 和语音 ASR 同时作为证据

- 视频抽帧后做 OCR，生成 `P001`、`P002` 这样的画面证据块。
- 音频/视频转写后生成 `S001`、`S002` 这样的语音证据块。
- AI 总结时同时阅读画面和语音。
- 当语音转写和画面文字冲突时，优先以画面 OCR 为准。

### 3. 覆盖率优先的智能抽帧

Smart Scribe 会自动判断视频类型：

- PPT/课程类：保守抽帧，减少重复 OCR。
- 抖音/评论/混剪类：覆盖率优先，按时间分桶保留更多画面。
- 长视频：抽帧预算会按时长和场景数量动态增长，最高受控，避免 OCR 成本失控。

处理日志会记录每个候选帧为什么保留或丢弃，便于调试抽帧质量。

### 4. 手动选帧补充

自动抽帧漏掉重点时，可以在播放器里手动选帧。手动选帧会作为“用户重点追加”进入总结提示词，避免被旧内容淹没。

### 5. Obsidian Markdown 导出

导出的 Markdown 包含：

- YAML frontmatter
- AI 摘要
- 核心要点和证据引用
- 来源链接
- 证据索引
- 可折叠详细原文

目标是让结果可以直接进入 Obsidian，而不是还需要大量二次清洗。

## 典型工作流

1. 粘贴视频链接或上传素材。
2. Smart Scribe 自动下载、抽帧、OCR、转写。
3. 生成可引用的证据块时间线。
4. AI 生成带引用的摘要和要点。
5. 发现漏掉画面时，手动选帧补充。
6. 系统自动重新生成总结。
7. 复制 Markdown 到 Obsidian。

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 后端 | FastAPI, SQLAlchemy, SQLite, ffmpeg |
| 前端 | React, Vite, TypeScript, Tailwind CSS, TanStack Query |
| OCR | PaddleOCR Cloud 或本地 PaddleOCR |
| ASR | DashScope / Fun-ASR |
| AI 总结 | DeepSeek |
| 导出 | Obsidian-compatible Markdown |

## 快速开始

### Windows 一键启动

```powershell
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
./start-windows.bat
```

首次运行会安装或检查 Python、Node.js、ffmpeg、cloudflared，创建后端虚拟环境，安装依赖并构建前端。启动后打开：

```text
http://localhost:8000
```

### Docker

```bash
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
docker compose up --build
```

Docker 镜像会先构建前端，再由后端统一托管页面和接口。启动后打开：

```text
http://localhost:8000
```

## API Key

打开应用右上角设置，填写：

- `deepseek_api_key`：用于 AI 总结。
- `dashscope_api_key`：用于语音转写。
- `paddleocr_cloud_key`：用于云端 OCR。
- `dashscope_workspace_id`：可选。
- `ytdlp_cookie_path`：可选，用于需要登录的视频源。

也可以通过环境变量配置：

```dotenv
SMART_SCRIBE_DEEPSEEK_API_KEY=sk-xxx
SMART_SCRIBE_DASHSCOPE_API_KEY=sk-xxx
SMART_SCRIBE_PADDLEOCR_CLOUD_KEY=xxx
SMART_SCRIBE_DASHSCOPE_WORKSPACE_ID=ws-xxx
```

## 项目边界

Smart Scribe 聚焦“已有素材到知识卡片”的整理链路。

会议录制、实时屏幕捕获、长期后台录音等属于更重的素材采集能力，建议由独立工具负责，例如 PPT-Grabber。更好的组合方式是：

```text
PPT-Grabber / 录制工具 -> frames + audio + manifest -> Smart Scribe -> Obsidian
```

这样项目边界更清楚，也更容易维护。

## 开发状态

目前重点方向：

- 更干净的 Obsidian 导出模板。
- 移动端和平板响应式细节优化。
- 后续再评估 exe/桌面化封装。

## 目录结构

```text
smart-scribe/
  backend/                 FastAPI 后端
  frontend/                React 工作台
  scripts/                 Windows 安装和启动脚本
  docs/                    API Key 获取演示和设计记录
  docker-compose.yml
  start-windows.bat
```

## 许可

当前为个人项目，暂未开放正式许可证。
