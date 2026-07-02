# Session Delete, Retry & Rename — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add session delete (with cascade DB + disk cleanup), per-step failure retry, and session rename to Smart Scribe.

**Architecture:** Backend adds DELETE/PATCH endpoints + error_message persistence + try/except guards. Frontend adds delete confirm UI, retry buttons, title save-on-blur. Existing idempotent endpoints (process/transcribe/match/generate) serve as retry without new routes.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite (back), React + TanStack Query + framer-motion (front)

## Global Constraints

- No new dependencies. Use existing FastAPI, SQLAlchemy, React Query stack.
- DB FK constraints are NOT ON DELETE CASCADE — always delete child rows explicitly before parent.
- Error messages stored on Session model, not a separate error table.
- Frontend mutations follow existing `safeFetch` + `useMutation` pattern from `lib/api.ts`.
- All task steps are sequential within each task.

---

### Task 1: Add error_message field to Session model

**Files:**
- Modify: `backend/app/models/session.py:7-16`

**Interfaces:**
- Produces: `Session.error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)`

- [ ] **Step 1: Add the column**

```python
# In class Session(Base), after line 14 (updated_at), insert:
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

- [ ] **Step 2: Add error_message to SessionOut schema**

In `backend/app/schemas/media.py`, add `error_message` to `SessionOut`:

```python
class SessionOut(BaseModel):
    id: int
    title: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Restart backend to pick up schema change**

```bash
cd /home/wxc/projects/smart-scribe && kill $(pgrep -f "uvicorn") 2>/dev/null; sleep 1
cd backend && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/opencode/backend.log 2>&1 & disown
sleep 2 && curl -s http://localhost:8000/api/health
```
Expected: `{"status":"ok"}`

---

### Task 2: Add DELETE /api/sessions/{session_id} endpoint

**Files:**
- Modify: `backend/app/api/media.py`

**Interfaces:**
- Produces: `DELETE /api/sessions/{session_id}` → `{"ok": true}` or 404

- [ ] **Step 1: Add imports at top of media.py**

```python
# Add after line 1:
import shutil
# Add to line 5 imports:
from app.models import EvidenceBlock, Material, Match, Summary, Session as SessionModel
```

Currently line 8 imports `EvidenceBlock, Material, Session as SessionModel`. Need to add `Match`, `Summary`, and `Transcript`, `TranscriptSegment`. Also need `from app.config import get_settings` already imported at line 7.

Edit line 8 from:
```python
from app.models import EvidenceBlock, Material, Session as SessionModel
```
to:
```python
from app.models import EvidenceBlock, Material, Match, Summary, Session as SessionModel, Transcript, TranscriptSegment
```

- [ ] **Step 2: Add DELETE route at end of media.py**

Insert after line 100 (after the process_materials route, before list_evidence):

```python
@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(Match).filter(
        Match.speech_block_id.in_(
            db.query(EvidenceBlock.id).filter(EvidenceBlock.session_id == session_id)
        )
    ).delete(synchronize_session=False)

    db.query(TranscriptSegment).filter(
        TranscriptSegment.transcript_id.in_(
            db.query(Transcript.id).filter(Transcript.session_id == session_id)
        )
    ).delete(synchronize_session=False)

    db.query(Transcript).filter(Transcript.session_id == session_id).delete(synchronize_session=False)
    db.query(EvidenceBlock).filter(EvidenceBlock.session_id == session_id).delete(synchronize_session=False)
    db.query(Material).filter(Material.session_id == session_id).delete(synchronize_session=False)
    db.query(Summary).filter(Summary.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()

    storage_dir = get_settings().storage_dir / f"session_{session_id}"
    if storage_dir.exists():
        shutil.rmtree(str(storage_dir))

    return {"ok": True}
```

- [ ] **Step 3: Verify endpoint**

```bash
curl -X DELETE http://localhost:8000/api/sessions/1
```
If session 1 exists: `{"ok":true}`
If not: `{"detail":"Session not found"}` with 404

---

### Task 3: Add PATCH /api/sessions/{session_id} endpoint

**Files:**
- Modify: `backend/app/api/media.py`

**Interfaces:**
- Produces: `PATCH /api/sessions/{session_id}` body `{"title":"..."}` → session object

- [ ] **Step 1: Add Pydantic schema**

Check if `SessionCreate` schema already exists. If it has only `title`, reuse it. If not, add inline:

```python
# Add this route after the DELETE route, before list_evidence:

from pydantic import BaseModel

class SessionUpdate(BaseModel):
    title: str

@router.patch("/api/sessions/{session_id}")
def update_session(session_id: int, body: SessionUpdate, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = body.title[:200]
    session.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"id": session.id, "title": session.title, "status": session.status, "created_at": session.created_at, "updated_at": session.updated_at, "error_message": session.error_message}
```

