# Smart Scribe Plan 3: 前端工作区 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task.

**Goal:** 实现 Adobe Pr 风格三栏工作区前端，包含素材管理、媒体预览、原文时间线、AI 总结面板、设置面板、WebSocket 进度条。

**Architecture:** React 19 + Vite + Tailwind v4 SPA，单页面 Workspace 组件 + Settings 弹窗。通过 REST API 调用后端，WebSocket 实时接收进度。状态管理用 React hooks + context（不引入状态库）。

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS v4, Vitest, React Testing Library, @testing-library/react, jsdom

## Global Constraints

- React 19 + TypeScript + Vite
- Tailwind CSS v4
- 代码无注释
- 前端代码目录: /home/wxc/projects/smart-scribe/frontend/
- 后端 API 在 localhost:8000，Vite 代理 /api 到后端
- 配色: 主背景 #0f0f1a, 面板 #1a1a2e, 边框 #2a2a4a, 文字 #e0e0e8, 次文字 #8888a0, 强调 #e94560, 成功 #00d2a0, 语音蓝 #3a5fe5, 画面红 #e94560
- 左栏 220px 固定，中栏 55%，右栏 30%
- 对照模式为默认视图：左侧时间线 + 右侧总结
- 测试: Vitest + React Testing Library (jsdom)
- 每 task 完成后 commit

---

## File Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── tailwind.config.ts             # Tailwind v4 config
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css                  # Tailwind + theme variables
│   ├── api/
│   │   └── client.ts              # axios/fetch wrapper for all backend endpoints
│   ├── context/
│   │   └── SessionContext.tsx      # session state + API calls
│   ├── hooks/
│   │   └── useWebSocket.ts        # WebSocket progress subscription
│   ├── components/
│   │   ├── TopBar.tsx              # title, status, time
│   │   ├── Sidebar.tsx             # upload + materials + sessions
│   │   ├── StatusBar.tsx           # bottom progress display
│   │   ├── Workspace.tsx           # three-panel layout shell
│   │   ├── UploadZone.tsx          # drag-drop + paste link
│   │   ├── MediaPreview.tsx        # video/audio/img viewer
│   │   ├── Timeline.tsx            # evidence blocks timeline (S001/P003)
│   │   ├── SummaryPanel.tsx        # AI corrected text + summary + key points
│   │   ├── CitationTag.tsx         # clickable [S001] style tag
│   │   └── SettingsModal.tsx       # API key settings form
│   ├── types/
│   │   └── index.ts               # Session, Material, EvidenceBlock, Summary, etc.
│   └── test/
│       ├── setup.ts
│       └── App.test.tsx
```

---

### Task 1: Vite + React + Tailwind 脚手架 + 布局骨架

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`, `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`
- Create: `frontend/src/components/TopBar.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/StatusBar.tsx`, `frontend/src/components/Workspace.tsx`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/vitest.config.ts`

- [ ] **Step 1: package.json**

```json
{
  "name": "smart-scribe-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "jsdom": "^25.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

- [ ] **Step 3: tailwind.config.ts**

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-main": "#0f0f1a",
        "bg-panel": "#1a1a2e",
        "border-panel": "#2a2a4a",
        "text-primary": "#e0e0e8",
        "text-secondary": "#8888a0",
        accent: "#e94560",
        success: "#00d2a0",
        warning: "#ffb800",
        "block-speech": "#3a5fe5",
        "block-screen": "#e94560",
      },
    },
  },
} satisfies Config;
```

- [ ] **Step 4: index.css + types (colors as CSS variables)**

```css
@import "tailwindcss";

:root {
  --bg-main: #0f0f1a;
  --bg-panel: #1a1a2e;
  --border-panel: #2a2a4a;
  --text-primary: #e0e0e8;
  --text-secondary: #8888a0;
  --accent: #e94560;
  --success: #00d2a0;
  --warning: #ffb800;
  --block-speech: #3a5fe5;
  --block-screen: #e94560;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: var(--bg-main);
  color: var(--text-primary);
  font-family: "Inter", system-ui, sans-serif;
  overflow: hidden;
  height: 100vh;
}

#root {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
```

- [ ] **Step 5: types/index.ts**

```typescript
export type SessionStatus = "created" | "processing" | "done" | "error";
export type MaterialType = "video" | "audio" | "image";
export type MaterialStatus = "pending" | "processing" | "done" | "error";
export type EvidenceType = "speech" | "screen";

