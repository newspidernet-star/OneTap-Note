# Mobile One-Page Flow + Sticky Player — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Replace mobile bottom tabs with single scrollable page, add sticky IslandButton player, add hamburger session menu.

**Architecture:** IslandButton gets sticky mode for preview. Workstation mobile layout restructured to one-page scrolling with hamburger drawer.

**Tech Stack:** React + Tailwind v4 + framer-motion + lucide-react

## Global Constraints

- Desktop layout unchanged. Mobile only (<768px, max-md:).
- Remove tabView state. Use `showMobileMenu` state for hamburger drawer.
- Session history list already rendered — just wrap it in a drawer overlay on mobile.
- Timeline click auto-scrolls to IslandButton + seeks video.

---

### Task 1: IslandButton sticky preview + timeline auto-scroll

**Files:**
- Modify: `frontend/src/components/IslandButton.tsx`
- Modify: `frontend/src/pages/Workstation.tsx`

- [ ] **Step 1: IslandButton sticky in preview mode**

In IslandButton.tsx, the return uses `<SpotlightCard className="w-full max-w-[320px] cursor-pointer">`. Add `sticky top-2 z-10` only when in preview mode by computing the className dynamically:

```tsx
const cardClass = mode === "preview"
  ? "w-full max-w-[320px] cursor-pointer sticky top-2 z-10"
  : "w-full max-w-[320px] cursor-pointer";
```

Apply `cardClass` to SpotlightCard.

- [ ] **Step 2: Timeline timestamp click auto-scrolls to IslandButton**

In Workstation.tsx, find the timeline timestamp onClick handler (both desktop and mobile versions). Add a scroll before the seek:

```tsx
onClick={(e) => {
  e.stopPropagation();
  if (currentPreview?.type === "video" || currentPreview?.type === "audio") {
    document.getElementById("island-btn")?.scrollIntoView({ behavior: "smooth", block: "start" });
    const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
    setTimeout(() => {
      if (videoRef.current && ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
    }, 400);
  }
}}
```

Add `id="island-btn"` to the wrapper div around IslandButton.

- [ ] **Step 3: Build + commit**

```bash
cd frontend && npm run build
git add -A && git commit -m "feat: sticky IslandButton preview + timeline auto-scroll"
```

---

### Task 2: Mobile one-page flow + hamburger menu (replace bottom tabs)

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

- [ ] **Step 1: Remove tabView state and bottom tab bar**

Delete the `tabView` state line. Delete the entire bottom tab `<nav>` block (the three-tab bar). Remove all `tabView` conditional renders.

- [ ] **Step 2: Make mobile one-page layout**

On mobile (`max-md:`), all three panels should be in a single scrollable column:
- Upload area (left sidebar content) — visible, full width
- IslandButton wrapper — visible, full width
- AI summary (main content) — visible, full width

Do this by removing `max-md:hidden` from left aside and main, and wrapping them in a single scrollable container on mobile.

Actually simpler: on mobile, the flex row becomes a flex column with all panels visible:

```tsx
<div className="flex flex-1 max-md:flex-col max-md:overflow-y-auto">
  {/* left aside: no max-md:hidden, full width on mobile */}
  <aside className="w-[220px] md:w-[200px] lg:w-[220px] bg-card/50 flex flex-col shrink-0 border-r-2 border-border/50 z-10 max-md:w-full max-md:border-r-0 max-md:border-b-2">
    ...upload area + session list...
  </aside>
  
  {/* main AI summary: no max-md:hidden */}
  <main className="flex-1 flex flex-col bg-card max-md:min-h-0">
    ...IslandButton + AI summary content...
  </main>
  
  {/* timeline: collapse into the main flow on mobile as a section at bottom */}
  ...timeline blocks as a collapsible section at the end of main...
</div>
```

- [ ] **Step 3: Move timeline into main flow on mobile**

On mobile, the timeline (right aside) should become a collapsible section at the bottom of the AI summary main area. Remove the right aside's `max-md:hidden` and make it full-width, or better: move the timeline evidence blocks into the bottom of the AI summary container on mobile using a conditional render.

Simplest approach: on mobile, render the timeline content as a `<CollapsibleCard>` inside the AI summary's scroll area. On desktop, keep the existing right aside.

```tsx
{/* Timeline — desktop sidebar or mobile collapsible card */}
<div className="hidden md:block">
  {/* existing desktop timeline aside + AnimatePresence */}
</div>
<div className="md:hidden mt-4 mx-5">
  <CollapsibleCard icon={Film} title={`原文证据 · ${displayEvidence.length} 块`} defaultOpen={false}>
    {/* timeline evidence block list (same as desktop) */}
  </CollapsibleCard>
</div>
```

- [ ] **Step 4: Add hamburger menu for session history**

Add `showMobileMenu` state:
```tsx
const [showMobileMenu, setShowMobileMenu] = useState(false);
```

In the header, on mobile add hamburger button:
```tsx
<button onClick={() => setShowMobileMenu(true)} className="md:hidden p-1.5 hover:bg-white/10 rounded-md">
  <Menu className="w-5 h-5" />
</button>
```
Import `Menu` from lucide-react.

Add drawer overlay at the root level (before delete/settings modals):
```tsx
<AnimatePresence>
  {showMobileMenu && (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 md:hidden"
      onClick={() => setShowMobileMenu(false)}
    >
      <motion.div initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
        transition={{ type: "spring", damping: 30, stiffness: 400 }}
        onClick={e => e.stopPropagation()}
        className="w-[280px] h-full bg-card border-r border-border overflow-y-auto p-4"
      >
        <div className="flex items-center justify-between mb-4">
          <span className="font-semibold text-base">历史会话</span>
          <button onClick={() => setShowMobileMenu(false)} className="p-1 text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <button onClick={() => { setActiveSessionId(MOCK_SESSION_ID); setShowMobileMenu(false); }}
          className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center gap-2 mb-1 transition-colors ${isMock ? 'bg-primary/10 text-primary' : 'hover:bg-white/5 text-muted-foreground'}`}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40" />
          演示会话（mock）
        </button>
        {realSessions.map(s => (
          <div key={s.id} className="group relative">
            <button onClick={() => { setActiveSessionId(s.id); setShowMobileMenu(false); }}
              className="w-full text-left px-3 py-2 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors hover:bg-white/5 text-muted-foreground"
            >
              <div className={`w-1.5 h-1.5 rounded-full ${s.status === 'failed' ? 'bg-red-500' : s.status === 'done' ? 'bg-green-500' : 'bg-muted-foreground/40'}`} />
              {s.title}
            </button>
            <button onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        <button onClick={() => { setActiveSessionId(MOCK_SESSION_ID); setShowMobileMenu(false); }}
          className="w-full mt-3 py-2 rounded-lg border border-dashed border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors">
          + 新建会话
        </button>
      </motion.div>
    </motion.div>
  )}
</AnimatePresence>
```

Also add `X` to lucide imports.

- [ ] **Step 5: Build + commit**

```bash
cd frontend && npm run build
git add -A && git commit -m "feat: mobile one-page flow + hamburger session menu, remove bottom tabs"
```
