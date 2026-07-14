# Engineering metrics and reproducible baselines

This document separates measured evidence from product claims. Numbers are only promoted into release notes or resume material when they can be reproduced from a script, a test report, or a real processing sample.

## Baseline snapshot (2026-07-15)

Measurement environment:

- Windows 11, AMD64
- Node.js `v24.14.1`, npm `11.11.0`, Python `3.11.9`
- Repository baseline commit: `b6d7ed6`
- Three frontend production builds on the same machine

| Area | Result | Method |
| --- | --- | --- |
| Repository scale | 168 commits, 118 core source files (81 frontend, 37 backend), 22 backend test files | `git ls-files` and `git rev-list` |
| Frontend production build | median 6.459 s across 3 runs | `scripts/collect-engineering-baseline.ps1 -BuildRuns 3` |
| JavaScript output | 815.27 KiB raw, 251.85 KiB gzip | generated `frontend/dist/assets` |
| CSS output | 164.19 KiB raw, 24.81 KiB gzip | generated `frontend/dist/assets` |
| ASR reliability tests | 11 passed in 0.07 s (command time 1.740 s) | focused pytest suite |
| Full backend suite | 84 passed, 6 failed, 3 warnings in 4.82 s | full pytest suite |
| Windows Setup artifact | 94.47 MiB | `desktop/dist-installer/One-Tap-Note-Setup-0.3.3.exe` |
| Windows portable ZIP | 120.18 MiB | `release/OneTap-Note-Windows.zip` |

The six full-suite failures are existing compatibility/test-maintenance issues in frame strategy, OCR, and summarizer mocks. They are retained in the report rather than being hidden by the metrics command.

## Large timeline before/after comparison

The benchmark compares the parent of `ee644e5` with `ee644e5` and later. Both versions use the same local database, the same 53-minute session, the same 784 evidence blocks, a `1440 x 900` Chromium viewport, and five runs per version.

| Metric | Before (`c20de90`) | After (`ee644e5`+) | Change |
| --- | ---: | ---: | ---: |
| Timeline open median | 812.23 ms | 346.76 ms | 57.3% lower |
| Timeline open range | 756.08-878.47 ms | 328.61-399.35 ms | narrower after optimization |
| Scroll frame p95 median | 18.30 ms | 18.30 ms | unchanged |
| Long-task time during full scroll | 573 ms | 209 ms | 63.5% lower |

The optimization removes per-row Framer Motion animation for lists over 120 items and applies CSS `content-visibility: auto` with an intrinsic row size. The result primarily reduces panel-opening work and total main-thread blocking while preserving scrolling frame cadence.

Reproduce this comparison with:

```powershell
backend\.venv\Scripts\python.exe scripts\benchmark-timeline.py `
  --target "current=http://127.0.0.1:5175" `
  --session-title "技术变革与历史循环" `
  --expected-blocks 784 `
  --runs 5 `
  --output ".metrics\reports\timeline-current"
```

The benchmark intentionally writes reports under ignored `.metrics/`. It does not add the user's media, transcript, note, or API credentials to Git.

## Processing-time collection

The processing progress service now writes one timing-only JSON line after a run finishes or fails:

```text
backend/storage/metrics/processing-runs.jsonl
```

Stored fields are limited to a random run ID, status, start/finish time, total duration, stage name, and stage duration. Session IDs, links, filenames, transcripts, notes, model output, error details, and API keys are not stored.

Use real tasks to accumulate representative samples. After enough samples exist, the baseline command reports median, minimum, and maximum duration for each stage. A useful first threshold is at least 10 runs across short, medium, and long videos; one successful run is not a performance claim.

Set `ONE_TAP_NOTE_COLLECT_METRICS=0` to disable local collection. Tests disable it automatically so test runs never pollute real samples.

## Desktop startup collection

The desktop shell records cold and warm startup timing under Electron's local user-data directory:

```text
metrics/startup-runs.jsonl
```

Each entry records only application version, packaged/development mode, whether first-run installation was required, health-check duration, backend-ready time, page-load time, and total startup time. It does not store project content or credentials.

After normal use has collected at least five cold starts and five warm starts, rerun the baseline collector to produce median and range values. Installer execution is intentionally excluded because running or uninstalling Setup automatically would alter the developer's machine.

## One-command local report

```powershell
.\scripts\collect-engineering-baseline.ps1 -BuildRuns 3
```

The command creates Markdown, JSON, build logs, and test logs under `.metrics/reports/`. The directory is ignored by Git because reports can contain machine paths and are measurement evidence, not product source.

## Remaining measurements

These still require real samples or deliberately controlled environments:

- download, transcription, and note-generation duration by video length;
- multi-link queue task count, success rate, and retry recovery rate;
- five-sample cold/warm desktop startup medians;
- Setup install time and first dependency preparation time on a clean Windows VM;
- human-reviewed completeness for long-video notes;
- operation-count comparison between Quick Capture and full knowledge-note processing;
- JavaScript split-bundle before/after comparison after code splitting is implemented.

Until those experiments are run, they must remain measurement tasks rather than resume numbers.
