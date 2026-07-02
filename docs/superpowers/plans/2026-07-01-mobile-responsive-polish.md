# 移动端响应式打磨 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复移动端 6 处交互坏点并全局打磨字号/间距/触摸热区/safe-area，让移动端体验从「勉强能用」升到「顺手好用」。

**Architecture:** 方案 A 最小侵入——只补充 `max-md:` 断点类和触摸交互修复，不改 DOM 结构、不拆组件。受影响文件全部在前端：`Workstation.tsx`、`SummaryHeroCard.tsx`、`UploadProgress.tsx`、`audio-player.tsx`、`use-mobile.tsx`、`index.css`。

**Tech Stack:** React + TypeScript + Tailwind CSS v4 + framer-motion。Tailwind 默认断点 `md=768px`。无前端测试框架，每个任务用 `npm run build` + 手动浏览器验证作为测试周期，构建通过即为该任务验收门槛。

## Global Constraints

- Tailwind 默认断点，`md:` = ≥768px，`max-md:` = <768px，`sm:` = ≥640px
- 所有移动端适配必须用 `max-md:` / `md:` 前缀，禁止新建 @media 查询
- 桌面端（≥768px）外观与交互必须完全不受影响——任何改动后桌面端截图对比无差异
- 改动只限前端，禁止碰后端
- 每个任务结束必须 `npm run build` 通过 + `git commit`
- 触摸热区最小 32×32px（关键按钮 ≥40px）

## File Structure

- `frontend/src/index.css` — 新增 `.safe-area-top` / `.safe-area-bottom` 工具类
- `frontend/src/hooks/use-mobile.tsx` — 确认全局 `useIsMobile` hook 返回值与用法
- `frontend/src/pages/Workstation.tsx` — 模块 1/2/4/5/6 的主战场
- `frontend/src/components/SummaryHeroCard.tsx` — 模块 3 删本地 useIsMobile
- `frontend/src/components/UploadProgress.tsx` — 模块 6 尺寸缩放
- `frontend/src/components/ui/audio-player.tsx` — 模块 6 媒体舞台高度

---

### Task 1: 会话行改名/删除按钮触摸可见

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`（侧边栏每行重命名按钮 ~行 752、删除按钮 ~行 760-761；移动端菜单抽屉里的删除按钮 ~行 988-989）

**Interfaces:**
- Consumes: 无
- Produces: 移动端会话行始终可见的重命名/删除按钮，触摸热区 ≥32×32px

**背景**：当前重命名、删除按钮使用 `opacity-0 group-hover:opacity-100`，触摸设备无 hover 永远不可见。

**改动**：给每处 `opacity-0 group-hover:opacity-100` 的会话操作按钮，附加 `max-md:opacity-100` 让移动端始终可见。同时把按钮的 `p-1` / `p-1.5` 补成 `max-md:min-w-[32px] max-md:min-h-[32px] max-md:p-1.5`，提升触摸热区。视觉权重在移动端用 `max-md:text-muted-foreground/40` 压低，避免抢眼。

桌面端因 `group-hover:opacity-100` 仍然只在 hover 时出现，不影响桌面外观。

共约 4 处按钮需要改 class。

- [ ] **Step 1: 改侧边栏每行重命名按钮**

定位 `Workstation.tsx` 中侧边栏 realSessions.map 内的重命名按钮。原代码：

```tsx
<button
  onClick={(e) => { e.stopPropagation(); setRenamingId(s.id); setRenameDraft(s.title); }}
  className="absolute right-7 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-foreground/5 text-muted-foreground hover:text-foreground transition-all"
  title="重命名"
>
  <Pencil className="w-3 h-3" />
</button>
```

改为：

```tsx
<button
  onClick={(e) => { e.stopPropagation(); setRenamingId(s.id); setRenameDraft(s.title); }}
  className="absolute right-7 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 max-md:opacity-100 max-md:min-w-[32px] max-md:min-h-[32px] max-md:flex max-md:items-center max-md:justify-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground transition-all"
  title="重命名"