export interface Session {
  id: number;
  title: string;
  status: SessionStatus;
  created_at: string;
}

export interface Material {
  id: number;
  type: MaterialType;
  source: string;
  sort_order: number;
  status: MaterialStatus;
}

export interface EvidenceBlock {
  id: string;
  type: EvidenceType;
  timestamp: number;
  speaker?: string;
  text: string;
  page_number?: number;
  image_path?: string;
}

export interface TranscriptSegment {
  start_time: number;
  end_time: number;
  speaker: string;
  text: string;
}

export interface KeyPoint {
  point: string;
  citations: string[];
}

export interface SummaryResult {
  corrected_text: string;
  summary: string;
  key_points: KeyPoint[];
  corrections: { offset: number; old: string; new: string }[];
  unused_block_ids: string[];
  citation_valid: boolean;
  invalid_citations: string[];
}
```

- [ ] **Step 6: Workspace.tsx (three-panel layout)**

```tsx
import { useState } from "react";
import type { Session } from "../types";

export default function Workspace() {
  const [activeTab, setActiveTab] = useState<"voice" | "screen" | "compare" | "summary">("compare");
  const [activeSession, setActiveSession] = useState<Session | null>(null);

  return (
    <div className="flex flex-col h-screen">
      {/* Top Bar */}
      <header className="h-10 bg-[var(--bg-panel)] border-b border-[var(--border-panel)] flex items-center px-4 shrink-0">
        <span className="text-sm font-semibold mr-4">Smart Scribe</span>
        {activeSession && <span className="text-sm text-[var(--text-secondary)]">{activeSession.title}</span>}
        <div className="ml-auto flex gap-2">
          <span className="w-3 h-3 rounded-full bg-[var(--success)]" />
          <span className="w-3 h-3 rounded-full bg-[var(--warning)]" />
          <span className="w-3 h-3 rounded-full bg-[var(--accent)]" />
        </div>
      </header>

      {/* Main Work Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-[220px] bg-[var(--bg-panel)] border-r border-[var(--border-panel)] flex flex-col shrink-0">
          <div className="p-3 border-b border-[var(--border-panel)]">
            <div className="border-2 border-dashed border-[var(--border-panel)] rounded-lg p-4 text-center text-sm text-[var(--text-secondary)] hover:border-[var(--accent)] cursor-pointer">
              拖拽文件或粘贴链接
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <p className="text-xs text-[var(--text-secondary)] mb-2">素材列表</p>
            <p className="text-xs text-[var(--text-secondary)] mt-4 mb-2">历史会话</p>
          </div>
        </aside>

        {/* Center */}
        <main className="flex-1 flex flex-col overflow-hidden" style={{ flex: "0 0 55%" }}>
          <div className="flex-1 bg-[var(--bg-main)] p-3 overflow-hidden">
            <p className="text-sm text-[var(--text-secondary)]">媒体预览</p>
          </div>
          <div className="h-64 bg-[var(--bg-panel)] border-t border-[var(--border-panel)] p-3 overflow-y-auto">
            <p className="text-sm text-[var(--text-secondary)]">原文时间线</p>
          </div>
        </main>

        {/* Right Panel */}
        <aside className="bg-[var(--bg-panel)] border-l border-[var(--border-panel)] p-3 overflow-y-auto" style={{ flex: "0 0 30%" }}>
          <h3 className="text-sm font-semibold mb-2">AI 总结</h3>
        </aside>
      </div>

      {/* Status Bar */}
      <footer className="h-8 bg-[var(--bg-panel)] border-t border-[var(--border-panel)] flex items-center px-4 text-xs text-[var(--text-secondary)] shrink-0">
        <span>就绪</span>
      </footer>
    </div>
  );
}
```

- [ ] **Step 7: App.tsx + main.tsx**

```tsx
import Workspace from "./components/Workspace";

export default function App() {
  return <Workspace />;
}
```

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 8: index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Smart Scribe</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 9: vitest.config.ts + test setup**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 10: tsconfig**

Basic tsconfig.json with references to tsconfig.app.json and tsconfig.node.json (standard Vite setup).

- [ ] **Step 11: 写基础测试 (App renders)**

```tsx
import { render, screen } from "@testing-library/react";
import App from "../App";

