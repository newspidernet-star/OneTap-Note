# One Tap Note

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/icon-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="frontend/public/icon-light.png">
    <img src="frontend/public/icon-light.png" alt="One Tap Note icon" width="112" height="112">
  </picture>
</div>

> 把短视频、音频、录屏和图片素材，转化成可以沉淀到个人知识库里的笔记。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.2.0-blue)](https://github.com/newspidernet-star/one-tap-note/releases/tag/v0.2.0)

---

## 这是什么

One Tap Note 是一个信息消化工具。

它最开始是为了解决“短视频怎么进入个人知识库”这个问题：刷抖音、B 站、YouTube 时看到一个有价值的视频，复制链接或上传素材，让系统把视频里的语音、文字、关键画面整理成一份可以放进 Obsidian 的 Markdown 笔记。

但它不只适合短视频。只要你手里已经有素材，比如会议录音、录屏、课程视频、图片截图、音频片段，也可以交给 One Tap Note 做整理。

我真正想做的不是一个更花哨的转写器，而是一个把信息从“看过”变成“积累过”的管道。

```text
已有素材 -> 转写 / OCR / 选帧 -> AI 整理 -> 知识笔记 -> Obsidian
```

## 产品内核：把输入压力压到最低

One Tap Note 这个名字的重点不是“点一下按钮”这么浅。

它想表达的是一种交互方向：尽量减少用户在信息整理上的输入压力。你不需要在刷视频、看资料、听录音的时候突然切换到“我要认真做笔记”的状态，也不需要先想清楚分类、标签、标题、摘要怎么写。看到有价值的东西，先用最轻的动作丢进来，后面的下载、转写、清洗、结构化和导出交给系统。

这也是为什么我觉得 “One Tap” 很贴合这个项目。它让我想到初代 iPhone 舍弃传统手机键盘和手写笔时的那个判断：最方便的输入工具，其实就是人自己的手指。对 One Tap Note 来说，理想状态也是这样：不用让用户背负额外的整理动作，只要一个链接、一个文件、一次上传，信息就开始被消化。

所以它不是一个单纯的“视频摘要工具”，而是一个信息内化工具：

```text
低压力输入 -> 自动消化 -> 知识卡片 -> 个人知识库 -> 以后可检索、可复用、可表达
```

最终产物也不应该只是“这个视频讲了什么”的简介，而应该是你真正想要的知识卡片：能直接放进 Obsidian，能在以后写作、面试、学习、复盘、决策时重新调用。

## 快速开始

### 方式一：下载 Release

1. 到 [Releases 页面](https://github.com/newspidernet-star/one-tap-note/releases/tag/v0.2.0) 下载 `One-Tap-Note-Windows.zip`
2. 解压
3. 双击 `One Tap Note.exe`
4. 打开右上角设置，填写需要的 API Key
5. 上传本地素材，或者粘贴视频链接
6. 生成知识笔记，复制到自己的 Obsidian 里

### 方式二：源码启动浏览器版

```powershell
git clone https://github.com/newspidernet-star/one-tap-note.git
cd one-tap-note
./start-windows.bat
```

启动后打开：

```text
http://localhost:8000
```

### 方式三：源码启动桌面版

```powershell
git clone https://github.com/newspidernet-star/one-tap-note.git
cd one-tap-note
./start-desktop.bat
```

桌面版会优先启动根目录下已经构建好的 `One Tap Note.exe`。

### 方式四：Docker

```bash
git clone https://github.com/newspidernet-star/one-tap-note.git
cd one-tap-note
docker compose up --build
```

启动后打开：

```text
http://localhost:8000
```

## 为什么要做

### 1. 收藏夹经常变成数字坟场

刷到一个视频，收藏的时候觉得“这个以后肯定有用”。

但现实通常是：收藏夹越堆越满，越满越不想看。到最后甚至连收藏都懒得点，因为心里知道，收进去大概率也是吃灰。

One Tap Note 想把“收藏”往前推一步：不要只把链接丢进坟场，而是尽快把内容转成能检索、能复用、能放进知识库的笔记。

### 2. 视频的信息提取成本太高

一个 3 分钟视频，有效信息可能只有 30 秒。

但你必须从头看到尾，才知道哪 30 秒有用。看完以后还不一定记得住，想找某个观点又要重新拖进度条。

这种纯手工的信息提取方式太重了。One Tap Note 做的是把视频先转成文字、证据和时间线，再交给 AI 清洗成结构化笔记。

### 3. 短视频生态比较封闭

网页文章和公众号文章通常能直接拿到正文，短视频不一样。

很多平台没有稳定开放的结构化内容接口。你能拿到的往往只是视频本身，然后必须从音频、画面、字幕和截图里重新提取信息。

这正是 One Tap Note 的切入点：用一个尽量通用的流程，把封闭生态里的视频内容重新整理成个人可控的文本资产。

### 4. 它不是普通会议转写工具

市面上很多 AI 工具做的是：

```text
会议录音 -> 转写 -> 摘要
```

这个场景很清楚，但也很拥挤。One Tap Note 更关注另一类高频场景：

```text
碎片化内容 -> 清洗 -> 结构化 -> 入库 -> 以后可检索复用
```

会议通常是正式沟通，内容相对结构化；短视频更像碎片化输入，跨度大、密度不稳定、上下文经常缺失。它需要的不只是转写，而是二次加工。

One Tap Note 真正在做的是：把“刷完就忘”的内容，变成“可沉淀、可检索、可复用”的知识资产。

| 对比项 | 一般会议转写工具 | One Tap Note |
| --- | --- | --- |
| 输入来源 | 会议录音，内容相对结构化 | 短视频、本地媒体、截图，内容更碎片 |
| 使用场景 | 工作时间，正式场合 | 刷手机、看视频、整理个人素材 |
| 输出目标 | 会议纪要、待办事项 | 个人知识库卡片 |
| 数据流向 | 一次性查看 | 持续沉淀，可检索，可复用 |
| 关键难点 | 转写准确率 | 封闭生态、碎片信息清洗、入库结构 |

## 设计原则

### 输入压力最小化

你不需要在刷视频时切换到“整理模式”。

看到有用的东西，先丢进来。后面的下载、转写、清洗、结构化和导出，交给系统处理。

这个原则贯穿整个产品：入口要轻，等待要清楚，导出要干净，笔记要能直接进入自己的知识库。用户不应该为了“整理信息”再额外学习一套复杂流程。

### 扁平化管理

不要一开始就让用户纠结文件夹、标签、分类。

先把内容变成干净的知识卡片，放进 Obsidian。真正需要的时候，通过搜索、链接和后续整理再慢慢生长。

### 控制权还给用户

自动抽帧不一定可靠，尤其是短视频、混剪、评论类内容。

所以 One Tap Note 现在默认语音优先，并保留手动选帧。你觉得某个画面重要，就自己标记进去。算法负责辅助，不替你做最终判断。

## 当前能力

### 素材输入

支持本地上传视频、音频、图片，也支持粘贴链接下载素材。

当前主要支持：

| 类型 | 说明 |
| --- | --- |
| 抖音链接 | 支持常见分享链接 |
| Bilibili / b23.tv | 支持常见视频链接 |
| YouTube | 通过 yt-dlp 处理 |
| 直链文件 | 支持 mp4、mp3、jpg、png 等常见媒体直链 |
| 本地文件 | 支持视频、音频、图片上传 |

### 语音转写

视频和音频会提取语音内容，生成可继续整理的原文。

当前系统更偏向“语音优先”的路线，因为很多短视频的主要信息确实来自声音。自动视频 OCR 默认关闭，避免慢、重复、误判，把更重要的判断留给手动选帧。

### 手动选帧

如果视频里有重要画面，比如 PPT、代码片段、评论截图、操作界面，可以在播放器里手动标记当前帧。

这些手动选帧会作为证据加入当前会话，用来补充语音转写没有覆盖的信息。

### 知识笔记

One Tap Note 会把原文整理成更适合阅读和保存的知识笔记。

当前生成逻辑会尽量做到：

- 不写成“本视频介绍了……”这种简介。
- 根据内容类型组织结构，比如观点、教程、清单、步骤。
- 原文是明确编号清单时，保留完整编号。
- 不强行生成没有价值的“注意事项”或“行动优先级”。
- 追加素材会提高权重，避免用户补充的信息被旧内容淹没。

### 原文和时间线

正文笔记保持干净，但原始信息不会丢。

你可以单独复制：

- 知识笔记
- 完整原文
- 时间戳 / 证据信息

时间线可以帮助你回到具体片段，播放器里的时间标签也可以点击跳转。

### 桌面端

Windows 桌面端基于 Electron。

当前桌面端支持：

- 独立窗口
- 启动加载页
- 系统托盘
- 关闭时选择“隐藏到托盘”或“直接退出”
- 记住关闭偏好
- 托盘菜单重新启用关闭询问

## 一个典型使用方式

我的个人用法大概是这样：

1. 刷到一个觉得有用的视频。
2. 复制链接，丢给 One Tap Note。
3. 等它下载、转写、整理。
4. 如果发现视频里有重要画面，就手动选帧补充。
5. 生成知识笔记。
6. 复制 Markdown，放进 Obsidian。

这样做的重点不是“收藏了一个视频”，而是把一次短暂的信息消费，变成一次真正的知识积累。

## 目标画面

我希望它最终能变成一个不断自我生长的外脑。

你在刷抖音时看到一个讲面试技巧的视频，觉得有用，复制链接丢进来。系统在后台把视频下载、转写、整理成卡片，存入知识库。

一周后面试前，你问一句：“我之前收藏过哪些面试技巧？”

系统能从你的知识库里把相关内容翻出来，汇总成可以直接看的答案。

这部分是长期目标，不代表当前版本已经完整实现。当前版本先把“素材 -> 笔记 -> Obsidian”这条主链路做好。

## 更远的最终形态

我相信后面的应用会越来越全面地拥抱智能体。很多工具不会只以“打开一个软件、点一堆按钮”的形式存在，而是会变成智能体可以调用的能力。

所以 One Tap Note 的最终形态，不只是一个桌面应用，而是一个连接智能体和个人知识库的内化工具。

它可以作为一个接口、一条工具链，帮助智能体完成这件事：

```text
任意链接 / 本地素材 / 截图 / 音频
        -> 信息提取
        -> 结构化清洗
        -> 知识笔记
        -> Obsidian / 个人知识库
        -> 以后被智能体重新调用
```

也就是说，它要做的不是简单地“总结一个视频”，而是把短视频数据、媒体数据和零散素材，转化为可以进入个人知识系统的知识基础。

更理想的画面是：

```text
刷到一个好视频
-> 复制链接发给微信、桌面助手或任意智能体入口
-> 智能体调用 One Tap Note
-> 自动完成下载、转写、整理、入库
-> 返回一份摘要，或者静默沉淀到知识库
```

这就是我说的“链接级输入，一句话完成”。用户不需要关心背后是下载器、转写器、OCR、模板，还是 API。用户只需要把信息丢进去，剩下的由工具和智能体协作完成。

从这个角度看，One Tap Note 更像是一个“短视频数据基础 -> 知识基础”的转换层，也是一个让碎片信息内化为个人知识库数据的工具。

## 底层想法

没有足够的积累，就很难有自己的表达。

写作、演讲、技术判断、审美、决策，很多输出能力的底层都是输入量。所谓“没灵感”“表达不出来”“没什么好说”，很多时候不是能力问题，而是积累不够。

One Tap Note 想降低积累的门槛。

以前刷完一个视频，脑子里过了一遍，很快就忘了。现在至少可以把它转成一张笔记，沉淀到自己的知识库里。日积月累，这些内容就不再只是消费痕迹，而是可以被重新调用的材料。

以输出为导向的输入，才是真正的积累。

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

### DeepSeek API Key

<img src="docs/get-deepseek-token.gif" alt="DeepSeek API Key 获取演示" width="720">

### DashScope API Key

<img src="docs/get-dashscope-token.gif" alt="DashScope API Key 获取演示" width="720">

### PaddleOCR Cloud Key

<img src="docs/get-paddleocr-token.gif" alt="PaddleOCR Cloud Key 获取演示" width="720">

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
one-tap-note/
  backend/                 FastAPI 后端
  frontend/                React 工作台
  desktop/                 Electron 桌面壳
    main.cjs               主进程
    preload.cjs            预加载脚本
    build-exe.ps1          构建 One Tap Note.exe
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

## 许可证

[MIT License](LICENSE)
