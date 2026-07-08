# Smart Scribe

> 把短视频、音频和图片素材整理成可以放进 Obsidian 的知识笔记。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.2.0-blue)](https://github.com/newspidernet-star/smart-scribe/releases/tag/v0.2.0)

---

## 这个项目解决什么问题

平时刷到一个有价值的视频，最麻烦的不是“看完”，而是看完以后怎么把它变成自己的东西。

很多内容来自抖音、B 站、YouTube 或本地素材：一个工具推荐、一段课程讲解、一段观点输出、一张视频里的关键截图。它们看起来有用，但如果没有整理，很快就会散掉。

Smart Scribe 想解决的是这个问题：

> 把已有素材转成一份干净、可追溯、可以继续放进 Obsidian 的知识笔记。

它不是会议纪要工具，也不是单纯的转写工具。它更像一个短视频知识整理工作台：上传或粘贴链接，得到原文、证据、时间线和一份可直接阅读的 Markdown 笔记。

## 现在能做什么

### 上传或粘贴链接

支持本地上传视频、音频、图片，也支持粘贴链接下载素材。

当前主要支持：

| 类型 | 说明 |
| --- | --- |
| 抖音链接 | 支持常见分享链接 |
| Bilibili / b23.tv | 支持常见视频链接 |
| YouTube | 通过 yt-dlp 处理 |
| 直链文件 | 支持 mp4、mp3、jpg、png 等常见媒体直链 |
| 本地文件 | 支持视频、音频、图片上传 |

当前 README 只写已经在项目里实现过的能力。

### 语音优先，手动选帧补充

现在默认路线是：优先从语音转写里提取主要信息。

自动视频 OCR 已经默认关闭，因为很多短视频里 95% 以上的信息来自语音，自动抽帧又容易慢、重复、漏重点。Smart Scribe 保留了手动选帧能力：当你觉得某个画面很重要，可以自己在播放器里标记当前帧，再把它加入证据链。

这也是这个项目现在比较核心的思路：

> 算法不可靠时，把控制权还给用户。

### 生成知识笔记

Smart Scribe 不只是把转写缩短，而是尽量把内容整理成可以直接阅读的知识笔记。

当前笔记生成会尽量做到：

- 不写成“本视频介绍了……”这种简介。
- 根据内容类型整理结构，比如观点、教程、清单、操作步骤。
- 如果原文是明确编号清单，会保留完整编号，不随便压缩。
- 不强行生成没有价值的“注意事项”“行动优先级”。
- 对追加素材提高权重，避免用户补充的信息被旧内容淹没。

### 保留原文和证据

笔记正文默认保持干净，但原始信息不会丢。

你可以单独复制：

- 知识笔记
- 完整原文
- 时间戳 / 证据信息

这样正文不会被技术信息淹没，需要复核时又能回到原文和时间线。

### 时间线和播放器

播放器现在支持手动选帧和时间戳跳转。

已经做过的播放器改进包括：

- 点击时间标签可以跳到对应播放位置。
- 选帧标签不会再把播放器宽度撑大。
- 普通页面和全屏页面的选帧状态保持同步。
- 全屏时有更稳定的控制区和退出逻辑。
- 时间线里可以直接复制时间戳。

### 处理进度反馈

处理过程会显示更细的阶段，而不是让用户干等：

- 接收素材
- 准备
- 转写
- 整理证据关系
- 生成笔记
- 完整性检查

后端也会记录处理日志，方便定位下载、转写、AI 生成等问题。

### 桌面端

Windows 桌面端基于 Electron。

当前桌面端能力：

- 独立窗口，不只是浏览器标签页。
- 支持最小化、最大化、关闭。
- 支持启动加载页。
- 支持关闭时选择“隐藏到系统托盘”或“直接退出”。
- 可以记住关闭偏好，下次按默认选择处理。
- 托盘菜单可以重新启用关闭询问。

## 快速开始

### 方式一：下载 Release

1. 到 [Releases 页面](https://github.com/newspidernet-star/smart-scribe/releases/tag/v0.2.0) 下载 `Smart-Scribe-Windows.zip`
2. 解压
3. 双击 `Smart Scribe.exe`

首次运行会检查运行环境。之后再次打开会更快。

### 方式二：源码启动浏览器版

```powershell
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
./start-windows.bat
```

启动后打开：

```text
http://localhost:8000
```

### 方式三：源码启动桌面版

```powershell
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
./start-desktop.bat
```

`start-desktop.bat` 会优先启动根目录下已经构建好的 `Smart Scribe.exe`。如果 exe 不存在，会尝试进入桌面端启动流程。

### 方式四：Docker

```bash
git clone https://github.com/newspidernet-star/smart-scribe.git
cd smart-scribe
docker compose up --build
```

启动后打开：

```text
http://localhost:8000
```

## API Key 配置

打开应用右上角设置，填写需要的 Key。

常用配置：

- `deepseek_api_key`：用于生成知识笔记
- `dashscope_api_key`：用于语音转写
- `paddleocr_cloud_key`：用于云端 OCR
- `dashscope_workspace_id`：可选
- `ytdlp_cookie_path`：可选，用于需要登录态的视频源

也可以通过环境变量配置：

```dotenv
SMART_SCRIBE_DEEPSEEK_API_KEY=sk-xxx
SMART_SCRIBE_DASHSCOPE_API_KEY=sk-xxx
SMART_SCRIBE_PADDLEOCR_CLOUD_KEY=xxx
SMART_SCRIBE_DASHSCOPE_WORKSPACE_ID=ws-xxx
```

获取示例：

### DeepSeek API Key

![DeepSeek API Key 获取演示](docs/get-deepseek-token.gif)

### DashScope API Key

![DashScope API Key 获取演示](docs/get-dashscope-token.gif)

### PaddleOCR Cloud Key

![PaddleOCR Cloud Key 获取演示](docs/get-paddleocr-token.gif)

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 后端 | FastAPI, SQLAlchemy, SQLite, ffmpeg |
| 前端 | React, Vite, TypeScript, Tailwind CSS, TanStack Query |
| 桌面端 | Electron |
| ASR | DashScope / Fun-ASR |
| OCR | PaddleOCR Cloud 或本地 PaddleOCR |
| AI 整理 | DeepSeek |
| 导出 | Obsidian-compatible Markdown |

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
    start-windows.ps1      启动后端
    package-windows-release.ps1
  docs/                    文档和 API Key 获取演示
  start-windows.bat        浏览器版入口
  start-desktop.bat        桌面版入口
  docker-compose.yml
  LICENSE
```

## 项目边界

Smart Scribe 目前专注于：

```text
已有素材 -> 证据化整理 -> 可阅读的知识笔记 -> Obsidian Markdown
```

这个仓库当前优先把“短视频 / 素材到知识笔记”的主流程做好。

## 许可证

[MIT License](LICENSE)
