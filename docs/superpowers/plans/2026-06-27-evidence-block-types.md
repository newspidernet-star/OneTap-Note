# Evidence Block Type Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distinguish evidence blocks by source media type (`speech`, `video_frame`, `image`, `document`) in both backend storage and the frontend timeline.

**Architecture:** Extend `EvidenceBlock.type` values, update the pipeline to write the correct type per material source, broaden matcher/summarizer filters to treat all non-speech types as citation material, and adapt the timeline UI to render the new categories.

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy / SQLite; React + TypeScript + Tailwind CSS.

## Global Constraints
- SQLite string column for `EvidenceBlock.type`; no schema migration needed.
- Existing `type="screen"` rows must remain readable (treat as `video_frame`).
- No new frontend dependencies.
- Matcher must still pair every speech block with every material block.

---

### Task 1: Pipeline writes `video_frame` and `image` types

**Files:**
- Modify: `backend/app/services/pipeline.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Material.type` values `"video"`, `"image"`
- Produces: `EvidenceBlock.type` values `"video_frame"` and `"image"`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_pipeline.py`:

```python
def test_video_material_creates_video_frame_blocks(db, tmp_path):
    from app.services.pipeline import process_session
    from app.models import Session, Material

    session = Session(title="test", status="created", created_at="now", updated_at="now")
    db.add(session)
    db.commit()

    # Create a tiny valid mp4 via ffmpeg
    video_path = tmp_path / "sample.mp4"
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=1",
        "-pix_fmt", "yuv420p", str(video_path)
    ], check=True, capture_output=True)

    material = Material(session_id=session.id, type="video", source="upload", file_path=str(video_path), status="pending")
    db.add(material)
    db.commit()

    result = process_session(session.id, db)
    db.refresh(material)

    assert material.status == "done"
    blocks = db.query(EvidenceBlock).filter_by(session_id=session.id).all()
    assert len(blocks) > 0
    assert all(b.type == "video_frame" for b in blocks)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_pipeline.py::test_video_material_creates_video_frame_blocks -v`

Expected: FAIL with assertion `assert 'screen' == 'video_frame'` or similar.

- [ ] **Step 3: Modify `_process_video`**

In `backend/app/services/pipeline.py`, change both `type="screen"` assignments inside `_process_video` to `type="video_frame"`.

Old:
```python
type="screen",
```

New:
```python
type="video_frame",
```

- [ ] **Step 4: Modify `_process_image`**

In the same file, change `type="screen"` inside `_process_image` to `type="image"`.

Old:
```python
type="screen",
```

New:
```python
type="image",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_pipeline.py::test_video_material_creates_video_frame_blocks -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat(pipeline): classify video and image evidence blocks by source type"
```

---

### Task 2: Matcher treats new material types as citation targets

**Files:**
- Modify: `backend/app/services/matcher.py`
- Test: `backend/tests/test_matcher.py`

**Interfaces:**
- Consumes: `EvidenceBlock.type` in `{"video_frame", "image", "document", "screen"}`
- Produces: `Match` rows pairing `speech` blocks with all material blocks

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_matcher.py` (or create it):

```python
def test_match_includes_video_frame_and_image_blocks(db):
    from app.services.matcher import match_evidence
    from app.models import EvidenceBlock, Session

    session = Session(title="test", status="created", created_at="now", updated_at="now")
    db.add(session)
    db.commit()

    s1 = EvidenceBlock(block_id="S001", session_id=session.id, type="speech", timestamp=0.0, text="voice")
    v1 = EvidenceBlock(block_id="V001", session_id=session.id, type="video_frame", timestamp=1.0, text="frame")
    i1 = EvidenceBlock(block_id="I001", session_id=session.id, type="image", timestamp=2.0, text="photo")
    db.add_all([s1, v1, i1])
    db.commit()

    match_evidence(session.id, db)
    matches = db.query(Match).filter_by(session_id=session.id).all()
    screen_block_ids = {m.screen_block_id for m in matches}
    assert v1.id in screen_block_ids
    assert i1.id in screen_block_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_matcher.py::test_match_includes_video_frame_and_image_blocks -v`

Expected: FAIL because matcher only queries `type="screen"`.

- [ ] **Step 3: Update matcher query**

In `backend/app/services/matcher.py`, replace:

```python
p_blocks = db.query(EvidenceBlock).filter_by(session_id=session_id, type="screen").all()
```

with:

```python
p_blocks = db.query(EvidenceBlock).filter(
    EvidenceBlock.session_id == session_id,
    EvidenceBlock.type.in_(["video_frame", "image", "document", "screen"])
).all()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_matcher.py::test_match_includes_video_frame_and_image_blocks -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/matcher.py backend/tests/test_matcher.py
git commit -m "feat(matcher): pair speech blocks with video_frame, image, document, and legacy screen blocks"
```

---

### Task 3: Summarizer handles new material types

**Files:**
- Modify: `backend/app/services/summarizer.py`
- Test: `backend/tests/test_summarizer.py`

