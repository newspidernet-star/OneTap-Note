# Qwen (DashScope) 语音识别集成

## 背景
原语音识别使用火山引擎 ASR。现切换为阿里云百炼 DashScope 的 Qwen ASR。

## 配置
在设置面板或 `/api/settings` 中配置：
- `dashscope_api_key`（必填）
- `dashscope_workspace_id`（可选；不填则使用默认 `dashscope.aliyuncs.com`）

环境变量：
- `SMART_SCRIBE_PUBLIC_BASE_URL`（可选，示例：`https://your-domain.com`）
  - 用于长音频异步转写，让 DashScope 能通过公网 URL 拉取音频文件。

## 模型选择
- 短音频（≤ 7MB）：使用 `qwen3-asr-flash`，通过 base64 data URI 同步调用。
- 长音频：使用 `qwen3-asr-flash-filetrans`，异步任务，需要音频文件可通过公网 URL 访问。
  - 本地文件会自动拼接为 `{PUBLIC_BASE_URL}/static/media/{relative_path}`。
  - 链接素材（`original_url`）可直接使用原 URL（待扩展）。

## 关键文件
- `backend/app/services/qwen_asr.py` — 新的 ASR 服务
- `backend/app/api/speech.py` — 调用入口改为 `qwen_asr.transcribe`
- `backend/app/api/settings.py` — 设置项改为 DashScope
- `backend/app/config.py` — 新增 `public_base_url`
- `frontend/src/pages/Workstation.tsx` — 设置面板改为 DashScope API Key / Workspace ID

## 长音频部署说明
若课堂录音超过 7MB，必须满足以下任一条件：
1. 将后端部署到具有公网域名的服务器，并设置 `SMART_SCRIBE_PUBLIC_BASE_URL`。
2. 将音频上传至 OSS/CDN，再通过链接方式提交（未来扩展）。

否则会遇到错误提示，要求配置公网地址。
