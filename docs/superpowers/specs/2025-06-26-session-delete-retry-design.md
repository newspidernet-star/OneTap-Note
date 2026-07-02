# Smart Scribe — 会话删除 / 失败重试 / 重命名 设计

日期: 2025-06-26

## 概述

给 Smart Scribe 添加三个能力：
1. **删除历史会话**（前端交互 + 后端 DELETE + 级联清理 + 磁盘清理）
2. **分步骤失败重试**（上传/处理/转写/匹配/生成每步失败可重试，不从头来）
3. **会话重命名**（前端标题输入框接入后端 PATCH 保存）

## 后端改动

### 1. Session 模型扩展

`backend/app/models/session.py` — Session 表新增一个字段：

```python
error_message = Column(String(500), nullable=True)
```

管线任意一步失败时，在对应的路由/服务里 `session.error_message = str(e)` 并 `session.status = "failed"`（现只有 `created`/`done`，新增 `failed`）。

### 2. DELETE 端点

`DELETE /api/sessions/{session_id}`

逻辑：
1. 查 id → 不存在抛 404
2. 按 FK 依赖顺序级联删除子表：
   - `matches`
   - `transcript_segments`
   - `transcripts`
   - `evidence_blocks`
   - `materials`
   - `summaries`
   - `sessions`
3. 删除磁盘目录 `storage/session_{id}/`
4. 返回 `{"ok": true}`

数据库 FK 不加 `ON DELETE CASCADE`（避免静默级联生产数据），用显式逐表 delete 保证可控。

### 3. PATCH 端点

`PATCH /api/sessions/{session_id}` — body: `{"title": "新标题"}`

逻辑：
1. 查 id → 不存在抛 404
2. 更新 title → commit
3. 返回 session 对象

### 4. 错误捕获

在 `backend/app/api/media.py` 的 `process_session`、`backend/app/api/speech.py` 的 `transcribe`、`backend/app/api/summary.py` 的 `match` 和 `generate` 四个路由里，加 `try/except` 包裹核心调用 → 失败时设置 `session.error_message` + `session.status = "failed"` → 仍返回 HTTP 500 给前端（让前端能感知失败）。

## 前端改动

### 1. 删除会话交互

侧边栏会话列表（`Workstation.tsx` 左侧 aside 的"历史会话"区域）：

- 每个会话条目右侧 hover 时出现 × 删除图标
- 点击 → 弹出确认对话框："确定删除「xxx」吗？所有媒体、证据、总结将一并清除。"
- 确认后调 `useDeleteSession` mutation → 成功后刷新列表，切换到下一个会话或 demo
- 删除中显示 loading spinner

### 2. 上传/处理/转写失败 → UploadProgress 区

`UploadProgress` 组件已支持 `error` 状态（红色提示图标 + 文字）。修改工作：

- 现有 `uploadStatus` 派生逻辑已含 `generateError` → `"error"`，但不够精确——需要区分"上传/处理/转写"错误 vs "匹配/生成"错误。
- 新增 `pipelineError` 状态（来自后端返回的 session.error_message），在 `uploadStatus` 为 error 时展示具体错误信息。
- error 态下，UploadProgress 显示一个"重新处理"按钮，调 `processMut.mutate({ sessionId })` 从头重跑流程。
- UploadProgress 组件需新增 `errorMessage?: string` prop，用于展示具体失败原因（读取自 `activeSession?.error_message`）。

### 3. 生成失败 → IslandButton 区

IslandButton 已有 `error` mode（显示错误 + 重试按钮）。现有逻辑依赖 `generateError`，保持不变。加上重试时调 `handleGenerate`（先 match 再 generate）。

### 4. 会话重命名

Workstation 顶部标题输入框（`<input defaultValue={title}>`）改成受控输入，失焦时调 `useRenameSession` mutation 保存：

```typescript
const renameMut = useRenameSession();
// onBlur: renameMut.mutate({ sessionId, title: e.target.value })
```

### 5. 新增 API hooks

`frontend/src/lib/api.ts` 新增两个 mutation：

```typescript
useDeleteSession()   // DELETE /api/sessions/{id}
useRenameSession()   // PATCH /api/sessions/{id}
```

query key 工具函数也新增两个导出。

## 数据流

```
用户操作                前端状态                        后端操作
────────               ────────                       ────────
点 × 删除             弹出确认框
确认                   调 useDeleteSession            DELETE 级联
                      刷新 session 列表
                      activeSessionId 切到下一个

上传/处理失败          调 processMut (retry)           POST process → 清旧数据 → 重跑
                       uploadStatus: uploading→ocr→...
                       成功→done / 失败→error

匹配/生成失败          调 handleGenerate              POST match → POST generate
                       buttonStatus: matching→...     成功→done / 失败→error

编辑标题 → 失焦        调 useRenameSession            PATCH title
```

## 文件改动清单

| 文件 | 操作 | 内容 |
|------|------|------|
| `backend/app/models/session.py` | edit | Session 加 `error_message` 字段 |
| `backend/app/api/media.py` | edit | process 加 try/except + 存 error、新增 DELETE/PATCH 路由 |
| `backend/app/api/speech.py` | edit | transcribe 加 try/except + 存 error |
| `backend/app/api/summary.py` | edit | match/generate 加 try/except + 存 error |
| `frontend/src/lib/api.ts` | edit | 加 `useDeleteSession`、`useRenameSession` hooks |
| `frontend/src/pages/Workstation.tsx` | edit | 删除按钮 + 确认弹窗、标题失焦保存、重试逻辑 |
| `frontend/src/components/UploadProgress.tsx` | edit | error 态加"重新处理"按钮 |
| `frontend/src/components/IslandButton.tsx` | edit | 完善重试按钮回调（已有雏形） |