>
  <Pencil className="w-3 h-3 max-md:w-4 max-md:h-4" />
</button>
```

- [ ] **Step 2: 改侧边栏每行删除按钮**

同一段 realSessions.map 内的删除按钮。原代码：

```tsx
<button
  onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all"
  title="删除"
>
  <Trash2 className="w-3.5 h-3.5" />
</button>
```

改为：

```tsx
<button
  onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 max-md:opacity-100 max-md:min-w-[32px] max-md:min-h-[32px] max-md:flex max-md:items-center max-md:justify-center hover:bg-red-500/10 text-muted-foreground hover:text-red-400 max-md:text-muted-foreground/50 transition-all"
  title="删除"
>
  <Trash2 className="w-3.5 h-3.5 max-md:w-4 max-md:h-4" />
</button>
```

- [ ] **Step 3: 改移动端菜单抽屉里的删除按钮**

定位 `Workstation.tsx` 中移动端菜单抽屉（`md:hidden` 的 motion.div）里每个 session 的删除按钮。原代码：

```tsx
<button onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400">
  <Trash2 className="w-3.5 h-3.5" />
</button>
```

改为：

```tsx
<button onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 max-md:opacity-100 min-w-[32px] min-h-[32px] flex items-center justify-center text-muted-foreground/50 hover:text-red-400">
  <Trash2 className="w-3.5 h-3.5" />
</button>
```

- [ ] **Step 4: Build 验证**

Run: `cd /home/wxc/projects/smart-scribe/frontend && npm run build`
Expected: `✓ built` 成功，无 TS 错误

- [ ] **Step 5: 手动验证**

浏览器 DevTools 切到 375px 宽（iPhone）：
- 会话列表每行右侧能看到重命名铅笔 + 删除垃圾桶图标
- 图标点击范围足够大，不会误触相邻按钮
- 切到 ≥768px 桌面端：按钮恢复成 hover 才出现，外观无变化

- [ ] **Step 6: Commit**

```bash
cd /home/wxc/projects/smart-scribe && git add frontend/src/pages/Workstation.tsx
git commit -m "fix(mobile): 会话行改名/删除按钮触摸设备始终可见

- 加 max-md:opacity-100 让触摸设备无 hover 也能显示按钮
- 触摸热区提到 32×32px
- 移动端图标稍放大到 w-4 h-4
- 桌面端保持 opacity-0 group-hover 不变"
```

---

### Task 2: 引用标签点击跳转状态统一

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`（~行 141-143 state 定义、行 358-371 handleCitationClick、行 534/539 时间线按钮、行 650/923/932/960 时间线面板渲染）

**Interfaces:**
- Consumes: 无
- Produces: 单一 `timelineVisible` state，桌面 aside 和移动端抽屉根据 `useIsMobile` 各自决定是否渲染

**背景**：当前 `timelineOpen`（桌面专用）和 `showMobileTimeline`（移动端）是两套独立 state。`handleCitationClick` 只设 `setTimelineOpen(true)`，移动端引用标签点击毫无反应。

**改动**：合并两套 state 为单一 `timelineVisible`，按当前是否移动端路由到桌面 aside 或移动端抽屉。

- [ ] **Step 1: 加 useIsMobile hook 使用**

`Workstation.tsx` 顶部已 import 区下方加 `const isMobile = useIsMobile();`，但 `Workstation` 目前没 import 这个 hook。先确认 `frontend/src/hooks/use-mobile.tsx` 导出的名称。

Run: `grep -n "export" /home/wxc/projects/smart-scribe/frontend/src/hooks/use-mobile.tsx`

预期看到 `export function useIsMobile()` 之类。本任务是直接 import 它。在 Workstation.tsx 文件已有的 import 区追加：

```tsx
import { useToast } from "@/hooks/use-toast";
import { useIsMobile } from "@/hooks/use-mobile";
```

在 `Workstation` 组件内已有 state 声明区（`useToast` 后面）加：

```tsx
const isMobile = useIsMobile();
```

