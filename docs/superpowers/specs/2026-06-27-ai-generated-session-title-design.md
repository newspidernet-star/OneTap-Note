# AI 自动生成会话标题 — 设计文档

## 背景
当前创建会话时，前端以上传文件名为默认标题：
```tsx
const baseName = arr[0]?.name.replace(/\.[^.]+$/, "") || "Untitled";
```
用户希望转写/总结完成后，由 AI 根据内容生成一个更合适的标题。

## 目标
- 在总结 pipeline 完成后，自动为会话生成 2~6 个字的概括性标题
- 替换默认的文件名标题
- 前端无需额外改动，标题通过会话列表刷新自然更新

## 方案

### 1. 触发时机
在 `summarizer.py` 成功生成 `summary` 后，追加一个轻量调用：
```python
title = await generate_title(summary.corrected_text or summary.summary)
session.title = title
await db.commit()
```

### 2. Prompt 设计
```
请为以下内容生成一个简短、准确的会话标题，2~6 个汉字，不要标点，不要解释。
内容：{text[:2000]}
标题：
```

### 3. 后端改动点
- `backend/app/services/summarizer.py`
  - 总结完成后调用 `generate_title`
  - 注入 `Session` repo 更新标题
- 新增 `backend/app/services/title_generator.py`
  - 封装 DeepSeek 调用
  - 清理输出（去掉引号、换行、多余空格）
  - 失败时保留原标题，不阻塞主流程

### 4. 前端
- 无需改动
- `useListSessions` 会在后台刷新时拿到新标题

## 边界
- 若用户已手动重命名，是否仍覆盖？
  - 建议：仅当标题仍为默认文件名（或 Untitled）时覆盖
  - 可通过标记 `title_ai_generated` 区分，或比较标题是否等于文件名
- 失败时静默降级，不影响总结结果

## 相关文件
- `backend/app/services/summarizer.py`
- `backend/app/services/title_generator.py`（新增）
- `frontend/src/pages/Workstation.tsx`（当前文件名标题逻辑）
