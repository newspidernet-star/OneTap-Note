# Smart Scribe

> 把短视频变成个人知识库素材：粘贴链接或上传视频/音频/图片，自动转写 + OCR + AI 知识整理，每个结论可追溯到具体画面或语音，导出 Obsidian 笔记。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.2.0-blue)](https://github.com/newspidernet-star/smart-scribe/releases/tag/v0.2.0)

---

## 它解决什么问题

平时刷抖音、B 站或者看项目介绍视频时，经常会遇到有价值的内容——一个工具推荐、一个 GitHub 项目、一段课程讲解、一页 PPT、一个评论区补充。但看完之后，这些东西通常就散在脑子里了，很难真正放进自己的知识库。

市面上的工具更偏会议场景（飞书妙记、录音转写、会议纪要），但我想解决的是另一个问题：

> 刷到一个短视频，觉得它有价值，能不能把它变成一张能放进 Obsidian 的知识卡片？

Smart Scribe 就是为这个场景做的：已有素材 → 证据化整理 → 可直接使用的知识笔记 → Obsidian 知识卡片。

## 亮点

### 1. 粘贴链接直接处理，不用先下载

不用手动下载视频再上传——粘贴一个抖音 / B 站 / YouTube 链接就行。自有抓取实现，不依赖 yt-dlp，也不需要登录账号。

| 平台 | 抓取方式 | 需要 cookie |
| --- | --- | --- |
| 抖音（视频 / 图文） | 自有实现：解析移动端分享页 SSR 数据，去水印下载 | 不需要 |
| Bilibili（含 b23.tv 短链） | 自有实现：调 B 站公开 API 取播放地址 | 不需要 |
| YouTube | yt-dlp | 可选（会员内容需要） |
| 任意直链（.mp4 / .mp3 / .jpg ...） | 直接下载 | 不需要 |

### 2. 同时看"画面"和"声音"

很多短视频的有价值信息不在语音里——项目名、链接、PPT 关键词、代码片段、评论区截图。如果只做语音转写，很容易漏掉。

Smart Scribe 把视频抽成关键画面做 OCR，也把音频转成文字。生成知识笔记时，画面证据和语音证据一起参与，术语以画面 OCR 为准。

### 3. 有证据链，不是凭空总结

内容会被拆成证据块：

- `S001`、`S002`：语音转写证据
- `P001`、`P002`：画面 OCR 证据

AI 生成知识笔记时带着这些引用，看到一个结论时可以回头找到它来自哪一段语音、哪一张画面。

### 4. 可以自己选帧补充

自动抽帧不可能永远正确。某个 PPT 页面、某个评论截图没被抽到时，可以在播放器里自己选帧补进证据链——不是完全相信算法，而是允许用户把觉得重要的画面塞回去。

### 5. 追加素材自动重新生成

一个视频不够完整时，可以继续补一张截图、补一段音频、补另一个视频。追加后自动重新生成知识笔记，不用手动点“重新生成”。

### 6. 导出成 Obsidian 笔记

默认导出的 Markdown 只保留给人阅读的知识正文。完整原文和证据记录仍然保留，但通过单独按钮按需复制，不再挤进主笔记。

## 快速开始

### 方法一：下载 Release（普通用户推荐）

1. 到 [Releases 页面](https://github.com/newspidernet-star/smart-scribe/releases/tag/v0.2.0) 下载 `Smart-Scribe-Windows.zip`
2. 解压
3. 双击 `Smart Scribe.exe`

首次运行会自动检查并安装 Python、Node.js、ffmpeg 等运行环境（需要几分钟）。之后每次打开都是秒开——关闭窗口后后端继续在后台运行，下次双击直接复用。

### 方法二：从源码启动（浏览器窗口）

```powershell
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
./start-windows.bat
```

启动后打开 `http://localhost:8000`。首次运行自动检查 Python、Node.js、ffmpeg、cloudflared，安装依赖并构建前端。

### 方法三：从源码启动（桌面窗口）

```powershell
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
./start-desktop.bat
```

`start-desktop.bat` 会优先启动已构建好的 `Smart Scribe.exe`；如果 exe 还不存在，会进入 Electron 开发模式。

桌面版和浏览器版的区别：

- 独立桌面窗口（最小化 / 最大化 / 关闭），不是浏览器标签页
- 启动页 + 加载动画
- 系统托盘常驻，关闭窗口不杀后端
- 标题栏颜色随深色 / 浅色主题切换

### 方法四：Docker

```bash
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
docker compose up --build
```

启动后打开 `http://localhost:8000`。

## 功能说明

### 素材处理

- 支持视频、音频、图片
- 支持本地上传和链接下载
- 支持同一会话继续追加素材
- 支持视频画面抽帧、OCR、语音转写
- 支持手动选帧补充

### 抽帧和 OCR

Smart Scribe 会根据视频内容选择关键画面。PPT / 课程类视频保留信息更完整的画面；抖音、评论、混剪类视频更重视覆盖率；长视频按时长和场景数量动态提高抽帧预算，但控制上限避免 OCR 成本失控。

处理日志会记录候选帧为什么被保留或丢弃，方便调试。

### 知识笔记和引用

知识笔记基于证据块生成，而不是只看一段转写文本。系统会先判断内容类型：教程优先整理步骤、错误和注意事项，观点内容优先整理结论与论证，会议内容优先整理决策和待办。如果画面文字和语音转写冲突，通常优先相信画面 OCR——因为很多专有名词、项目名、代码片段，画面上的文字比语音转写更可靠。

### Markdown 导出

默认导出的 Markdown 面向 Obsidian，包含：

- YAML frontmatter
- 根据内容类型生成的知识正文
- 教程步骤、观点脉络、决策待办等动态结构
- 来源链接和轻量时间戳

需要复核时，还可以单独复制完整原文或证据记录。主笔记保持干净，原始信息也不会丢失。

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 后端 | FastAPI, SQLAlchemy, SQLite, ffmpeg |
| 前端 | React, Vite, TypeScript, Tailwind CSS, TanStack Query |
| 桌面壳 | Electron |
| OCR | PaddleOCR Cloud 或本地 PaddleOCR |
| ASR | DashScope / Fun-ASR |
| AI 知识整理 | DeepSeek |
| 导出 | Obsidian-compatible Markdown |

## API Key

打开应用右上角设置，填写：

- `deepseek_api_key`：用于生成知识笔记
- `dashscope_api_key`：用于语音转写
- `paddleocr_cloud_key`：用于云端 OCR
- `dashscope_workspace_id`：可选
- `ytdlp_cookie_path`：可选，用于需要登录的视频源

也可以通过环境变量配置：

```dotenv
SMART_SCRIBE_DEEPSEEK_API_KEY=sk-xxx
SMART_SCRIBE_DASHSCOPE_API_KEY=sk-xxx
SMART_SCRIBE_PADDLEOCR_CLOUD_KEY=xxx
SMART_SCRIBE_DASHSCOPE_WORKSPACE_ID=ws-xxx
```

获取演示：

### DeepSeek API Key

![DeepSeek API Key 获取演示](docs/get-deepseek-token.gif)

### DashScope API Key

![DashScope API Key 获取演示](docs/get-dashscope-token.gif)

### PaddleOCR Cloud Key

![PaddleOCR Cloud Key 获取演示](docs/get-paddleocr-token.gif)

## 目录结构

```text
smart-scribe/
  backend/                 FastAPI 后端
  frontend/                React 工作台
  desktop/                 Electron 桌面壳
    main.cjs               主进程
    preload.cjs            预加载脚本
    build-exe.ps1          构建 Smart Scribe.exe
    package.json
  scripts/                 Windows 安装和启动脚本
    setup-windows.ps1      首次安装依赖
    start-windows.ps1      启动后端（支持无浏览器模式）
    package-windows-release.ps1  打包 Release zip
  docs/                    API Key 获取演示和设计文档
  start-windows.bat        浏览器版入口
  start-desktop.bat        桌面版入口
  docker-compose.yml
  LICENSE                  MIT
```

## 项目边界

这个项目专注在：

```text
已有素材 → 证据化整理 → 可直接使用的知识笔记 → Obsidian 知识卡片
```

会议录制、屏幕捕获、实时上传这些方向暂不做。如果需要，可以让独立工具负责采集（比如 [PPT-Grabber](https://github.com/newspidernet-star/PPT-Grabber)），再把素材交给 Smart Scribe 整理：

```text
PPT-Grabber / 录制工具 → frames + audio + manifest → Smart Scribe → Obsidian
```

## 接下来想做

- 继续打磨移动端和平板端体验
- 让 Docker 体验尽量接近 Windows 一键启动
- 继续清理 Markdown 导出模板，让它更像干净的知识卡片
- 后续评估 Setup 安装器（现在用 zip 便携版）
- 把 Smart Scribe 做成 CLI 和 MCP 工具，让任何智能体都能直接调用

我越来越相信，未来的软件不会只以一个独立应用的形式存在，它也应该成为智能体可以随时调用的能力。

所以我希望以后能把 Smart Scribe 做成一个稳定的接口：不管入口是微信里的智能体、桌面助手，还是其他 Agent，只要把视频链接或本地文件交给它，再说一句“用 Smart Scribe 整理”，它就能完成下载、抽帧、OCR、语音转写、总结和 Markdown 导出，返回和现在这个应用一样完整的结果。

现在的桌面应用不会消失，它依然适合需要查看过程、手动选帧和追加素材的人。CLI、API 和 MCP 则负责把这套能力带到更多入口里，继续减少输入压力。

## 许可

[MIT License](LICENSE)