- [ ] **Step 2: 合并 timelineOpen 与 showMobileTimeline 为 timelineVisible**

定位 `Workstation.tsx` 内 state 声明：

```tsx
const [timelineOpen, setTimelineOpen] = useState(false);
const [showMobileMenu, setShowMobileMenu] = useState(false);
const [showMobileTimeline, setShowMobileTimeline] = useState(false);
```

替换为：

```tsx
const [timelineVisible, setTimelineVisible] = useState(false);
const [showMobileMenu, setShowMobileMenu] = useState(false);
```

（不再需要 `showMobileTimeline`，移动端时间线复用 `timelineVisible` + `isMobile` 判断）

- [ ] **Step 3: 更新 handleCitationClick**

原代码：

```tsx
const handleCitationClick = (id: string) => {
    setTimelineOpen(true);
    setHighlightedBlock(id);
    setTimeout(() => {
      const el = document.getElementById(`ev-${id}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const block = displayEvidence.find(b => b.id === id);
      if (block && videoRef.current) {
        const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
        if (ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
      }
    }, 300);
    setTimeout(() => setHighlightedBlock(null), 2000);
  };
```

改为：

```tsx
const handleCitationClick = (id: string) => {
    setTimelineVisible(true);
    setHighlightedBlock(id);
    setTimeout(() => {
      const el = document.getElementById(`ev-${id}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const block = displayEvidence.find(b => b.id === id);
      if (block && videoRef.current) {
        const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
        if (ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
      }
    }, 300);
    setTimeout(() => setHighlightedBlock(null), 2000);
  };
```

仅一行变化：`setTimelineOpen(true)` → `setTimelineVisible(true)`。

- [ ] **Step 4: 更新顶栏时间线按钮**

定位顶栏 `onClick={() => setTimelineOpen(o => !o)}`，改为 `onClick={() => setTimelineVisible(v => !v)}`。

移动端时间线按钮 `onClick={() => setShowMobileTimeline(true)}`，改为 `onClick={() => setTimelineVisible(true)}`。

- [ ] **Step 5: 更新桌面时间线 aside 渲染条件**

定位桌面端时间线 aside（`hidden md:block` / `max-md:hidden` 的 `AnimatePresence` 块）。原代码里 `timelineOpen` 作为 motion 控制条件，全部替换为 `timelineVisible && !isMobile`。

例如：

```tsx
<AnimatePresence>
  {timelineOpen && (
    <motion.aside ...>
```

改为：

```tsx
<AnimatePresence>
  {timelineVisible && !isMobile && (
    <motion.aside ...>
```

注意 aside 上的 close 按钮 onClick 也要换成 `setTimelineVisible(false)`。

- [ ] **Step 6: 更新移动端时间线抽屉渲染条件**

定位移动端时间线抽屉（`md:hidden` 的 motion.div 块）。原代码里 `showMobileTimeline` 控制条件，替换为 `timelineVisible && isMobile`。

例如：

```tsx
<AnimatePresence>
  {showMobileTimeline && (
    <motion.div ...>
```

改为：

```tsx
<AnimatePresence>
  {timelineVisible && isMobile && (
    <motion.div ...>
```

抽屉内 close 按钮 / 遮罩 onClick 换成 `setTimelineVisible(false)`。

- [ ] **Step 7: Build 验证**

Run: `cd /home/wxc/projects/smart-scribe/frontend && npm run build`
Expected: `✓ built`

如果有 TS 报错「timelineOpen / showMobileTimeline 未定义」：grep 残留引用全部替换成 `timelineVisible` + 对应 `isMobile` 判断。

Run: `grep -n "timelineOpen\|showMobileTimeline" /home/wxc/projects/smart-scribe/frontend/src/pages/Workstation.tsx`
Expected: 空输出（无残留）

- [ ] **Step 8: 手动验证**

- 桌面端（≥768px）：点引用标签 → 桌面 aside 时间线滑入 + 高亮目标块；点顶栏时间线按钮可开/关
- 移动端（375px）：点引用标签 → 移动端右抽屉弹出 + 高亮目标块
- 桌面端切到移动端尺寸 / 反之：状态不丢失，不存在「桌面 aside 卡在打开状态切到移动端时不显示」

- [ ] **Step 9: Commit**

```bash
cd /home/wxc/projects/smart-scribe && git add frontend/src/pages/Workstation.tsx
git commit -m "fix(mobile): 引用标签点击跳转 + 时间线状态统一

- 合并 timelineOpen / showMobileTimeline 为单一 timelineVisible
- handleCitationClick 触发 timelineVisible，由 isMobile 路由到桌面 aside 或移动端抽屉
- 桌面/移动端时间线开关共用同一 state，消除状态割裂"
```

---

### Task 3: 统一 useIsMobile 断点

**Files:**
- Modify: `frontend/src/components/SummaryHeroCard.tsx`（删本地 useIsMobile hook、改用全局 hook）

**Interfaces:**
- Consumes: Task 2 引入的全局 `useIsMobile` hook（`@/hooks/use-mobile`）
- Produces: SummaryHeroCard 与主布局共享 768px 断点，640-767 灰区不再错乱

**背景**：SummaryHeroCard 自带 `useIsMobile(breakpoint=640)` hook，与全局 768 灰区错乱。

- [ ] **Step 1: 删本地 useIsMobile hook 定义**

`SummaryHeroCard.tsx` 顶部已有的 import：

```tsx
import { ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { DynamicIsland, DynamicIslandView } from "@/components/ui/be-ui-dynamic-island";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
```

追加全局 hook import 并删本地 hook：

```tsx
import { ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { DynamicIsland, DynamicIslandView } from "@/components/ui/be-ui-dynamic-island";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";
```

（移除 `useEffect, useState` 的 import，如果其他地方不再用——保留即可，TS 会树摇）

删掉 `SummaryHeroCard.tsx` 内 `function useIsMobile(breakpoint = 640)` 整个定义块。

- [ ] **Step 2: 替换 hook 调用**

定位 `SummaryHeroCard` 函数体内：

```tsx
const isMobile = useIsMobile();
```

此调用保持不变（参数不传，走全局 hook 默认 768）。

- [ ] **Step 3: Build 验证**

Run: `cd /home/wxc/projects/smart-scribe/frontend && npm run build`
Expected: `✓ built`

- [ ] **Step 4: 手动验证**

- 桌面端（≥768px）：生成总结时显示 5 段展开进度岛（与改前外观一致）
- 640px 设备：hero 卡切换到 compact 药丸（与改前一致）
- 700px 设备（640-767 灰区）：hero 卡走 compact 药丸（**修复点**：改前这里仍显示展开岛，与主布局的移动端风格不一致）

- [ ] **Step 5: Commit**

```bash
cd /home/wxc/projects/smart-scribe && git add frontend/src/components/SummaryHeroCard.tsx
git commit -m "fix(mobile): SummaryHeroCard 改用全局 useIsMobile (768px)

删除 SummaryHeroCard 自带 useIsMobile(640) hook，改用全局 useIsMobile(768)。
消除 640-767 灰区 hero 卡与主布局风格不一致。"
```

---

### Task 4: Settings 弹窗移动端 bottom-sheet

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`（Settings 弹窗 motion.div ~行 1060-1118）

**Interfaces:**
- Consumes: 无
- Produces: 移动端 Settings 弹窗从居中 modal 变 bottom-sheet + safe-area 底部 padding

- [ ] **Step 1: 改 Settings 弹窗外壳 class**

定位 `Workstation.tsx` 内 `{showSettings && (...)}` 块的 motion.div 遮罩 + 内部 sheet。

内层 motion.div（白色卡片）原 class 类似：

```tsx
className="bg-card border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl"
```

改为（沿用删除弹窗的 pattern）：

```tsx
className="bg-card border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl max-md:rounded-b-none max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:max-w-none max-md:rounded-t-2xl"
style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom, 0px))' }}
```

- [ ] **Step 2: Build 验证**

Run: `npm run build`
Expected: `✓ built`

- [ ] **Step 3: 手动验证**

- 桌面端：Settings 弹窗居中显示，外观不变
- 移动端（375px）：Settings 从底部滑入，底部留刘海安全区 padding，圆角只在顶部

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Workstation.tsx
git commit -m "fix(mobile): Settings 弹窗移动端变 bottom-sheet + safe-area

移动端 max-md: 下弹窗变底部 sheet，并加 env(safe-area-inset-bottom) 适配刘海。
与删除弹窗风格对齐。桌面端不变。"
```

---

### Task 5: safe-area 全局覆盖

**Files:**
- Modify: `frontend/src/index.css`（新增工具类）
- Modify: `frontend/src/pages/Workstation.tsx`（贴工具类到移动端浮层）

**Interfaces:**
- Consumes: 无
- Produces: `.safe-area-top` / `.safe-area-bottom` 工具类，供 Workstation 浮层使用

- [ ] **Step 1: 在 index.css 加工具类**

`frontend/src/index.css` 末尾追加：

```css
.safe-area-top { padding-top: env(safe-area-inset-top); }
.safe-area-bottom { padding-bottom: env(safe-area-inset-bottom); }
.safe-area-pad { padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom); }
```

- [ ] **Step 2: 给移动端菜单抽屉贴类**

定位 `Workstation.tsx` 内移动端菜单抽屉 motion.div（左侧滑入，`md:hidden`），在最外层 div 或 motion.div className 末尾加 `safe-area-pad`。

- [ ] **Step 3: 给移动端时间线抽屉贴类**

定位移动端时间线抽屉 motion.div（右侧滑入，`md:hidden`），className 末尾加 `safe-area-pad`。

- [ ] **Step 4: 给顶栏贴 safe-area-top**

定位 `Workstation.tsx` 顶栏 `<header>`，class 末尾追加 `safe-area-top`。

- [ ] **Step 5: Build 验证**

Run: `npm run build`
Expected: `✓ built`

- [ ] **Step 6: 手动验证**

- 桌面端：无视觉差异（桌面 safe-area 值为 0）
- 移动端（iPhone 有刘海）：顶栏内容不被刘海遮挡；菜单/时间线抽屉顶部有刘海空白；Settings 弹窗（已在 Task 4 处理）底部留 home indicator 区

- [ ] **Step 7: Commit**

```bash
git add frontend/src/index.css frontend/src/pages/Workstation.tsx
git commit -m "fix(mobile): 全局 safe-area padding 覆盖

- 新增 .safe-area-top / .safe-area-bottom / .safe-area-pad 工具类
- 顶栏、菜单抽屉、时间线抽屉贴 safe-area
- 适配刘海屏 home indicator 区"
```

---

### Task 6: 字号/间距/触摸热区打磨

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`（会话行高、链接输入框、总结卡片字号）
- Modify: `frontend/src/components/UploadProgress.tsx`（尺寸缩放）
- Modify: `frontend/src/components/ui/audio-player.tsx`（媒体舞台高度）

**Interfaces:**
- Consumes: 无
- Produces: 小屏字号/间距自动缩放、触摸热区达标

- [ ] **Step 1: AudioPlayer 媒体舞台高度响应式**

`frontend/src/components/ui/audio-player.tsx` 定位 `h-[300px]` 的 media container div：

```tsx
<motion.div className="relative h-[300px] w-full overflow-hidden rounded-[16px] bg-[#eaeaea] dark:bg-white/20">
```

改为：

```tsx
<motion.div className="relative h-[300px] max-md:h-[200px] w-full overflow-hidden rounded-[16px] bg-[#eaeaea] dark:bg-white/20">
```

- [ ] **Step 2: UploadProgress 尺寸缩放**

`frontend/src/components/UploadProgress.tsx` 定位外层 div：

```tsx
<div className="flex flex-col items-center justify-center gap-3 w-full min-h-[140px] rounded-2xl bg-card border-2 border-dashed border-border/60 select-none">
```

改为：

```tsx
<div className="flex flex-col items-center justify-center gap-3 w-full min-h-[140px] max-md:min-h-[100px] rounded-2xl bg-card border-2 border-dashed border-border/60 select-none">
```

错误文案 `max-w-[200px]`：

```tsx
<p className="text-[11px] text-red-400/70 text-center max-w-[200px]">
```

改为：

```tsx
<p className="text-[11px] text-red-400/70 text-center max-w-[200px] max-md:max-w-[180px]">
```

- [ ] **Step 3: 链接输入框触摸热区**

`Workstation.tsx` 链接输入框所在 div 的 `py-1.5`（或类似）class 改：

```tsx
className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-card border border-border/40 ..."
```

改为：

```tsx
className="flex items-center gap-2 px-3 py-1.5 max-md:py-2.5 rounded-xl bg-card border border-border/40 ..."
```

- [ ] **Step 4: 会话行行高**

`Workstation.tsx` 侧边栏每行 button 的 `py-2`：

```tsx
className={`w-full text-left px-3 py-2 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors ...`}
```

改为：

```tsx
className={`w-full text-left px-3 py-2 max-md:py-2.5 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors ...`}
```

`space-y-1` 容器：

```tsx
className="flex-1 overflow-y-auto p-2 space-y-1"
```

改为：

```tsx
className="flex-1 overflow-y-auto p-2 space-y-1 max-md:space-y-1.5"
```

- [ ] **Step 5: 总结卡片字号缩放**

`Workstation.tsx` 内总结卡片标题/正文的 `text-base` 加 `max-md:text-sm`，正文 `text-sm` 加 `max-md:text-xs`。（具体 class 在 CollapsibleCard 内容区，grep `text-base` 找位置）

- [ ] **Step 6: Build 验证**

Run: `cd /home/wxc/projects/smart-scribe/frontend && npm run build`
Expected: `✓ built`

- [ ] **Step 7: 手动验证**

- 360px 宽：字号无溢出、间距不挤、按钮可点
- AudioPlayer 视频缩略图高度变 200px
- UploadProgress 高度紧凑
- 链接输入框触摸点不会误触
- 桌面端（≥768px）：全部外观无变化

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Workstation.tsx frontend/src/components/UploadProgress.tsx frontend/src/components/ui/audio-player.tsx
git commit -m "feat(mobile): 字号/间距/触摸热区断点类缩放

- AudioPlayer 媒体舞台 max-md:h-[200px]
- UploadProgress max-md:min-h-[100px] 错误文案 max-md:max-w-[180px]
- 链接输入框 max-md:py-2.5、会话行 max-md:py-2.5
- 总结卡片 max-md:text-sm / text-xs
- 侧边栏 max-md:space-y-1.5"
```

---

## Self-Review

**Spec coverage:** 6 个模块全部映射到 6 个 Task，覆盖 spec 的验收清单 7 条。

**Placeholder scan:** 无 TBD/TODO，每个步骤都给了改动前后的完整代码。

**Type consistency:** `timelineVisible` 在 Task 2 定义后所有引用点都统一名称。`isMobile` 由全局 `useIsMobile()` 产出，Task 2 和 Task 3 都使用同一签名。`useIsMobile` import 路径 `@/hooks/use-mobile` 在两个 Task 中一致。

## 验收总览

所有任务完成后，最终一次浏览器验证：

- [ ] 移动端侧边栏每行都能看到并点击重命名/删除按钮
- [ ] 移动端点击引用标签能弹出时间线抽屉并高亮目标块
- [ ] 640-767px 灰区 hero 卡与主布局一致走移动端风格
- [ ] Settings 弹窗移动端变 bottom-sheet + 底部 safe-area
- [ ] 顶栏、菜单抽屉、时间线抽屉、Settings 都有 safe-area padding
- [ ] 小屏（360px）字号/间距无溢出、触摸热区 ≥32px
- [ ] 桌面端（≥768px）外观与交互完全不受影响