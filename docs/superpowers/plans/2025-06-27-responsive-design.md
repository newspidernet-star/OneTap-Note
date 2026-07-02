# Responsive Three-Breakpoint Layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Workstation responsive across desktop (3-col), tablet (2-col), and mobile (bottom-tab single-panel).

**Architecture:** Single file `Workstation.tsx` modified with Tailwind responsive prefixes (`md:`, `max-md:`, `lg:`) + one new state `tabView`. No new components or dependencies.

**Tech Stack:** React + Tailwind v4 + framer-motion + lucide-react

## Global Constraints

- No new dependencies. Pure Tailwind responsive classes + existing lucide icons.
- All changes in `frontend/src/pages/Workstation.tsx`.
- Desktop layout unchanged visually.
- Tablet: 2 columns (upload + AI summary), timeline as collapsed tab.
- Mobile: bottom tab bar with 3 icons, single panel view.
- `tabView` state only active on `<768px`.

---

### Task 1: Add tabView state + responsive Header

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

**Interfaces:**
- Produces: `tabView: "upload" | "summary" | "timeline"` state, initialized to `"summary"`

- [ ] **Step 1: Add tabView state**

After line ~118 (timelineOpen state), add:

```typescript
const [tabView, setTabView] = useState<"upload" | "summary" | "timeline">("summary");
```

- [ ] **Step 2: Make header responsive — hide title input and status on mobile**

Find the header block (around line ~308). Replace the title input and status section with responsive versions.

The header block currently looks like:
```tsx
<header className="h-12 border-b border-border/40 bg-card flex items-center justify-between px-4 shrink-0 z-10 relative">
  <div className="flex items-center gap-4">
    <div className="flex items-center gap-2 text-primary">
      <Sparkles className="w-5 h-5" />
      <span className="font-bold tracking-tight">Smart Scribe</span>
    </div>
    <div className="w-px h-4 bg-border" />
    <input key={...} ... />
  </div>
  <div className="flex items-center gap-3">
    ...status + theme + settings...
  </div>
</header>
```

Change the title input to hide on mobile:
```tsx
<div className="w-px h-4 bg-border max-md:hidden" />
<input key={activeSession?.id || "mock"} type="text" defaultValue={activeSession?.title || ""} onBlur={...} className="bg-transparent border-none outline-none focus:ring-1 ring-primary rounded px-2 text-sm font-medium w-64 max-md:hidden" />
```

