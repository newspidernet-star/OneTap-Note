# Smart Scribe

自托管的 AI 媒体总结工作台。上传视频 / 音频 / 图片或粘贴链接 → 自动转写 + OCR + AI 总结，**每一个结论都能追溯到具体的 PPT 页或语音时间点**。

定位是"专业工作台"而不是"网页表单"——Premiere / DaVinci 那种暗色工作站美学，按一次按钮走完流水线，结果可引用、可追溯。

## 功能

- 上传本地媒体文件，或粘贴视频链接（yt-dlp 抓取）
- 视频自动抽帧做 **OCR**（识别 PPT / 字幕），音频做 **语音转写**（说话人分离）
- 把转写片段和 OCR 片段对齐成"证据块"（S=Speech / P=Picture）
- 一键生成带引用的 **AI 总结**（核心要点 / 摘要 / 纠错原文），点击引用可跳回原时间点
- 会话标题由 AI 根据内容自动生成，手动改名会被保留
- 证据块颜色编码 + 图标 + 标签三重区分，符合无障碍

## 技术栈

| 层 | 选型 |
|----|------|
| 后端 | FastAPI · SQLAlchemy · SQLite · ffmpeg · yt-dlp · Playwright |
| 前端 | Vite + React 18 + TypeScript · TailwindCSS v4 · Radix UI · TanStack Query · framer-motion |
| OCR | 本地 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 或 [PaddleOCR 云端 API](https://aistudio.baidu.com/paddleocr) |
| 语音转写 | 阿里云百炼 [Fun-ASR 录音文件识别](https://help.aliyun.com/zh/model-studio/fun-asr-recorded-speech-recognition-http-api) |
| AI 总结 | DeepSeek Chat |

---

## 快速开始

### 1. 克隆

```bash
git clone <your-repo-url> smart-scribe
cd smart-scribe
```

### 2. 配置环境变量

后端在 `backend/.env`（gitignore，需自己建）：

```dotenv
# OCR 模式：local = 容器内跑 PaddleOCR；cloud = 调百度 PaddleOCR 云端 API
SMART_SCRIBE_OCR_MODE=cloud

# 必填：让阿里云 ASR 能回拉你服务器上的音频文件
# 指向本服务的公网可访问根地址，例如：
#   http://your-domain.com
#   http://1.2.3.4:8000
#   https://scribe.example.com
# 留空且 SMART_SCRIBE_TUNNEL=auto 时会自动起 cloudflared 临时隧道，无需公网 IP
SMART_SCRIBE_PUBLIC_BASE_URL=
# 无公网 IP 时自动建立 cloudflared 临时隧道（auto / 关闭留空）
SMART_SCRIBE_TUNNEL=auto
```

> 环境变量前缀统一为 `SMART_SCRIBE_`，对应 `backend/app/config.py` 里的 `Settings`。

### 3. 启动后端（Docker，推荐）

```bash
docker compose up --build -d
```

后端跑在 `http://localhost:8000`，健康检查 `/api/health`。

镜像里已装 ffmpeg、PaddleOCR、Playwright Chromium。本地 OCR 模式开箱即用（只是吃显存/内存）。

### 4. 启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev
```

开发服务器自带代理：`/api`、`/static`、`/ws` 全部转发到 `http://localhost:8000`（见 `vite.config.ts`），所以直接访问 `http://localhost:5173` 即可。

> **Windows 提示**：Vite v5 默认监听 IPv6 `[::1]:5173`，用 `http://127.0.0.1:5173` 会 `ERR_CONNECTION_REFUSED`。请用 `http://localhost:5173`；若坚持用 IP，启动时加 `--host 127.0.0.1`：`npm run dev -- --host 127.0.0.1`。

**生产部署**前端 `npm run build` 出 `dist/`，由你自己的 Nginx / Caddy 托管，把 `/api/*` 和 `/static/*` 反代到后端 `:8000`。

### 5. 在网页里填 API Key

打开前端 → 设置页，填以下 key（存进 SQLite，AES 加密）：

| Key | 必填 | 用途 | 获取方式 |
|-----|------|------|----------|
| `dashscope_api_key` | ✅ | 阿里云 Fun-ASR 语音转写 | [阿里云百炼控制台](https://bailian.console.aliyun.com/) → API-KEY 管理 |
| `dashscope_workspace_id` | 可选 | 走业务空间专属域名（更快更稳），不填走默认 `dashscope.aliyuncs.com` | 百炼控制台 → 业务空间详情 |
| `deepseek_api_key` | ✅ | AI 总结生成 | [DeepSeek 开放平台](https://platform.deepseek.com/) → API Keys |
| `paddleocr_cloud_key` | 仅云端 OCR 必填 | 调 PaddleOCR 云端 API | [百度 AI Studio](https://aistudio.baidu.com/paddleocr) → 访问令牌 |
| `ytdlp_cookie_path` | 可选 | yt-dlp 抓取需登录的视频 | 见 [yt-dlp cookies 文档](https://github.com/yt-dlp/yt-dlp/wiki/Extractors-And-Authentication) |

**也可以用环境变量预配 key**（优先于设置页，适合不想在网页里手填的场景）：

```dotenv
# backend/.env（或容器/平台的环境变量）
SMART_SCRIBE_DASHSCOPE_API_KEY=sk-xxx
SMART_SCRIBE_DEEPSEEK_API_KEY=sk-xxx
SMART_SCRIBE_PADDLEOCR_CLOUD_KEY=xxx
# 可选：
SMART_SCRIBE_DASHSCOPE_WORKSPACE_ID=xxx
SMART_SCRIBE_YTDLP_COOKIE_PATH=/path/to/cookies.txt
```

凡是由环境变量提供的 key，设置页会显示 **"✓ 由部署者配置"** 并禁用对应输入框，避免误填覆盖。

---

## 在 Windows 上启动

### ⓪ 一键脚本（推荐先试）

仓库根目录的 `start-windows.bat` 把下面 A/B 的手动步骤全部自动化：

1. 双击 `start-windows.bat`。
2. 首次运行会自动 `winget` 安装 Python 3.11 / Node.js LTS / ffmpeg / cloudflared（已装则跳过），创建 `backend/.venv`，`pip install` Windows 依赖子集（云端 OCR，跳过 paddleocr），`playwright install chromium`，`npm install && npm run build`，生成 `backend/.env`。
3. 之后启动后端（uvicorn），**前端构建产物由后端直接托管**，单进程监听 `http://localhost:8000`，浏览器自动打开。
4. 进设置页填三个 API Key 即可（同 B6）。

> 限制：仅云端 OCR（需 `paddleocr_cloud_key`）；语音转写时后端自动起 cloudflared 临时隧道供阿里云回拉。脚本会自动探测本机 `127.0.0.1:7897` 代理（clash 默认端口）；下载慢可先 `set HTTPS_PROXY=http://127.0.0.1:7897` 再双击。

---

下面两条路适合需要本地 OCR 或更多控制的用户：

Windows 上有两条路。首选 Docker Desktop（一键起全套，行为和 Linux 一致）；当 Docker 跑不起来或不想装时，再走本地 `uvicorn` 方案。

### A. 都能用：先装好 Docker Desktop 再 `docker compose`

这是最省心的方式——镜像把 ffmpeg / Playwright / PaddleOCR 全打包好了，本地 OCR、云端 OCR 都能跑。

1. 装 Docker Desktop：
   ```powershell
   winget install Docker.DockerDesktop
   ```
2. 启动 Docker Desktop。如果报 **"Virtualization support not detected"**（虚拟化未开启），按下面任一处理：
   - 重启进 BIOS / UEFI，开启 Intel VT-x / AMD-V；
   - 或者：控制面板 → 程序 → 启用或关闭 Windows 功能 → 勾选 "虚拟机平台" 和 "适用于 Linux 的 Windows 子系统（WSL）"，重启后再开 Docker Desktop；
   - 仍然起不来就走方案 B（本地 uvicorn），不强依赖虚拟化。
3. Docker 正常后回到主流程：
   ```powershell
   docker compose up --build -d
   ```
   然后直接做第 4、5 步（前端、API Key）即可。

### B. 不用 Docker：本地 uvicorn 跑后端

适用于：没装 Docker、虚拟化开不了、不想拉几个 GB 的 PaddlePaddle 镜像。代价是 **OCR 必须走云端**（见下文说明）。

#### B0. 选 OCR 模式

本地 OCR（`SMART_SCRIBE_OCR_MODE=local`）依赖 PaddlePaddle，在 Windows 上原生安装很容易翻车（没有官方 Windows GPU wheel、CPU wheel 也常因 MKL / Visual C++ 运行库失败）。**Windows 本地方案只推荐云端 OCR**：

```dotenv
# backend/.env
SMART_SCRIBE_OCR_MODE=cloud
SMART_SCRIBE_PUBLIC_BASE_URL=
SMART_SCRIBE_TUNNEL=auto
```

> 如果你确实需要本地 OCR：要么走方案 A（Docker），要么在 WSL2 里跑后端。Windows 原生跑本地 OCR 不在支持范围内。

#### B1. 准备运行依赖

需要 **Python 3.11**（3.12/3.13 下 FastAPI、Playwright 等多数包还没有 wheel）、**ffmpeg**、**Node.js 18+**：

```powershell
winget install Python.Python.3.11
winget install Gyan.FFmpeg        # 装完确认 `ffmpeg -version` 能跑
winget install OpenJS.NodeJS.LTS # 已装可跳过
```

#### B2. 装后端依赖

云端 OCR 不会 import `paddleocr` / `paddlepaddle`，可把它们从 `backend/requirements.txt` 里**暂时删掉这两行**（留着会装失败，云端模式用不上）：

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
cd backend
pip install -r requirements.txt
playwright install chromium
```

#### B3. 启动后端

```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

健康检查 `http://localhost:8000/api/health`。改完代码按 Ctrl+C 重跑即可。

#### B4. 启动前端

另开一个 PowerShell：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`（开发服务器会把 `/api`、`/static`、`/ws` 代理到 `:8000`）。

#### B5. 公网回拉（语音转写必读）

阿里云 Fun-ASR 要从公网回拉音频。Docker 镜像内置 cloudflared，但 **Windows 本地启动默认没有 cloudflared**，所以 `SMART_SCRIBE_TUNNEL=auto` 在 Windows 原生上不会自动起隧道。三选一：

- **有公网 IP / 域名**：在 `backend/.env` 填 `SMART_SCRIBE_PUBLIC_BASE_URL=https://your-host`，并保证 `/static/media/*` 可公网下载（见下方"公网地址配置"章节）；
- **内网穿透**：用 frp / Cloudflare Tunnel / 花生壳把某公网域名隧穿到本机 `:8000`，再填 `SMART_SCRIBE_PUBLIC_BASE_URL`；
- **手动装 cloudflared**：`winget install Cloudflare.cloudflared`，保证它在 PATH 里，后端代码会在转写时自动起 quick tunnel（`SMART_SCRIBE_TUNNEL=auto`）。**装完务必重开 PowerShell**——winget 不会刷新当前终端的 PATH，旧窗口里 `cloudflared` 仍找不到。

#### B6. 填 API Key

打开前端 → 设置页，填：

| Key | 必填 | 说明 |
|-----|------|------|
| `dashscope_api_key` | ✅ | 阿里云 Fun-ASR |
| `deepseek_api_key` | ✅ | AI 总结 |
| `paddleocr_cloud_key` | ✅ | 云端 OCR 必填，没有它 OCR 流程不可用 |

---

## 两种 OCR 模式

由 `SMART_SCRIBE_OCR_MODE` 控制，**改完需重启**：

### `cloud`（默认，推荐）

调百度 AI Studio 的 [PaddleOCR 云端服务](https://aistudio.baidu.com/paddleocr)，模型 `PP-OCRv6`：

1. 注册 AI Studio 账号，开通 PaddleOCR 服务
2. 在控制台拿到访问令牌（Access Token）
3. 设置页填入 `paddleocr_cloud_key`

后端走 `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`，自带限流重试（429 退避）。快、不吃本机资源，适合大多数场景。

### `local`（离线/隐私场景）

设 `SMART_SCRIBE_OCR_MODE=local` 切回本地推理。镜像内置 PaddleOCR + PaddlePaddle，吃 CPU/内存，但不需要任何百度账号，适合离线/隐私场景。

---

## 公网地址配置（语音转写必读）

阿里云 Fun-ASR 是**异步转写**：你把音频文件提交给它，它会**从你给的 URL 把文件拉回去**处理。所以 Smart Scribe 必须把音频挂在一个公网可访问的地址上。

### 工作机制

`backend/app/services/qwen_asr.py` 里：

1. 把上传的任意格式音频用 ffmpeg 转成 16kHz 单声道 MP3，存到 `backend/storage/`
2. 拼出公网 URL：`{SMART_SCRIBE_PUBLIC_BASE_URL}/static/media/<相对路径>`
3. 提交给阿里云 Fun-ASR，轮询任务状态，取回结果

**所以 `SMART_SCRIBE_PUBLIC_BASE_URL` 必须填一个能让阿里云服务器从公网访问到你这台机器的根地址。**

### 场景 ⓪：没有公网 IP（自动隧道，推荐先试）

不填 `SMART_SCRIBE_PUBLIC_BASE_URL`，把 `SMART_SCRIBE_TUNNEL=auto`（默认就是 auto），后端启动转写时会自动起一个 **cloudflared quick tunnel**，拿到一个随机的 `*.trycloudflare.com` 临时域名当作公网地址喂给阿里云。镜像里已内置 cloudflared，纯出站 443，不需要域名、账号、内网穿透。

- 每次重启域名会变，但只影响"正在进行的转写"，已完成的会话不受影响。
- 安全：隧道模式会自动屏蔽来自隧道的 `/api/*` 请求，**只暴露 `/static/media` 这一条音频下载路径**，外人拿域名也下不到你的 API。
- Cloudflare Free 单请求体上限 100MB；Smart Scribe 实际喂的是 16kHz/32kbps 的 MP3（约 4KB/s，1 小时 ~14MB），远低于上限。

### 三种典型场景

**① 有公网 IP / 域名 + HTTPS**

```dotenv
SMART_SCRIBE_PUBLIC_BASE_URL=https://scribe.example.com
```

Nginx 反代示例：

```nginx
server {
    listen 443 ssl;
    server_name scribe.example.com;

    location / {              # 前端静态
        root /var/www/scribe-frontend/dist;
        try_files $uri /index.html;
    }
    location /api/  { proxy_pass http://127.0.0.1:8000; }
    location /static/ { proxy_pass http://127.0.0.1:8000; }   # 关键：ASR 回拉走这里
    location /ws/   { proxy_pass http://127.0.0.1:8000; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; }
}
```

**② 有公网 IP，直接暴露端口**

```dotenv
SMART_SCRIBE_PUBLIC_BASE_URL=http://1.2.3.4:8000
```

后端已经把 `/static/media` 挂在 `main.py` 上对外服务，直接可达即可。

**③ 内网穿透（frp / Cloudflare Tunnel / 花生壳）**

把某个公网域名隧穿到本机 `:8000`，然后：

```dotenv
SMART_SCRIBE_PUBLIC_BASE_URL=https://your-tunnel.example.com
```

### 验证是否配通

启动后端后，从**另一台公网机器**访问：

```bash
curl -I ${SMART_SCRIBE_PUBLIC_BASE_URL}/api/health
# 期望 HTTP/1.1 200 OK
```

能拿到 200 就说明阿里云也能拉到你的音频。如果一直转写失败、报 `InvalidFile.DownloadFailed`，99% 是这个地址不通——检查防火墙、反代、HTTPS 证书。

> ⚠️ 不配公网地址且未开自动隧道 → 转写流程会报错："语音转写需要公网回拉音频…"。开 `SMART_SCRIBE_TUNNEL=auto` 即可自动解决，无需公网 IP。

---

## 目录结构

```
smart-scribe/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 路由：media / speech / summary / settings
│   │   ├── services/      # ocr.py / qwen_asr.py / summarizer.py / title_generator.py / crypto.py / tunnel.py
│   │   ├── models/ schemas/ config.py main.py
│   ├── storage/           # 上传文件 + SQLite DB（gitignore）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-windows.txt   # Windows 云端 OCR 依赖子集（剔除 paddleocr）
├── frontend/
│   ├── src/pages/Workstation.tsx        # 工作台主页
│   ├── src/components/                  # SummaryHeroCard / IslandButton / UploadProgress
│   ├── src/lib/api.ts                   # TanStack Query 封装
│   └── vite.config.ts                   # 含 /api /static /ws 代理
├── scripts/
│   ├── setup-windows.ps1                # Windows 一键安装（被 start-windows.bat 调用）
│   └── start-windows.ps1                # Windows 一键启动
├── docs/
│   ├── DEVLOG.md          # 逐项开发日志
│   └── superpowers/specs/ # 设计文档
├── docker-compose.yml     # 仅后端；前端自行 npm run dev/build
├── start-windows.bat      # Windows 双击入口（首次安装，之后启动）
├── PRODUCT.md             # 产品定位与设计原则
└── AGENTS.md              # AI 协作说明
```

---

## 多人共享部署（隔离 + 用完即焚）

默认行为是"自己用"：**无会话隔离、无自动清除**——所有会话都列在侧栏，永久保留。

如果你要把实例公开给多人用（比如部署到公网、给团队/朋友体验），开启 `ephemeral` 模式会同时启用三层隐私保护：

| 保护 | 机制 |
|------|------|
| **会话隔离** | 每个浏览器标签生成独立 `client_id`（存 `sessionStorage`），列表只显示自己的会话，互不可见 |
| **心跳续命** | 前端每 15 秒 ping 一次后端，证明"标签还开着" |
| **关闭即清** | 后台清扫线程每 30 秒扫一次，删除"心跳已停超过 60 秒"的会话（DB 记录 + 媒体文件）。`status=processing` 的会话受保护最多 1 小时，避免打断正在跑的转写/总结 |

### 开启方式

在环境变量里加一行（`backend/.env`、`docker-compose.yml` 的 `environment`、或部署平台的 secrets）：

```dotenv
SMART_SCRIBE_EPHEMERAL=true
# 可选：调整 grace 时长（秒），默认 60
SMART_SCRIBE_EPHEMERAL_TTL=60
```

开启后，设置页会显示"关闭标签后清除"的提示横幅。**改完需重启后端**。

### 关闭方式

删除 `SMART_SCRIBE_EPHEMERAL` 这一行（或设为 `false`），重启。已存的会话不会被删，只是不再自动清扫。

> ⚠️ **重要安全说明**：这套隔离是**软隔离**，只防"两个体验者无意中在侧栏看到对方的会话标题"，**防不住故意窥探的人**——`client_id` 是前端生成的明文字符串，没有认证。要让公网实例真正安全，请在网络层加保护（如 Cloudflare Access、Basic Auth、防火墙白名单），只放行你信任的人。

---

## 常见问题

**转写一直失败，提示音频下不下来？**
ASR 拉不到你的公网。检查 `SMART_SCRIBE_PUBLIC_BASE_URL` 是否能从公网访问，且 `/static/media/...` 路径能直接下到文件。

**本地 OCR 模式构建特别慢 / 镜像特别大？**
PaddlePaddle + PaddleOCR + Playwright Chromium 套件很大，第一次 build 要 10 分钟左右。想精简就切 `cloud` 模式，镜像里就不需要跑本地模型了（但依赖仍装着，如需彻底瘦身可以改 `requirements.txt`）。

**前端访问白屏 / API 404？**
开发模式必须通过 `localhost:5173` 而不是直接访问后端 8000；生产必须把 `/api`、`/static` 反代到后端。

**改了 `SMART_SCRIBE_OCR_MODE` 没生效？**
环境变量在 Settings 类加载时读一次，改完要 `docker compose restart backend`。

---

## 许可证

私有项目，未公开发布。