- [ ] **Step 2: Verify**

```bash
curl -X PATCH http://localhost:8000/api/sessions/1 -H "Content-Type: application/json" -d '{"title":"New Name"}'
```

---

### Task 4: Add error handling to process endpoint

**Files:**
- Modify: `backend/app/api/media.py:88-100`

- [ ] **Step 1: Wrap process_materials in try/except**

Replace lines 88-100 (the process_materials function) with:

```python
@router.post("/api/media/session/{session_id}/process")
def process_materials(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        result = process_session(session_id, db)
        session.status = "done"
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        return {
            "frames_count": result.frames_count,
            "ocr_pages_count": result.ocr_pages_count,
            "evidence_block_ids": result.evidence_block_ids,
        }
    except Exception as e:
        session.status = "failed"
        session.error_message = str(e)[:500]
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Verify error propagation**

Upload a file that will cause processing failure (e.g., a text file), trigger process, then check:

```bash
curl http://localhost:8000/api/sessions | python3 -m json.tool
```
Verify that the session shows `"status": "failed"` and `"error_message"` is populated.

---

### Task 5: Add error handling to transcribe endpoint

**Files:**
- Modify: `backend/app/api/speech.py:13-23`

- [ ] **Step 1: Import Session model and add try/except**

Add import at top:
```python
from app.models import Material, Session as SessionModel, Transcript, TranscriptSegment
```
(Add `Session as SessionModel` to existing line 5)

Replace lines 13-23 with:

```python
@router.post("/transcribe/{session_id}", response_model=TranscribeResponse)
async def start_transcribe(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    audio_materials = db.query(Material).filter_by(session_id=session_id, type="audio").all()
    video_materials = db.query(Material).filter_by(session_id=session_id, type="video").all()
    candidates = audio_materials + video_materials
    if not candidates:
        raise HTTPException(status_code=404, detail="会话没有音频或视频素材")
    material = candidates[0]
    try:
        audio_path = prepare_audio(material)
        transcribe(audio_path, session_id, db)
        session.error_message = None
        db.commit()
        return TranscribeResponse(task_id="done", status="completed")
    except Exception as e:
        session.status = "failed"
        session.error_message = str(e)[:500]
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

Also add `from datetime import datetime, timezone` to speech.py imports.

- [ ] **Step 2: Verify**

Restart backend and check curl output after triggering transcription on a session with no API keys configured.

---

### Task 6: Add error handling to match and generate endpoints

**Files:**
- Modify: `backend/app/api/summary.py:25-39`

- [ ] **Step 1: Import Session model and datetime**

Add to imports:
```python
from datetime import datetime, timezone
from app.models import Session as SessionModel, Summary
```

- [ ] **Step 2: Wrap run_match**

Replace lines 25-28 with:

```python
@router.post("/match/{session_id}", response_model=MatchResponse)
def run_match(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        matches = match_evidence(session_id, db)
        session.error_message = None
        db.commit()
        return MatchResponse(pairs_count=len(matches))
    except Exception as e:
        session.status = "failed"
        session.error_message = str(e)[:500]
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: Wrap run_generate**

Replace lines 31-39 with:

```python
@router.post("/generate/{session_id}", response_model=SummaryGenerateResponse)
def run_generate(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        clear_summary(session_id, db)
        result = generate_summary(session_id, db)
        verification = verify_citations(result, session_id, db)
        result["_citation_valid"] = verification["valid"]
        result["_invalid_citations"] = verification["invalid_ids"]
        save_summary(result, session_id, db)
        session.error_message = None
        db.commit()
        return SummaryGenerateResponse(status="completed")
    except Exception as e:
        session.status = "failed"
        session.error_message = str(e)[:500]
        session.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Verify**

```bash
curl -X POST http://localhost:8000/api/summary/generate/1 2>&1
```
Check that failed sessions show error_message in GET /api/sessions.

---

### Task 7: Add useDeleteSession mutation to api.ts

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add mutation hook**

Insert after `useProcessSession` (around line 142):

```typescript
export const useDeleteSession = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string }, TContext>({
    mutationFn: ({ sessionId }) =>
      safeFetch<any>(`/api/sessions/${toIntId(sessionId)}`, { method: "DELETE" }),
    ...options?.mutation,
  });
};
```

---

### Task 8: Add useRenameSession mutation to api.ts

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add mutation hook**

Insert after `useDeleteSession`:

```typescript
export const useRenameSession = <TError = unknown, TContext = unknown>(
  options?: {
    mutation?: UseMutationOptions<any, TError, { sessionId: string; title: string }, TContext>;
  }
) => {
  return useMutation<any, TError, { sessionId: string; title: string }, TContext>({
    mutationFn: ({ sessionId, title }) =>
      safeFetch<any>(`/api/sessions/${toIntId(sessionId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      }),
    ...options?.mutation,
  });
};
```

- [ ] **Step 2: Export to frontend consumers**

The hooks are exported inline with `export const`. No additional export block needed.

---

### Task 9: Add delete button + confirm dialog to sidebar

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

- [ ] **Step 1: Import delete mutation**

Add to imports from `@/lib/api`:
```typescript
useDeleteSession,
```
(add to the existing import block at line 17-18)

Also add `Trash2` icon to lucide-react import at line 2.

- [ ] **Step 2: Add delete mutation and state**

After line ~155 (after `const generateMutation = ...`), add:

```typescript
const deleteMut = useDeleteSession({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() });
      setDeleteTarget(null);
    },
  },
});
const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
```

- [ ] **Step 3: Add delete button to each session row**

In the sidebar session list (currently around lines 389-402, the `realSessions.map` block), modify each session button to include a delete icon on hover. Replace the session button block:

Find the `<button>` inside `realSessions.map` (around line 396-402):

```tsx
{realSessions.map(s => (
  <button key={s.id} onClick={() => setActiveSessionId(s.id)}
    className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center gap-2 transition-colors ${activeSessionId === s.id ? 'bg-primary/10 text-primary' : 'hover:bg-white/5 text-muted-foreground'}`}
  >
    <div className={`w-1.5 h-1.5 rounded-full ${s.status === 'done' ? 'bg-green-500' : s.status === 'processing' ? 'bg-amber-500' : 'bg-muted-foreground/40'}`} />
    <span className="truncate">{s.title}</span>
  </button>
))}
```

Replace with:

```tsx
{realSessions.map(s => (
  <div key={s.id} className="group relative">
    <button onClick={() => setActiveSessionId(s.id)}
      className={`w-full text-left px-3 py-2 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors ${activeSessionId === s.id ? 'bg-primary/10 text-primary' : 'hover:bg-white/5 text-muted-foreground'}`}
    >
      <div className={`w-1.5 h-1.5 rounded-full ${s.status === 'failed' ? 'bg-red-500' : s.status === 'done' ? 'bg-green-500' : s.status === 'processing' ? 'bg-amber-500' : 'bg-muted-foreground/40'}`} />
      <span className="truncate">{s.title}</span>
    </button>
    <button
      onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
      className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all"
      title="删除"
    >
      <Trash2 className="w-3.5 h-3.5" />
    </button>
  </div>
))}
```

- [ ] **Step 4: Add confirm modal**

At the end of the return block, just before the closing `</div>` of the root element (before the settings modal AnimatePresence), add:

```tsx
<AnimatePresence>
  {deleteTarget && (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
      onClick={() => setDeleteTarget(null)}
    >
      <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
        onClick={e => e.stopPropagation()}
        className="bg-card border border-border rounded-2xl p-6 w-full max-w-sm shadow-2xl"
      >
        <h3 className="font-semibold text-foreground text-lg mb-2">删除会话</h3>
        <p className="text-sm text-muted-foreground mb-6">
          确定删除「{deleteTarget.title}」吗？<br />
          <span className="text-red-400 text-xs">媒体文件、证据块、总结将一并清除。</span>
        </p>
        <div className="flex gap-2 justify-end">
          <button onClick={() => setDeleteTarget(null)}
            className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-foreground/5 transition-colors">
            取消
          </button>
          <button onClick={() => {
            deleteMut.mutate({ sessionId: deleteTarget.id });
            if (activeSessionId === deleteTarget.id) {
              const remaining = realSessions.filter(s => s.id !== deleteTarget.id);
              if (remaining.length > 0) setActiveSessionId(remaining[0].id);
              else setActiveSessionId(MOCK_SESSION_ID);
            }
          }}
            disabled={deleteMut.isPending}
            className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
            {deleteMut.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            删除
          </button>
        </div>
      </motion.div>
    </motion.div>
  )}
</AnimatePresence>
```

---

### Task 10: Wire session rename on title input blur

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

- [ ] **Step 1: Import rename mutation**

Add `useRenameSession` to the import from `@/lib/api`.

- [ ] **Step 2: Add rename mutation**

After the deleteMut declaration, add:

```typescript
const renameMut = useRenameSession();
```

- [ ] **Step 3: Replace title input with controlled version**

Current title input (in the header):
```tsx
<input key={activeSession?.id || "mock"} type="text" defaultValue={activeSession?.title || ""} className="bg-transparent border-none outline-none focus:ring-1 ring-primary rounded px-2 text-sm font-medium w-64" />
```

Replace with:
```tsx
<input
  key={activeSession?.id || "mock"}
  type="text"
  defaultValue={activeSession?.title || ""}
  onBlur={(e) => {
    const newTitle = e.target.value.trim();
    if (newTitle && activeSessionId && !isMock && newTitle !== activeSession?.title) {
      renameMut.mutate({ sessionId: activeSessionId, title: newTitle });
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() });
    }
  }}
  className="bg-transparent border-none outline-none focus:ring-1 ring-primary rounded px-2 text-sm font-medium w-64"
/>
```

---

### Task 11: Add retry button to UploadProgress error state

**Files:**
- Modify: `frontend/src/components/UploadProgress.tsx`

- [ ] **Step 1: Add errorMessage and onRetry props**

Change the interface from:
```typescript
interface Props {
  status: UploadStatus;
}
```
to:
```typescript
interface Props {
  status: UploadStatus;
  errorMessage?: string;
  onRetry?: () => void;
}
```

- [ ] **Step 2: Update destructure and render**

Change:
```typescript
export default function UploadProgress({ status }: Props) {
```
to:
```typescript
export default function UploadProgress({ status, errorMessage, onRetry }: Props) {
```

Replace the error text line (currently `{status === "error" && <p className="text-[11px] text-red-400/70">请检查文件或 API 设置</p>}`) with:

```tsx
{status === "error" && (
  <div className="flex flex-col items-center gap-2">
    <p className="text-[11px] text-red-400/70 text-center max-w-[200px]">
      {errorMessage || "请检查文件或 API 设置"}
    </p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-4 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
      >
        <RefreshCw className="w-3 h-3" /> 重新处理
      </button>
    )}
  </div>
)}
```

- [ ] **Step 3: Add RefreshCw import**

Add to lucide-react import line:
```typescript
import { ..., RefreshCw } from "lucide-react";
```

---

### Task 12: Wire error message and retry to UploadProgress in Workstation

**Files:**
- Modify: `frontend/src/pages/Workstation.tsx`

- [ ] **Step 1: Get pipelineError from activeSession**

After the `isProcessing` line, add:

```typescript
const pipelineError = activeSession?.error_message || generateError || undefined;
```

- [ ] **Step 2: Update uploadStatus to include pipelineError**

The current uploadStatus derivation already handles `generateError → "error"`. Now it should also check `pipelineError`:

```typescript
const uploadStatus: UploadStatus = pipelineError && !matchMut.isPending && !generateMutation.isPending
  ? "error"
  : uploadRunning || uploadMut.isPending
    ? "uploading"
    : processMut.isPending
      ? "ocr"
      : transcribeMut.isPending
        ? "transcribing"
        : (activeSession?.status === 'done' || activeSession?.status === 'processing') &&
          !(uploadMut.isPending || processMut.isPending || transcribeMut.isPending)
          ? "done"
          : "idle";
```

- [ ] **Step 3: Pass errorMessage and onRetry to UploadProgress**

Find `<UploadProgress status={uploadStatus} />` in the render (inside the upload area AnimatePresence) and change to:

```tsx
<UploadProgress
  status={uploadStatus}
  errorMessage={pipelineError}
  onRetry={() => {
    if (activeSessionId && !isMock) {
      processMut.mutate({ sessionId: activeSessionId });
    }
  }}
/>
```

- [ ] **Step 4: Clean up buttonStatus derivation**

The buttonStatus should check error separately from pipelineError:

```typescript
const buttonStatus: ButtonStatus = generateError
  ? "error"
  : matchMut.isPending
    ? "matching"
    : generateMutation.isPending
      ? "summarizing"
      : displaySummary
        ? "done"
        : "idle";
```

This is already mostly correct — ensure `generateError` is the `pipelineError` when from match/generate, but NOT from upload/process/transcribe failures.

- [ ] **Step 5: Add onError to process/transcribe/match mutations in Workstation**

After the existing mutation declarations (around line ~152-156), add onError callbacks so the frontend picks up backend-set error_message:

```typescript
const processMut = useProcessSession({
  mutation: {
    onError: () => {
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() });
    },
  },
});

const transcribeMut = useTranscribe({
  mutation: {
    onError: () => {
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() });
    },
  },
});

const matchMut = useMatchEvidence({
  mutation: {
    onError: () => {
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() });
    },
  },
});
```

Replace the existing bare `useProcessSession()` / `useTranscribe()` / `useMatchEvidence()` calls with these.

- [ ] **Step 6: Verify with build**

```bash
cd /home/wxc/projects/smart-scribe/frontend && timeout 60 npm run build 2>&1 | tail -5
```
Expected: `✓ built in ...`