Also hide the status dot/text on mobile (`max-md:hidden`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Workstation.tsx
git commit -m "feat: add tabView state, responsive header hide on mobile"
```

- [ ] **Step 4: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -3
```
Expected: `✓ built in ...`

---

### Task 2: Responsive three-column layout + bottom tab bar

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

**Interfaces:**
- Consumes: `tabView` state from Task 1
- Produces: Responsive panel visibility via `max-md:hidden` + `md:` prefixes + bottom tab bar JSX

- [ ] **Step 1: Make left sidebar responsive — hide on mobile unless tabView=upload**

Find the left aside (around line ~379):
```tsx
<aside className="w-[220px] bg-card/50 flex flex-col shrink-0 border-r-2 border-border/50 z-10">
```

Change to:
```tsx
<aside className={`w-[220px] md:w-[200px] lg:w-[220px] bg-card/50 flex flex-col shrink-0 border-r-2 border-border/50 z-10 ${tabView !== "upload" ? "max-md:hidden" : "max-md:w-full"}`}>
```

- [ ] **Step 2: Make AI summary middle responsive — hide on mobile unless tabView=summary**

Find the main element (around line ~478):
```tsx
<main className="flex-1 flex flex-col bg-card">
```

Change to:
```tsx
<main className={`flex-1 flex flex-col bg-card ${tabView !== "summary" ? "max-md:hidden" : ""}`}>
```

- [ ] **Step 3: Make timeline sidebar responsive — hide on mobile unless tabView=timeline**

The timeline AnimatePresence block wraps `<motion.aside>` or the collapsed button. Add the visibility conditional:

For the `{timelineOpen ? (` block's `<motion.aside>`, keep as is but add `max-md:hidden` class to the entire AnimatePresence wrapper:

```tsx
<AnimatePresence>
  {timelineOpen ? (
    <motion.aside
      key="timeline-open"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 400, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col shrink-0 bg-card border-l-2 border-border/50 z-10 overflow-hidden max-md:hidden"
    >
```

And for the collapsed button:
```tsx
{!timelineOpen && (
  <button ... className="shrink-0 w-10 ... max-md:hidden">
```

When `tabView === "timeline"` on mobile, show the timeline full-width instead:

Add after the collapsed button (and before the closing `</div>` of the flex wrapper):

```tsx
{tabView === "timeline" && (
  <div className="hidden max-md:flex flex-col flex-1 bg-card z-10">
    <div className="px-4 py-2.5 bg-card text-xs font-medium text-muted-foreground flex items-center gap-2">
      <Film className="w-3.5 h-3.5" /> 时间线 · {displayEvidence.length} 块
    </div>
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      ...same timeline content as the aside version...
    </div>
  </div>
)}
```

Actually, duplicating the timeline content is bad. Better approach: extract the timeline content into a render function or just make the aside itself work for both desktop and mobile.

Simpler approach: on mobile, when tabView=timeline, force the timeline aside to be visible and full-width regardless of timelineOpen state.

Let me restructure: replace the AnimatePresence block with a conditional that on desktop behaves as before (collapsible aside), on mobile shows full-width when tabView=timeline.

```tsx
{/* Desktop: collapsible aside. Mobile: full-width when tab=timeline */}
{tabView === "timeline" ? (
  <div className="hidden max-md:flex flex-col flex-1 bg-card z-10">
    <div className="px-4 py-2.5 bg-card text-xs font-medium text-muted-foreground flex items-center gap-2 shadow-[0_1px_0_0_var(--border)]">
      <Film className="w-3.5 h-3.5" /> 时间线 · {displayEvidence.length} 块
    </div>
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      <TimelineContent />
    </div>
  </div>
) : (
  <>
    <AnimatePresence>
      {timelineOpen ? (
        <motion.aside ... className="... max-md:hidden">
          <div className="px-4 py-2.5 ..."><Film /> 时间线 · {displayEvidence.length} 块 <button onClick={() => setTimelineOpen(false)}><PanelRightClose /></button></div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3" ref={timelineRef}>
            <TimelineContent />
          </div>
        </motion.aside>
      ) : null}
    </AnimatePresence>
    {!timelineOpen && <button ... className="... max-md:hidden"><PanelRightOpen /> 时间线</button>}
  </>
)}
```

And extract TimelineContent as a local component inside Workstation that renders the evidence blocks map. But extracting a component means defining it inside Workstation or as a regular component. Since the blocks map uses `displayEvidence`, `highlightedBlock`, `handleCitationClick`, etc., it's easier to just duplicate the JSX or use a render helper.

For the plan, I'll just put the duplicated JSX in both places - it's 30 lines of timeline content that's the same. The implementer can refactor if they want.

Actually, for the plan clarity, let me define a `renderTimeline()` inline function.

OK this is getting complex. Let me simplify the plan: the implementer will handle the exact refactoring. I'll describe the intent clearly.

- [ ] **Step 4: Add bottom tab bar (mobile only)**

Add this JSX right before the closing `</div>` of the root container (before the delete and settings modals):

```tsx
{/* Mobile bottom tab bar */}
<nav className="hidden max-md:flex items-center justify-around h-14 shrink-0 bg-card border-t border-border/40 z-20" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
  <button onClick={() => setTabView("upload")} className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors ${tabView === "upload" ? "text-primary" : "text-muted-foreground"}`}>
    <CloudUpload className="w-5 h-5" />
    <span className="text-[10px] font-medium">上传</span>
  </button>
  <button onClick={() => setTabView("summary")} className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors ${tabView === "summary" ? "text-primary" : "text-muted-foreground"}`}>
    <Sparkles className="w-5 h-5" />
    <span className="text-[10px] font-medium">AI 总结</span>
  </button>
  <button onClick={() => setTabView("timeline")} className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors ${tabView === "timeline" ? "text-primary" : "text-muted-foreground"}`}>
    <Film className="w-5 h-5" />
    <span className="text-[10px] font-medium">时间线</span>
  </button>
