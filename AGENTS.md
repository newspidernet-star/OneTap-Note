# Smart Scribe — Agent Notes

## Project Context
Smart Scribe is an AI media summarization workstation. Users upload video/audio/image files or paste links, the backend extracts evidence blocks (speech + screen/OCR), and the frontend generates an AI summary with citations.

## AI Summary Button — Role & Behavior

The "生成 AI 总结" (Generate AI Summary) control is the central trigger for the summarization flow in the workstation UI.

### Empty state
- Rendered as a centered hero card (`SummaryHeroCard` at `frontend/src/components/SummaryHeroCard.tsx`).
- Title: "AI 总结", subtitle: "上传媒体或粘贴链接后生成带引用来源的结构化总结".
- CTA button: solid 52px pill-style button with arrow hover animation.

### Click / generation flow
1. `handleGenerate` in `frontend/src/pages/Workstation.tsx` runs.
2. First calls `matchEvidence` to align evidence blocks.
3. Then calls `generateSummary` to produce the final result.

### Processing state
- The hero card shows a loading state: the CTA button displays the current stage, and a 5-segment progress bar below tracks 上传 → OCR → 转写 → 匹配证据块 → 生成总结.

### Completion state
- The control slides upward and shrinks.
- It is replaced by the media preview window (video/audio/image) at the top of the AI summary column.
- Below it, the summary content cards slide in: 核心要点 (key points), 摘要 (summary), 纠错原文 (corrected transcript).

### Error / retry
- If generation fails, the control shows an error panel with a retry button.

### Compact mode
- When a summary already exists, the top preview area offers a "重新生成" (regenerate) action.

## Key Files
- `frontend/src/pages/Workstation.tsx` — layout, state, generation handlers, responsive logic.
- `frontend/src/components/SummaryHeroCard.tsx` — empty/loading/error-state hero card.
- `frontend/src/components/IslandButton.tsx` — multi-mode control (idle / pipeline / preview / error).
- `frontend/src/components/UploadProgress.tsx` — upload / OCR / transcribe progress shown in the left sidebar.

## Implemented Features
- AI-generated session titles: after the first successful summarization, the backend automatically replaces the default filename title with a concise content-derived title. Manual renames are preserved on regeneration. See `docs/superpowers/specs/2026-06-27-ai-generated-session-title-design.md`.
- Qwen ASR integration: speech transcription now uses DashScope (Qwen) ASR instead of Volcano Engine. Configure `dashscope_api_key` and optionally `dashscope_workspace_id`. For long audio files, set `SMART_SCRIBE_PUBLIC_BASE_URL` so the async filetrans model can fetch the file via a public URL.
