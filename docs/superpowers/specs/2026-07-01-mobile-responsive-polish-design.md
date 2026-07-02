# Smart Scribe 移动端响应式打磨设计

> 方案 A：最小侵入修复 + 全局打磨。不拆组件、不改 DOM 结构，只补齐触摸交互和细节。

## 背景

当前前端已有响应式骨架（三栏→纵向堆叠、汉堡菜单抽屉、移动端时间线抽屉、删除弹窗 bottom-sheet），但有 6 处移动端明显坏掉的地方需要修复，外加字号/间距/触摸热区需要打磨。

用户选择的目标：**移动端体验全面打磨**——修坏点 + 调字号/间距/触摸热区/safe-area，让移动端不只是能用而是好用。导航模式保留顶部汉堡菜单。上传与浏览同等重要。

## 设计模块

### 1. 会话行改名/删除按钮（触摸可见性）

**现状**：按钮使用 `opacity-0 group-hover:opacity-100`，触摸设备无 hover 永远不可见、不可点。影响范围：
- `Workstation.tsx` 侧边栏每行的重命名（Pencil）、删除（Trash2）按钮
- `Workstation.tsx` 移动端菜单抽屉里的删除按钮

**改法**：
- 桌面端（`md:`）：保持 `opacity-0 group-hover:opacity-100`
- 移动端（`max-md:`）：改为 `opacity-100` 始终可见，图标缩小 + 降低视觉权重（`text-muted-foreground/40`），避免在有限按钮区域间引入新的背景色变化
- 触摸热区提到 `min-w-[32px] min-h-[32px]`，接近 44px 但不挤压
- 移动端菜单抽屉里的删除按钮同理

纯 class 改动，不动逻辑。约 4 处按钮 class。

### 2. 引用标签点击跳转（状态统一）

**现状**：`handleCitationClick` 只设 `setTimelineOpen(true)`（桌面 aside），移动端引用标签点击无反应。桌面 `timelineOpen` 与移动 `showMobileTimeline` 是两套独立 state。

**改法**：
- 统一两个 state 为单个 `timelineVisible` 状态
- `handleCitationClick` 设 `setTimelineVisible(true)` + 高亮块（逻辑不变）
- 桌面 aside 的可见性由 `timelineVisible && !isMobile` 控制
- 移动端抽屉的可见性由 `timelineVisible && isMobile` 控制
- 顶栏的「时间线」按钮、移动端「时间线」按钮都 toggle `timelineVisible`
- 消除状态割裂，不多写分支逻辑

需新增判断当前是否移动端的辅助（`useIsMobile` hook 或 `matchMedia`），与模块 3 对齐到同一断点（768px）。

### 3. 统一 useIsMobile 断点

**现状**：`SummaryHeroCard` 自带 hook 用 640px，全局 `use-mobile.tsx` 用 768px。640-767 灰区显示错乱：布局因 `md:` 而已切移动端，hero 卡仍按桌面展开岛渲染。

**改法**：
- 删掉 `SummaryHeroCard` 内的 `useIsMobile` hook 定义
- 改用全局 `useIsMobile()`（768px），或直接用 CSS `max-md:` 控制展开岛显隐
- 倾向直接 CSS 化：少一层 JS 状态，更一致
- 具体：`SummaryHeroCard.tsx` 的 `view={isLoading && !isMobile ? "loading" : null}` 改为依赖全局 hook 或由 CSS 响应式控制 DynamicIsland 的展开/药丸形态切换

校验：646px 设备上 hero 卡与主布局一致走移动端风格。

### 4. Settings 弹窗移动端适配（bottom-sheet）

**现状**：Settings 弹窗为居中 modal（`max-w-md` + `p-4`），与删除弹窗的 bottom-sheet 风格不一致、未适配 safe-area。

**改法**：
- 移动端（`max-md:`）添加类：`max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:max-w-none max-md:rounded-b-none`
- 移动端底部 padding 加 `env(safe-area-inset-bottom)`（与删除弹窗保持一致）
- 桌面端保持现状居中 modal
- 只改 class + inline style，不动提交逻辑

### 5. safe-area 全局覆盖

**现状**：仅删除弹窗一处处理了 `env(safe-area-inset-bottom)`。

**改法**：给 4 个移动端浮层/区域统一加 safe-area padding：
1. 移动端菜单抽屉（左侧滑入）→ 顶 `env(safe-area-inset-top)`、底 `env(safe-area-inset-bottom)`
2. 移动端时间线抽屉（右侧滑入）→ 同上
3. Settings 弹窗 → 模块 4 已处理
4. 顶栏 → 加 `padding-top: env(safe-area-inset-top)`，给刘海留出空间

实现方式：在 `index.css` 加 `.safe-area-top { padding-top: env(safe-area-inset-top); }`、`.safe-area-bottom { padding-bottom: env(safe-area-inset-bottom); }` 工具类，需要的地方贴类即可。

### 6. 字号/间距/触摸热区打磨

**现状**：AudioPlayer `h-[300px]` 固定、UploadProgress 固定尺寸、关键按钮热区偏小、无断点缩放。

**改法**（纯断点类微调，不改 DOM）：
- AudioPlayer 媒体舞台：`h-[300px]` → `h-[240px] max-md:h-[200px]`
- UploadProgress：`min-h-[140px]` → `min-h-[120px] max-md:min-h-[100px]`；错误文案 `max-w-[200px]` → `max-w-[240px] max-md:max-w-[180px]`
- 播放/暂停按钮：现状 `h-10 w-10`（40px），可接受，不动
- 链接输入框：`py-1.5` → `max-md:py-2.5`，输入框 height 提到 44px 级别
- 会话行：`py-2` → `max-md:py-2.5`，行高增大方便手指点
- 总结卡片标题：`text-base` → `text-base max-md:text-sm`
- 摘要正文：`max-md:text-sm`
- 侧边栏行间距：`space-y-1` → `space-y-1 max-md:space-y-1.5`

校验：
- 360px 宽（常见小手机）：无溢出、无重叠、可滚动
- 768px 以下触发所有 `max-md:` 变化
- 768px+ 不受影响、保持桌面样式

## 影响范围

仅前端，不涉及后端。受影响文件：
- `frontend/src/pages/Workstation.tsx`（模块 1/2/4/5/6）
- `frontend/src/components/SummaryHeroCard.tsx`（模块 3）
- `frontend/src/components/UploadProgress.tsx`（模块 6）
- `frontend/src/components/ui/audio-player.tsx`（模块 6）
- `frontend/src/hooks/use-mobile.tsx`（模块 2/3 全局 hook 复用）
- `frontend/src/index.css`（模块 5 safe-area 工具类）

## 验收清单

- [ ] 移动端侧边栏每行都能看到并点击重命名/删除按钮
- [ ] 移动端点击引用标签能弹出时间线抽屉并高亮目标块
- [ ] 640-767px 灰区 hero 卡与主布局一致走移动端风格
- [ ] Settings 弹窗移动端变 bottom-sheet + 底部 safe-area
- [ ] 顶栏、菜单抽屉、时间线抽屉、Settings 都有 safe-area padding
- [ ] 小屏（360px）字号/间距无溢出、触摸热区 ≥32px
- [ ] 桌面端（≥768px）外观与交互完全不受影响