</nav>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Workstation.tsx
git commit -m "feat: responsive three-column layout + mobile bottom tab bar"
```

- [ ] **Step 6: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -3
```
Expected: `✓ built in ...`

---

### Task 3: Adapt IslandButton, dialogs, and remaining elements for mobile

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

- [ ] **Step 1: IslandButton responsive width**

Find `<IslandButton` in the render and add a wrapper that constrains width on mobile:

No change needed to IslandButton itself — the SpotlightCard inside uses `w-[320px]` which overflows on mobile. Change the IslandButton import/usage by wrapping:

```tsx
<div className="w-full max-w-[320px]">
  <IslandButton
    status={buttonStatus}
    ...
  />
</div>
```

Actually the `w-[320px]` is set on the SpotlightCard inside IslandButton. Let me just change that to be responsive. But IslandButton is a separate component...

Simpler: add `max-md:w-full max-md:max-w-none` to the existing wrapper div around IslandButton. In Workstation.tsx:

```tsx
<div className="w-[320px] max-md:w-full">
```

Wait, the IslandButton itself uses `<SpotlightCard className="w-[320px]...">`. On mobile, 320px exceeds the viewport. I should change IslandButton to accept a className prop or make its width responsive. Since we're keeping changes to Workstation.tsx only, add an override class to the wrapper around IslandButton.

Actually, the IslandButton is already wrapped in a div from the previous SpotlightCard replacement. Let me check the current code.

Actually, looking at the current code, IslandButton renders SpotlightCard with `className="w-[320px] cursor-pointer"`. On phones, 320px > viewport width. The fix is to make SpotlightCard's width responsive. But SpotlightCard is in IslandButton.tsx.

For the plan, I'll note to modify IslandButton.tsx too (it's a trivial change):

In `frontend/src/components/IslandButton.tsx`, line ~33:
```tsx
<SpotlightCard className="w-[320px] cursor-pointer max-md:w-full">
```

Wait, the plan says only Workstation.tsx. But this is a 2-word change. Let me just include it as part of this task, modifying IslandButton.tsx too.

- [ ] **Step 2: IslandButton width fix**

In `frontend/src/components/IslandButton.tsx`, change:
```tsx
<SpotlightCard className="cursor-pointer w-full max-w-[320px]">
```

(Replace `w-[320px]` with `w-full max-w-[320px]` - buttons fill mobile width up to 320px max.)

- [ ] **Step 3: Delete confirm modal — make fullscreen on mobile**

The delete modal is a fixed overlay with a centered card. On mobile, make it take full width with a bottom sheet feel:

Find the delete modal's inner `<motion.div>`:
```tsx
<motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
  onClick={e => e.stopPropagation()}
  className="bg-card border border-border rounded-2xl p-6 w-full max-w-sm shadow-2xl"
>
```

Change to:
```tsx
<motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
  onClick={e => e.stopPropagation()}
  className="bg-card border border-border rounded-2xl p-6 w-full max-w-sm shadow-2xl max-md:rounded-b-none max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:max-w-none"
  style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom, 0px))' }}
>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Workstation.tsx frontend/src/components/IslandButton.tsx
git commit -m "feat: responsive IslandButton, dialogs, mobile polish"
```

- [ ] **Step 5: Final build check**

```bash
cd frontend && npm run build 2>&1 | tail -3
```
Expected: `✓ built in ...`
