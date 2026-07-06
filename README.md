# Smart Scribe

我做 Smart Scribe，是因为我经常遇到一种很尴尬的场景：

一个视频里明明有很多有价值的信息，比如项目名、工具链接、课程里的关键页、评论区截图、演示画面，但我看完之后很难把它们干净地放进自己的知识库里。普通的 AI 总结通常更依赖语音转写，画面里的文字和截图信息很容易被忽略。最后得到的东西像一段“看过了的摘要”，但不像一张可以长期保存、复查和引用的知识卡片。

所以 Smart Scribe 想解决的不是“帮我随便总结一下视频”，而是：

> 把短视频/素材整理成可追溯的数字知识基础，再导出到 Obsidian。

它的定位不是会议录制工具，也不是通用网盘转写工具。更准确地说，它是一个面向个人知识库的素材整理工作台。

## 它在做什么

Smart Scribe 会把视频、音频、图片和链接拆成一块块可追溯的证据：

- 视频画面会抽帧并做 OCR，形成 `P001`、`P002` 这样的画面证据。
- 音频和视频里的声音会转写，形成 `S001`、`S002` 这样的语音证据。
- AI 总结不是凭空写一段话，而是基于这些证据块生成摘要、要点和引用。
- 导出的 Markdown 会尽量保持干净，适合直接放进 Obsidian。

我希望它最后产出的不是一篇花哨的 AI 小作文，而是一张能被继续整理、复习、链接和沉淀的知识卡片。

## 现在的核心能力

### 链接和本地素材都能处理

可以粘贴抖音、Bilibili、YouTube 或直链，也可以上传本地视频、音频和图片。

同一个会话里还可以继续追加素材。追加的内容通常是用户觉得重要、怕被漏掉的信息，所以现在追加后会自动重新生成总结，不需要再手动点一次“重新生成”。

### 画面 OCR 和语音 ASR 一起作为证据

很多视频最有价值的部分不一定在语音里，而是在画面里。

比如一个 GitHub 项目的名字、PPT 页上的术语、截图里的链接、评论区里的补充信息，这些只靠语音转写很容易漏掉。Smart Scribe 会同时处理画面和语音，并在语音和画面冲突时优先相信画面 OCR。

### 覆盖率优先的抽帧策略

不同视频不应该用同一种抽帧方式。

- PPT/课程类视频：尽量保守，少抽重复页。
- 抖音/评论/混剪类视频：更重视覆盖率，按时间分桶保留更多画面。
- 长视频：抽帧预算会按时长和场景数量动态增长，但仍然有上限，避免 OCR 成本失控。

处理日志里会记录候选帧为什么被保留或丢弃。这个功能不是给普通用户看的，但它对调试很重要，因为我确实遇到过“人眼看着差异很大，算法却没选出来”的情况。

### 手动选帧补充

自动抽帧不可能永远完美。

所以播放器里可以手动选帧。如果某一页 PPT、某个评论截图、某个关键画面没被自动选中，可以自己补进去。手动补的帧会作为“用户重点追加”进入总结流程，避免被原来的大段内容淹没。

### Obsidian Markdown 导出

导出的 Markdown 会包含：

- YAML frontmatter
- AI 摘要
- 核心要点和证据引用
- 来源链接
- 证据索引
- 可折叠的详细原文

目标是让它能直接进入 Obsidian，而不是还要花很多时间二次清洗。

## 一个典型用法

1. 粘贴一个视频链接，或者上传本地素材。
2. Smart Scribe 自动下载、抽帧、OCR、转写。
3. 页面生成可引用的证据块时间线。
4. AI 基于证据生成摘要和要点。
5. 如果发现漏掉了关键画面，就手动选帧补充。
6. 系统自动重新生成总结。
7. 复制 Markdown 到 Obsidian，继续整理成自己的知识卡片。

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

如果不知道这些 Key 去哪里找，可以看下面几段演示：

### DeepSeek API Key

![DeepSeek API Key 获取演示](docs/get-deepseek-token.gif)

### DashScope API Key

![DashScope API Key 获取演示](docs/get-dashscope-token.gif)

### PaddleOCR Cloud Key

![PaddleOCR Cloud Key 获取演示](docs/get-paddleocr-token.gif)

## 项目边界

我一开始也想过把它继续扩成会议录制、屏幕录制、实时上传之类的工具。但想了一圈之后，感觉那样会把项目做散。

Smart Scribe 更适合专注在“已有素材 -> 证据化整理 -> 知识卡片”这条链路上。会议录制、实时屏幕捕获、长期后台录音这些能力更重，也更像另一个独立工具该做的事情。

如果要和我之前的 PPT-Grabber 配合，更合理的方式可能是：

```text
PPT-Grabber / 录制工具 -> frames + audio + manifest -> Smart Scribe -> Obsidian
```

这样边界更清楚，也更容易维护。

## 接下来想做

- 继续打磨移动端和平板端体验。
- 让 Docker 体验尽量接近 Windows 一键启动。
- 继续清理 Markdown 导出模板，让它更像干净的知识卡片。
- 后面再评估 exe/桌面化封装。

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
