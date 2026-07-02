# Evidence Block Type Classification

## Goal
Make the backend distinguish evidence blocks by their source media type so the timeline can render meaningful categories: speech, video frame, image, and document.

## Background
Currently, the backend stores every non-speech evidence block as `type="screen"`. The redesigned timeline shows a "资料" category for all non-speech blocks, but it cannot tell whether a block came from a video frame, an uploaded image, or a document page. This makes the UI less informative and limits future features like video-frame citations vs. image citations.

## Proposed Change
Extend `EvidenceBlock.type` to support four values:

| Source material | Current `type` | New `type` |
|-----------------|----------------|------------|
| Audio/video transcript | `speech` | `speech` |
| Video frame OCR | `screen` | `video_frame` |
| Uploaded image OCR | `screen` | `image` |
| Document / PPT page (future) | `screen` | `document` |

## Backend Changes

### `backend/app/services/pipeline.py`
- `_process_video`: create evidence blocks with `type="video_frame"` instead of `"screen"`.
- `_process_image`: create evidence blocks with `type="image"` instead of `"screen"`.
- `_process_speech`: keep `type="speech"`.

### `backend/app/services/matcher.py`
- Speech blocks: keep filter `type="speech"`.
- Material blocks: change filter from `type="screen"` to `type.in_(["video_frame", "image", "document"])`.

### `backend/app/services/summarizer.py`
- Update all `b.type == "screen"` checks to treat `"video_frame"`, `"image"`, and `"document"` as citation material.
- Update `Match.screen_block_id` queries to include the three material types.

### `backend/app/api/media.py`
- No change required; the `/api/media/evidence/{session_id}` endpoint already returns `b.type` as-is.

### Database Compatibility
- SQLite uses string columns, so no schema migration is needed for new values.
- Existing rows with `type="screen"` will be treated as `video_frame` at query time to avoid breaking old sessions.

## Frontend Changes

### `frontend/src/components/TimelinePanel.tsx`
- Update `isSource()` to return true for `"video_frame"`, `"image"`, and `"document"`.
- Update node labels:
  - `speech`: speaker initial (unchanged)
  - `video_frame`: "V" or video icon
  - `image`: image icon
  - `document`: "D" or document icon
- Keep the "资料" filter tab and red accent color for all material types; optionally add sub-colors later.

### `frontend/src/components/TimelinePanel.tsx` node colors
- Keep blue theme for `speech`.
- Keep red theme for material types, with possible future differentiation.

## Acceptance Criteria
1. Uploading a video produces evidence blocks with `type="video_frame"`.
2. Uploading an image produces evidence blocks with `type="image"`.
3. Uploading audio produces only `type="speech"` blocks.
4. Matcher still pairs speech blocks with all material blocks.
5. Summarizer still cites material blocks correctly.
6. Timeline renders material blocks under the "资料" category without errors.
7. Old sessions with `type="screen"` continue to work.

## Out of Scope
- Adding separate filter tabs for `video_frame` vs `image` vs `document`.
- Different accent colors per material subtype.
- Document/PPT ingestion (the `document` type is reserved for future use).