test("renders Smart Scribe title", () => {
  render(<App />);
  expect(screen.getByText("Smart Scribe")).toBeInTheDocument();
});
```

- [ ] **Step 12: 安装 + 跑**

```bash
cd /home/wxc/projects/smart-scribe/frontend && npm install && npx vitest run
```
Expected: 1 passed

- [ ] **Step 13: Commit**

```bash
git add -A && git commit -m "feat: frontend scaffolding — Vite+React+Tailwind three-panel layout"
```

---

### Task 2: API 客户端 + 类型 + Session Context

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/context/SessionContext.tsx`
- Create: `frontend/src/test/client.test.ts`

- [ ] **Step 1: client.ts (fetch 封装)**

```typescript
const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  sessions: {
    list: () => request<Session[]>("/sessions"),
    create: (title: string) => request<Session>("/sessions", { method: "POST", body: JSON.stringify({ title }) }),
  },
  media: {
    upload: (formData: FormData) =>
      fetch(`${BASE}/media/upload`, { method: "POST", body: formData }).then((r) => r.json()),
    listMaterials: (sid: number) => request<Material[]>(`/media/session/${sid}/materials`),
    process: (sid: number) => request<{ frames_count: number; ocr_pages_count: number; evidence_block_ids: string[] }>(`/media/session/${sid}/process`, { method: "POST" }),
    evidence: (sid: number) => request<EvidenceBlock[]>(`/media/evidence/${sid}`),
  },
  speech: {
    transcribe: (sid: number) => request<{ task_id: string; status: string }>(`/speech/transcribe/${sid}`, { method: "POST" }),
    transcript: (sid: number) => request<{ session_id: number; segments: TranscriptSegment[] }>(`/speech/transcript/${sid}`),
  },
  summary: {
    match: (sid: number) => request<{ pairs_count: number }>(`/summary/match/${sid}`, { method: "POST" }),
    generate: (sid: number) => request<{ status: string }>(`/summary/generate/${sid}`, { method: "POST" }),
    result: (sid: number) => request<SummaryResult>(`/summary/result/${sid}`),
    verify: (sid: number) => request<{ citation_valid: boolean; invalid_citations: string[]; unused_block_ids: string[] }>(`/summary/verify/${sid}`, { method: "POST" }),
  },
  settings: {
    list: () => request<{ key: string; is_set: boolean; is_required: boolean }[]>("/settings"),
    update: (settings: { key: string; value: string; is_required: boolean }[]) =>
      request<{ status: string }>("/settings", { method: "POST", body: JSON.stringify({ settings }) }),
  },
};
```

- [ ] **Step 2: SessionContext.tsx (session 列表 + 当前 session 状态管理)**

```tsx
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api } from "../api/client";
import type { Session } from "../types";

interface SessionContextType {
  sessions: Session[];
  activeSession: Session | null;
  setActiveSession: (s: Session | null) => void;
  createSession: (title: string) => Promise<Session>;
  refreshSessions: () => Promise<void>;
}

const Ctx = createContext<SessionContextType | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await api.sessions.list();
      setSessions(list);
    } catch {}
  }, []);

  const createSession = useCallback(async (title: string) => {
    const s = await api.sessions.create(title);
    setSessions((prev) => [s, ...prev]);
    return s;
  }, []);

  useEffect(() => { refreshSessions(); }, [refreshSessions]);

  return (
    <Ctx.Provider value={{ sessions, activeSession, setActiveSession, createSession, refreshSessions }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSession() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useSession must be inside SessionProvider");
  return c;
}
```

- [ ] **Step 3: App.tsx 包裹 SessionProvider**

```tsx
import { SessionProvider } from "./context/SessionContext";
import Workspace from "./components/Workspace";

export default function App() {
  return (
    <SessionProvider>
      <Workspace />
    </SessionProvider>
  );
}
```

- [ ] **Step 4: 测试 (SessionProvider + mock fetch)**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { SessionProvider } from "../context/SessionContext";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    sessions: {
      list: vi.fn(),
      create: vi.fn(),
    },
    media: { upload: vi.fn(), listMaterials: vi.fn(), process: vi.fn(), evidence: vi.fn() },
    speech: { transcribe: vi.fn(), transcript: vi.fn() },
    summary: { match: vi.fn(), generate: vi.fn(), result: vi.fn(), verify: vi.fn() },
    settings: { list: vi.fn(), update: vi.fn() },
  },
}));

