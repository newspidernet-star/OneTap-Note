# Qwen (DashScope) 语音识别集成 — 实施计划

## 任务拆分
1. ✅ 新增 `backend/app/services/qwen_asr.py`
   - DashScope API key / workspace ID 读取
   - 同步 `qwen3-asr-flash`（base64 data URI，≤ 7MB）
   - 异步 `qwen3-asr-flash-filetrans`（公网 URL，长音频）
   - 结果解析为 `TranscriptSegment`

2. ✅ 替换调用入口
   - `backend/app/api/speech.py` 导入 `qwen_asr.transcribe`
   - 删除/保留旧的 `backend/app/services/speech.py`（火山引擎）作为备份

3. ✅ 配置项迁移
   - `backend/app/api/settings.py` 改为 `dashscope_api_key` / `dashscope_workspace_id`
   - `backend/app/config.py` 新增 `public_base_url`
   - 前端设置面板同步更新

4. ✅ 测试更新
   - 更新 `tests/test_speech.py` 为 Qwen 解析逻辑
   - 保留 `tests/test_speech_api.py` API 层测试
   - 全量 backend 测试通过

## 状态
已完成。

## 后续可扩展
- 链接素材直接使用 `original_url` 走 filetrans。
- OSS 上传支持，避免依赖服务公网地址。
- 说话人分离参数调优（待 DashScope 文档明确参数名）。