**Interfaces:**
- Consumes: `EvidenceBlock.type` values and `Match` rows
- Produces: summary with valid citations to `video_frame`/`image`/`document` blocks

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_summarizer.py`:

```python
def test_summary_cites_video_frame_and_image_blocks(db, monkeypatch):
    from app.services.summarizer import generate_summary
    from app.models import EvidenceBlock, Session, Match

    session = Session(title="test", status="created", created_at="now", updated_at="now")
    db.add(session)
    db.commit()

    s1 = EvidenceBlock(block_id="S001", session_id=session.id, type="speech", timestamp=0.0, text="电磁感应")
    v1 = EvidenceBlock(block_id="V001", session_id=session.id, type="video_frame", timestamp=1.0, text="法拉第定律")
    db.add_all([s1, v1])
    db.commit()

    m = Match(speech_block_id=s1.id, screen_block_id=v1.id, score=1.0, time_sim=1.0, keyword_sim=1.0, semantic_sim=1.0)
    db.add(m)
    db.commit()

    # Mock DeepSeek call to avoid network
    monkeypatch.setattr("app.services.summarizer._call_deepseek", lambda *a, **k: {
        "summary": "本课讲电磁感应。",
        "key_points": [{"point": "法拉第定律", "citations": ["V001"]}],
        "corrected_text": "电磁感应",
        "unused_block_ids": [],
        "citation_valid": True,
        "invalid_citations": [],
        "corrections": []
    })

    result = generate_summary(session.id, db)
    assert "V001" in str(result.key_points)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_summarizer.py::test_summary_cites_video_frame_and_image_blocks -v`

Expected: FAIL due to `type == "screen"` checks ignoring `video_frame`.

- [ ] **Step 3: Update summarizer type checks**

In `backend/app/services/summarizer.py`, find all occurrences of `type == "screen"` and `"screen"` and replace with a material-type check.

Define a helper near the top:

```python
_MATERIAL_TYPES = {"video_frame", "image", "document", "screen"}
```

Replace checks like:

```python
if b.type == "screen":
```

with:

```python
if b.type in _MATERIAL_TYPES:
```

And:

```python
Match.speech_block_id.in_([b.id for b in blocks if b.type == "speech"])
```

remains unchanged; update only the screen side:

```python
Match.screen_block_id.in_([b.id for b in blocks if b.type in _MATERIAL_TYPES])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_summarizer.py::test_summary_cites_video_frame_and_image_blocks -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/summarizer.py backend/tests/test_summarizer.py
git commit -m "feat(summarizer): allow citations to video_frame, image, document, and legacy screen blocks"
```

---

### Task 4: Frontend timeline renders new material types

**Files:**
- Modify: `frontend/src/components/TimelinePanel.tsx`
- Test: `npm run build` (no unit tests for this component)

**Interfaces:**
- Consumes: evidence block `type` in `{"speech", "video_frame", "image", "document", "screen"}`
- Produces: native right-panel timeline with correct node labels and category tabs

- [ ] **Step 1: Update source detection**

In `frontend/src/components/TimelinePanel.tsx`, change:

```typescript
const isSource = (block: EvidenceBlock) => block.type !== "speech";
```

to:

```typescript
const MATERIAL_TYPES = new Set(["video_frame", "image", "document", "screen"]);
const isSource = (block: EvidenceBlock) => MATERIAL_TYPES.has(block.type);
```

- [ ] **Step 2: Update node label logic**

Change:

```typescript
const nodeLabel = (block: EvidenceBlock) => {
  if (isSource(block)) return "P";
  const name = block.speaker || "讲";
  return name.slice(0, 1);
};
```

to:

```typescript
const nodeLabel = (block: EvidenceBlock) => {
  if (block.type === "video_frame") return "V";
  if (block.type === "image" || block.type === "screen") return "P";
  if (block.type === "document") return "D";
  const name = block.speaker || "讲";
  return name.slice(0, 1);
};
```

- [ ] **Step 3: Update speaker tab derivation**

Change:

```typescript
const speakers = Array.from(
  new Set(blocks.filter((b) => b.type === "speech").map((b) => b.speaker || "主讲"))
);
```

This can stay as-is.

- [ ] **Step 4: Update card identity label**

Change:

```typescript
<span className="truncate">
  {speech ? block.speaker || "主讲" : "课件截图"}
</span>
```

to:

```typescript
<span className="truncate">
  {speech
    ? block.speaker || "主讲"
    : block.type === "video_frame"
      ? "视频帧"
      : block.type === "image" || block.type === "screen"
        ? "课件截图"
        : "文档页面"}
</span>
```

- [ ] **Step 5: Build frontend**

Run: `npm run build`

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TimelinePanel.tsx
git commit -m "feat(timeline): render video_frame, image, document, and legacy screen evidence blocks"
```

---

### Task 5: Verification

- [ ] **Step 1: Run backend tests**

Run: `pytest backend/tests -q`

Expected: all tests pass.

- [ ] **Step 2: Run frontend build**

Run: `npm run build`

Expected: build succeeds.

- [ ] **Step 3: Manual smoke test**

1. Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Upload a video file → verify evidence blocks appear with `type="video_frame"`
4. Upload an image file → verify evidence blocks appear with `type="image"`
5. Click "生成 AI 总结" (with APIs configured) → verify summary cites `V001` / `I001` correctly
6. Verify timeline shows "V" node for video frames and "P" node for images

- [ ] **Step 4: Commit verification log (optional)**

```bash
git add docs/superpowers/specs/2026-06-27-evidence-block-types-design.md docs/superpowers/plans/2026-06-27-evidence-block-types.md
git commit -m "docs: evidence block type classification spec and plan"
```

---

## Self-Review Checklist

- [x] Spec coverage: pipeline types, matcher filters, summarizer filters, frontend rendering, legacy compatibility — all have tasks.
- [x] No placeholders: every step has concrete code or exact commands.
- [x] Type consistency: `_MATERIAL_TYPES` is used consistently in matcher and summarizer; frontend `MATERIAL_TYPES` matches backend set.
- [x] Backward compatibility: legacy `screen` type is included in material filters and rendered as "课件截图" / "P".