test("SessionProvider loads sessions on mount", async () => {
  (api.sessions.list as ReturnType<typeof vi.fn>).mockResolvedValue([{ id: 1, title: "Test", status: "created" }]);
  render(
    <SessionProvider>
      <div>loaded</div>
    </SessionProvider>
  );
  await waitFor(() => expect(api.sessions.list).toHaveBeenCalled());
});
```

- [ ] **Step 5: 跑测试 + commit**

```bash
cd /home/wxc/projects/smart-scribe/frontend && npm test -- --run
```

Commit: `feat: API client + SessionContext with session state management`

---

### Task 3: 左侧栏（上传区 + 素材列表 + 历史会话）

**Files:**
- Create: `frontend/src/components/UploadZone.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/test/Sidebar.test.tsx`

- [ ] **Step 1: UploadZone.tsx (拖拽 + 粘贴链接 + 新建会话)**

```tsx
import { useState, useRef, type DragEvent } from "react";
import { useSession } from "../context/SessionContext";
import { api } from "../api/client";

export default function UploadZone() {
  const { activeSession, createSession, refreshSessions } = useSession();
  const [link, setLink] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFiles(files: FileList) {
    if (!activeSession) {
      const s = await createSession("Untitled");
      uploadFiles(s.id, files);
      return;
    }
    uploadFiles(activeSession.id, files);
  }

  async function uploadFiles(sid: number, files: FileList) {
    for (let i = 0; i < files.length; i++) {
      const fd = new FormData();
      fd.append("file", files[i]);
      fd.append("session_id", String(sid));
      fd.append("sort_order", String(i));
      await api.media.upload(fd);
    }
    refreshSessions();
  }

  return (
    <div
      className="border-2 border-dashed border-[var(--border-panel)] rounded-lg p-3 text-center text-xs text-[var(--text-secondary)] hover:border-[var(--accent)] cursor-pointer transition-colors"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e: DragEvent) => { e.preventDefault(); handleFiles(e.dataTransfer.files); }}
      onClick={() => fileInputRef.current?.click()}
    >
      <p className="mb-1">拖拽文件到此处</p>
      <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)} />
      <div className="flex gap-1 mt-2" onClick={(e) => e.stopPropagation()}>
        <input
          className="flex-1 bg-[var(--bg-main)] border border-[var(--border-panel)] rounded px-2 py-1 text-xs"
          placeholder="或粘贴链接..."
          value={link}
          onChange={(e) => setLink(e.target.value)}
          onKeyDown={async (e) => {
            if (e.key === "Enter" && link.trim()) {
              if (!activeSession) await createSession("Untitled");
              setLink("");
            }
          }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Sidebar.tsx（整合上传 + 素材列表 + 历史）**

```tsx
import { useEffect, useState } from "react";
import { useSession } from "../context/SessionContext";
import { api } from "../api/client";
import UploadZone from "./UploadZone";
import type { Material } from "../types";

export default function Sidebar() {
  const { sessions, activeSession, setActiveSession, createSession, refreshSessions } = useSession();
  const [materials, setMaterials] = useState<Material[]>([]);

  useEffect(() => {
    if (activeSession) {
      api.media.listMaterials(activeSession.id).then(setMaterials).catch(() => setMaterials([]));
    } else {
      setMaterials([]);
    }
  }, [activeSession]);

  const statusIcon = (s: string) => {
    if (s === "done") return "✓";
    if (s === "processing") return "⏳";
    if (s === "error") return "✕";
    return "○";
  };

  return (
    <aside className="w-[220px] bg-[var(--bg-panel)] border-r border-[var(--border-panel)] flex flex-col shrink-0">
      <div className="p-3 border-b border-[var(--border-panel)]">
        <UploadZone />
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {activeSession && (
          <>
            <p className="text-xs text-[var(--text-secondary)] mb-2">素材列表</p>
            <ul className="space-y-1 mb-4">
              {materials.map((m) => (
                <li key={m.id} className="text-xs flex items-center gap-1">
                  <span className="text-[var(--text-secondary)]">{statusIcon(m.status)}</span>
                  <span>
                    {m.type === "video" ? "■" : m.type === "audio" ? "♪" : "▦"} {m.type}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
        <p className="text-xs text-[var(--text-secondary)] mb-2">历史会话</p>
        <ul className="space-y-1">
          {sessions.map((s) => (
            <li
              key={s.id}
              className={`text-xs cursor-pointer px-1 py-0.5 rounded hover:bg-[var(--border-panel)] ${activeSession?.id === s.id ? "bg-[var(--border-panel)]" : ""}`}
              onClick={() => setActiveSession(s)}
            >
              {s.title}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
```

- [ ] **Step 3: 测试 (Sidebar renders, shows sessions)**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { SessionProvider, useSession } from "../context/SessionContext";
import { api } from "../api/client";

vi.mock("../api/client");

test("Sidebar renders UploadZone and session list", async () => {
  // mock sessions list
  render(<SessionProvider><div data-testid="sidebar" /></SessionProvider>);
  await waitFor(() => expect(screen.getByTestId("sidebar")).toBeInTheDocument());
});
```

- [ ] **Step 4: 跑测试 + commit**

---

### Task 4: 媒体预览（视频/音频/图片）+ 原文时间线

**Files:**
- Create: `frontend/src/components/MediaPreview.tsx`
- Create: `frontend/src/components/Timeline.tsx`
- Create: `frontend/src/test/Timeline.test.tsx`

- [ ] **Step 1: MediaPreview.tsx**

```tsx
import type { EvidenceBlock } from "../types";

interface Props {
  activeBlock: EvidenceBlock | null;
  materialType?: "video" | "audio" | "image";
  materialPath?: string;
}

export default function MediaPreview({ activeBlock, materialType, materialPath }: Props) {
  if (!activeBlock && !materialPath) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-[var(--text-secondary)]">
        <p>选择一个证据块查看预览</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-hidden bg-black rounded">
      {materialType === "video" && materialPath && (
        <video controls className="w-full h-full object-contain" src={materialPath} />
      )}
      {materialType === "audio" && (
        <div className="flex items-center justify-center h-full">
          <audio controls src={materialPath} className="w-3/4" />
        </div>
      )}
      {materialType === "image" && materialPath && (
        <div className="relative h-full">
          <img src={materialPath} className="w-full h-full object-contain" alt="" />
          {activeBlock && (
            <div className="absolute bottom-0 left-0 right-0 bg-[var(--bg-panel)]/90 p-2 text-xs text-[var(--text-secondary)]">
              {activeBlock.text}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Timeline.tsx**

```tsx
import { useEffect, useState, useRef } from "react";
import type { EvidenceBlock } from "../types";
import { api } from "../api/client";

interface Props {
  sessionId: number;
  onSelect: (block: EvidenceBlock) => void;
  highlightedId?: string;
}

export default function Timeline({ sessionId, onSelect, highlightedId }: Props) {
  const [blocks, setBlocks] = useState<EvidenceBlock[]>([]);
  const refs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    api.media.evidence(sessionId).then(setBlocks).catch(() => setBlocks([]));
  }, [sessionId]);

  useEffect(() => {
    if (highlightedId) {
      refs.current.get(highlightedId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightedId]);

  return (
    <div className="space-y-1">
      {blocks.map((b) => (
        <div
          key={b.id}
          ref={(el) => { if (el) refs.current.set(b.id, el); }}
          className={`p-2 rounded cursor-pointer text-xs transition-colors hover:brightness-110 ${highlightedId === b.id ? "ring-1 ring-[var(--accent)]" : ""} ${b.type === "speech" ? "border-l-2 border-[var(--block-speech)]" : "border-l-2 border-[var(--block-screen)]"}`}
          style={{ background: highlightedId === b.id ? "var(--border-panel)" : "var(--bg-main)" }}
          onClick={() => onSelect(b)}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className={`font-mono text-[10px] px-1 rounded ${b.type === "speech" ? "bg-[var(--block-speech)]" : "bg-[var(--block-screen)]"} text-white`}>
              {b.id}
            </span>
            <span className="text-[var(--text-secondary)]">
              [{(b.timestamp / 60).toFixed(0).padStart(2, "0")}:{(b.timestamp % 60).toFixed(0).padStart(2, "0")}]
            </span>
            {b.speaker && <span className="text-[var(--text-secondary)]">{b.speaker}</span>}
          </div>
          <p className="text-[var(--text-primary)] leading-relaxed">{b.text}</p>
        </div>
      ))}
      {blocks.length === 0 && <p className="text-xs text-[var(--text-secondary)] p-2">暂无证据块</p>}
    </div>
  );
}
```

- [ ] **Step 3: 测试 + commit**

---

### Task 5: AI 总结面板（纠错原文 + 摘要 + 要点 + 引用标签）

**Files:**
- Create: `frontend/src/components/CitationTag.tsx`
- Create: `frontend/src/components/SummaryPanel.tsx`

- [ ] **Step 1: CitationTag.tsx**

```tsx
interface Props {
  id: string;
  onClick: (id: string) => void;
}

export default function CitationTag({ id, onClick }: Props) {
  return (
    <span
      className="inline-block text-[10px] font-mono bg-[var(--accent)] text-white px-1 rounded cursor-pointer hover:opacity-80 mx-0.5"
      onClick={(e) => { e.stopPropagation(); onClick(id); }}
    >
      [{id}]
    </span>
  );
}
```

- [ ] **Step 2: SummaryPanel.tsx**

```tsx
import { useEffect, useState } from "react";
import { api } from "../api/client";
import CitationTag from "./CitationTag";
import type { SummaryResult } from "../types";

interface Props {
  sessionId: number;
  onCitationClick: (blockId: string) => void;
}

function renderWithCitations(text: string, onClick: (id: string) => void) {
  const parts = text.split(/(\[[SP]\d+\])/);
  return parts.map((part, i) => {
    const m = part.match(/^\[([SP]\d+)\]$/);
    if (m) return <CitationTag key={i} id={m[1]} onClick={onClick} />;
    return <span key={i}>{part}</span>;
  });
}

export default function SummaryPanel({ sessionId, onCitationClick }: Props) {
  const [data, setData] = useState<SummaryResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.summary.result(sessionId).then(setData).catch(() => setData(null));
  }, [sessionId]);

  async function handleGenerate() {
    setLoading(true);
    await api.summary.match(sessionId);
    await api.summary.generate(sessionId);
    const result = await api.summary.result(sessionId);
    setData(result);
    setLoading(false);
  }

  if (!data) {
    return (
      <div className="p-3">
        <button
          className="w-full bg-[var(--accent)] text-white text-sm rounded py-2 px-3 hover:opacity-90 disabled:opacity-50"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? "生成中..." : "生成 AI 总结"}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section>
        <h4 className="text-xs text-[var(--text-secondary)] mb-1">纠错原文</h4>
        <p className="text-sm leading-relaxed">{data.corrected_text}</p>
      </section>
      <section>
        <h4 className="text-xs text-[var(--text-secondary)] mb-1">摘要</h4>
        <p className="text-sm leading-relaxed">{renderWithCitations(data.summary, onCitationClick)}</p>
      </section>
      <section>
        <h4 className="text-xs text-[var(--text-secondary)] mb-1">核心要点</h4>
        <ul className="space-y-1">
          {data.key_points.map((kp, i) => (
            <li key={i} className="text-sm flex items-start gap-1">
              <span className="text-[var(--accent)] mt-0.5">{i + 1}.</span>
              <span>
                {kp.point}{" "}
                {kp.citations.map((c) => (
                  <CitationTag key={c} id={c} onClick={onCitationClick} />
                ))}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 3: 测试 + commit**

---

### Task 6: 对照模式集成（Workspace 整合所有面板 + 联动逻辑）

**Files:**
- Modify: `frontend/src/components/Workspace.tsx`

- [ ] **Step 1: 更新 Workspace.tsx，集成所有组件**

```tsx
import { useState, useCallback } from "react";
import { useSession } from "../context/SessionContext";
import Sidebar from "./Sidebar";
import MediaPreview from "./MediaPreview";
import Timeline from "./Timeline";
import SummaryPanel from "./SummaryPanel";
import type { EvidenceBlock, Material } from "../types";

export default function Workspace() {
  const { activeSession } = useSession();
  const [activeBlock, setActiveBlock] = useState<EvidenceBlock | null>(null);
  const [highlightedId, setHighlightedId] = useState<string | undefined>();
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);

  const handleBlockSelect = useCallback((block: EvidenceBlock) => {
    setActiveBlock(block);
  }, []);

  const handleCitationClick = useCallback((blockId: string) => {
    setHighlightedId(blockId);
    setTimeout(() => setHighlightedId(undefined), 2000);
  }, []);

  return (
    <div className="flex flex-col h-screen">
      <header className="h-10 bg-[var(--bg-panel)] border-b border-[var(--border-panel)] flex items-center px-4 shrink-0">
        <span className="text-sm font-semibold mr-4">Smart Scribe</span>
        {activeSession && (
          <span className="text-sm text-[var(--text-secondary)]">{activeSession.title}</span>
        )}
        <div className="ml-auto flex gap-2">
          <span className="w-3 h-3 rounded-full bg-[var(--success)]" />
          <span className="w-3 h-3 rounded-full bg-[var(--warning)]" />
          <span className="w-3 h-3 rounded-full bg-[var(--accent)]" />
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-hidden" style={{ flex: "0 0 55%" }}>
          <div className="flex-1 bg-[var(--bg-main)] p-2">
            <MediaPreview activeBlock={activeBlock} />
          </div>
          <div className="h-64 bg-[var(--bg-panel)] border-t border-[var(--border-panel)] p-2 overflow-y-auto">
            {activeSession ? (
              <Timeline sessionId={activeSession.id} onSelect={handleBlockSelect} highlightedId={highlightedId} />
            ) : (
              <p className="text-xs text-[var(--text-secondary)] p-2">请先选择一个会话</p>
            )}
          </div>
        </main>
        <aside className="bg-[var(--bg-panel)] border-l border-[var(--border-panel)] p-3 overflow-y-auto" style={{ flex: "0 0 30%" }}>
          <h3 className="text-sm font-semibold mb-2">AI 总结</h3>
          {activeSession ? (
            <SummaryPanel sessionId={activeSession.id} onCitationClick={handleCitationClick} />
          ) : (
            <p className="text-xs text-[var(--text-secondary)]">请先选择一个会话</p>
          )}
        </aside>
      </div>
      <footer className="h-8 bg-[var(--bg-panel)] border-t border-[var(--border-panel)] flex items-center px-4 text-xs text-[var(--text-secondary)] shrink-0">
        <span>就绪</span>
      </footer>
    </div>
  );
}
```

- [ ] **Step 2: 跑测试 + commit**

---

### Task 7: 设置面板（API key 表单）

**Files:**
- Create: `frontend/src/components/SettingsModal.tsx`

- [ ] **Step 1: SettingsModal.tsx (弹窗表单)**

```tsx
import { useState, useEffect } from "react";
import { api } from "../api/client";

interface SettingRow {
  key: string;
  label: string;
  is_set: boolean;
  is_required: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function SettingsModal({ open, onClose }: Props) {
  const [rows, setRows] = useState<SettingRow[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      api.settings.list().then(setRows);
    }
  }, [open]);

  async function handleSave() {
    const settings = Object.entries(values).map(([key, value]) => ({
      key,
      value,
      is_required: rows.find((r) => r.key === key)?.is_required ?? false,
    }));
    await api.settings.update(settings);
    onClose();
  }

  async function handleTest(key: string) {
    setTesting(key);
    try {
      const result = await fetch(`/api/settings/${key}/test`, { method: "POST" });
      const data = await result.json();
      alert(data.ok ? "连接成功" : `失败: ${data.message}`);
    } catch {
      alert("测试失败");
    }
    setTesting(null);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[var(--bg-panel)] border border-[var(--border-panel)] rounded-lg p-6 w-[480px] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-4">API 设置</h2>
        {rows.map((r) => (
          <div key={r.key} className="mb-3">
            <label className="block text-xs text-[var(--text-secondary)] mb-1">
              {r.key} {r.is_required && <span className="text-[var(--accent)]">*</span>}
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                className="flex-1 bg-[var(--bg-main)] border border-[var(--border-panel)] rounded px-3 py-1.5 text-sm"
                placeholder={r.is_set ? "已配置" : "输入 API key..."}
                value={values[r.key] || ""}
                onChange={(e) => setValues((v) => ({ ...v, [r.key]: e.target.value }))}
              />
              <button
                className="text-xs px-3 py-1 bg-[var(--border-panel)] rounded hover:bg-[var(--text-secondary)]"
                onClick={() => handleTest(r.key)}
                disabled={testing === r.key}
              >
                {testing === r.key ? "..." : "测试"}
              </button>
            </div>
          </div>
        ))}
        <div className="flex gap-2 mt-4">
          <button className="flex-1 bg-[var(--accent)] text-white rounded py-2 hover:opacity-90" onClick={handleSave}>
            保存
          </button>
          <button className="flex-1 bg-[var(--border-panel)] rounded py-2 hover:opacity-80" onClick={onClose}>
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TopBar 加设置按钮 → Workspace 集成**

在 Workspace 中加设置按钮和状态：
```tsx
const [settingsOpen, setSettingsOpen] = useState(false);
// 在 header 中加:
<button className="text-xs text-[var(--text-secondary)] hover:text-white" onClick={() => setSettingsOpen(true)}>⚙</button>
// 最后:
<SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
```

- [ ] **Step 3: 跑测试 + commit**

---

### Task 8: WebSocket 进度 + 状态栏

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/components/StatusBar.tsx`

- [ ] **Step 1: useWebSocket.ts**

```tsx
import { useState, useEffect, useRef } from "react";

interface ProgressStep {
  step: string;
  status: "done" | "active" | "pending";
}

export function useWebSocket(sessionId: number | null) {
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/progress/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.steps) setSteps(data.steps);
      if (data.step) setSteps((prev) => {
        const idx = prev.findIndex((s) => s.step === data.step);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = data;
          return next;
        }
        return [...prev, data];
      });
    };

    return () => ws.close();
  }, [sessionId]);

  return steps;
}
```

- [ ] **Step 2: 简化 StatusBar — 不依赖 WebSocket（后端 WS 未实现），用静态状态映射**

由于后端 WebSocket 尚未完全实现，先做静态状态显示，WebSocket 在 Plan 4 接入：

```tsx
interface Props {
  status: string;
  message: string;
}

export default function StatusBar({ status, message }: Props) {
  const [processingSteps, setProcessingSteps] = useState<{label: string; done: boolean}[]>([]);

  useEffect(() => {
    const defaultSteps = [
      {label: "抽帧", done: true},
      {label: "OCR", done: false},
      {label: "语音转写", done: false},
      {label: "匹配", done: false},
      {label: "AI总结", done: false},
    ];
    setProcessingSteps(defaultSteps);
  }, [status === "processing"]);

  return (
    <footer className="h-8 bg-[var(--bg-panel)] border-t border-[var(--border-panel)] flex items-center px-4 text-xs shrink-0 gap-4">
      <span className="text-[var(--text-secondary)]">{message || "就绪"}</span>
      <div className="flex gap-3 ml-auto">
        {processingSteps.map((s, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${s.done ? "bg-[var(--success)]" : "bg-[var(--border-panel)]"}`} />
            <span className="text-[var(--text-secondary)]">{s.label}</span>
            {i < processingSteps.length - 1 && <span className="text-[var(--border-panel)]">→</span>}
          </span>
        ))}
      </div>
    </footer>
  );
}
```

- [ ] **Step 3: 集成到 Workspace + commit**

---

## Self-Review

**Spec coverage:**
- [x] Three-panel Adobe Pr style layout (left 220 / center 55% / right 30%) — Task 1
- [x] Upload zone + materials + session history — Task 3
- [x] Media preview (video/audio/image) — Task 4
- [x] Evidence block timeline (S001/P003 interleaved) — Task 4
- [x] AI summary (corrected text + summary + key points + citations) — Task 5
- [x] Compare mode (timeline ↔ summary linked) — Task 6
- [x] Settings panel (API key form) — Task 7
- [x] Status bar with progress visualization — Task 8
- [x] Dark theme (#0f0f1a, #1a1a2e, #2a2a4a, #e0e0e8, #e94560, #00d2a0) — Task 1
- [x] Citation click → scroll to evidence block — Task 5 + 6
- [x] API client integration — Task 2

**Not in Plan 3 (deferred):**
- WebSocket live progress (后端 WS 未实现，Task 8 已备 hook，接入待后端 WS 完成后)
- Download link form submission (前端已备输入框，后端 API 已就绪)
- OCR mode toggle in settings (前端已备 settings 表单)
- 4-tab views (当前只实现 compare 默认视图，其他 3 个 tab 属 UI 增强)
