# Product

## Register

product

## Users

学生、讲师、会议记录员。使用场景：复习课堂录像、整理会议录音、给视频内容做带引用的结构化笔记。用户在专注状态下使用此工具，期望像打开 Premiere Pro 一样进入工作流，而不是填一个网页表单。

## Product Purpose

Smart Scribe 是自托管的课堂/会议记录工作台：上传视频/音频/图片 → 自动转写 + OCR + AI 总结，且每个结论都能追溯到具体 PPT 页或语音时间点。成功标准：用户打开就知道这是个"专业工具"而非"网页表单"，按一次按钮走完流水线，结果可引用可追溯。

## Brand Personality

克制、专业、有重量感。Premiere Pro 或 DaVinci Resolve 那种暗色工作站美学——不是网络应用，是工作台。语气三个词：precise / dense / purposeful。

## Anti-references

- **2000 年代功能主义工具**：只有文字和方块按钮，无层次无过渡无图标——用户明确点名这是反面
- **典型 SaaS 网页**：奶油底色、巨大卡片、每节上方一行 uppercase 小标语——典型 AI 生成感
- **通用表单式 UI**：居中卡片 + 标题 + 按钮，看起来像注册页

## Design Principles

1. **Earned familiarity, not surprise**：参照 Linear / Figma / Premiere Pro 的工具语言，用户坐下来就懂，不要发明奇形怪状的控件
2. **密度是美德**：工具用户在固定 DPI 屏幕前工作，信息密度比留白更重要
3. **状态丰富、装饰克制**：每个控件都有完整的 hover/focus/active/disabled/loading/error 状态，但不用装饰性动画或糖纸
4. **Dark workspace, not dark mode**：这是工作站主题，不是浅色主题的"夜间变种"——配色从开工站美学推导，不是浅色反转
5. **原文永远在场上**：AI 摘要和原文时间线永远并存，摘要可引用回原文，这是产品差异化核心

## Accessibility & Inclusion

- 暗色主题下正文 ≥4.5:1 contrast（#e0e0e8 on #0f0f1a ≈ 14:1，通过）
- 所有交互控件键盘可达，focus 可见
- 支持 prefers-reduced-motion：动效全部走淡入淡出替代
- 证据块颜色编码（S 蓝 / P 红）同时也用图标 + 标签区分，仅颜色不传达信息