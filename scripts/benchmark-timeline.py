from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return round(ordered[index], 2)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"samples": 0, "median": None, "min": None, "max": None}
    return {
        "samples": len(values),
        "median": round(statistics.median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


async def select_session(page: Page, title: str, expected_blocks: int) -> None:
    await page.goto(page.url or "about:blank")
    session = page.get_by_text(title, exact=True)
    await session.last.click()
    await page.wait_for_function(
        "expected => document.querySelectorAll('[id^=\"ev-\"]').length === 0 || "
        "document.body.innerText.includes(String(expected))",
        arg=expected_blocks,
        timeout=30_000,
    )


async def install_observers(page: Page) -> None:
    await page.evaluate(
        """
        () => {
          window.__benchmarkLongTasks = [];
          if (window.PerformanceObserver && PerformanceObserver.supportedEntryTypes.includes('longtask')) {
            window.__benchmarkObserver = new PerformanceObserver((list) => {
              window.__benchmarkLongTasks.push(...list.getEntries().map((entry) => ({
                start: entry.startTime,
                duration: entry.duration,
              })));
            });
            window.__benchmarkObserver.observe({ entryTypes: ['longtask'] });
          }
        }
        """
    )


async def run_once(page: Page, url: str, title: str, expected_blocks: int) -> dict[str, Any]:
    await page.goto(url, wait_until="networkidle", timeout=60_000)
    session = page.get_by_text(title, exact=True)
    await session.last.wait_for(state="visible", timeout=30_000)
    await session.last.click()
    await page.wait_for_timeout(500)
    await install_observers(page)

    timeline_button = page.get_by_role("button", name="时间线").last
    await timeline_button.wait_for(state="visible", timeout=15_000)
    started = time.perf_counter()
    await timeline_button.click()
    await page.wait_for_function(
        "expected => document.querySelectorAll('[id^=\"ev-\"]').length >= expected",
        arg=expected_blocks,
        timeout=60_000,
    )
    open_result = await page.evaluate(
        """
        async () => {
          const rows = document.querySelectorAll('[id^="ev-"]');
          const last = rows[rows.length - 1];
          if (last) last.getBoundingClientRect();
          await new Promise(requestAnimationFrame);
          await new Promise(requestAnimationFrame);
          return { rows: rows.length };
        }
        """
    )
    open_ms = (time.perf_counter() - started) * 1000

    scroll_result = await page.evaluate(
        """
        async () => {
          const first = document.querySelector('[id^="ev-"]');
          if (!first) throw new Error('Timeline row not found');
          let scroller = first.parentElement;
          while (scroller && scroller !== document.body) {
            const style = getComputedStyle(scroller);
            if (/auto|scroll/.test(style.overflowY) && scroller.scrollHeight > scroller.clientHeight) break;
            scroller = scroller.parentElement;
          }
          if (!scroller || scroller === document.body) throw new Error('Timeline scroller not found');

          const frameDeltas = [];
          const maxScroll = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
          let previous = performance.now();
          for (let step = 0; step <= 120; step += 1) {
            await new Promise(requestAnimationFrame);
            const now = performance.now();
            frameDeltas.push(now - previous);
            previous = now;
            scroller.scrollTop = maxScroll * (step / 120);
          }
          await new Promise(requestAnimationFrame);
          return {
            frame_deltas_ms: frameDeltas,
            scroll_height: scroller.scrollHeight,
            viewport_height: scroller.clientHeight,
            long_tasks: window.__benchmarkLongTasks || [],
          };
        }
        """
    )
    deltas = [float(value) for value in scroll_result["frame_deltas_ms"]]
    long_tasks = scroll_result["long_tasks"]
    return {
        "rows": open_result["rows"],
        "open_ms": round(open_ms, 2),
        "scroll": {
            "frame_samples": len(deltas),
            "frame_p50_ms": percentile(deltas, 0.50),
            "frame_p95_ms": percentile(deltas, 0.95),
            "frames_over_25ms": sum(value > 25 for value in deltas),
            "frames_over_50ms": sum(value > 50 for value in deltas),
            "long_task_count": len(long_tasks),
            "long_task_total_ms": round(sum(item["duration"] for item in long_tasks), 2),
            "scroll_height": scroll_result["scroll_height"],
            "viewport_height": scroll_result["viewport_height"],
        },
    }


async def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    targets = []
    for target in args.target:
        label, url = target.split("=", 1)
        targets.append((label, url))

    report: dict[str, Any] = {
        "schema_version": 1,
        "measured_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "session_title": args.session_title,
        "expected_blocks": args.expected_blocks,
        "runs_per_target": args.runs,
        "targets": [],
    }
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            for label, url in targets:
                context = await browser.new_context(viewport={"width": 1440, "height": 900})
                await context.add_init_script(
                    "sessionStorage.setItem('one_tap_note_client_id', 'timeline-benchmark')"
                )
                page = await context.new_page()
                runs = []
                try:
                    for index in range(args.runs):
                        print(f"{label}: run {index + 1}/{args.runs}", flush=True)
                        runs.append(await run_once(page, url, args.session_title, args.expected_blocks))
                finally:
                    await context.close()
                open_values = [run["open_ms"] for run in runs]
                p95_values = [run["scroll"]["frame_p95_ms"] for run in runs]
                long_task_values = [run["scroll"]["long_task_total_ms"] for run in runs]
                report["targets"].append(
                    {
                        "label": label,
                        "url": url,
                        "runs": runs,
                        "summary": {
                            "open_ms": summarize(open_values),
                            "scroll_frame_p95_ms": summarize(p95_values),
                            "scroll_long_task_total_ms": summarize(long_task_values),
                        },
                    }
                )
        finally:
            await browser.close()
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# One Tap Note timeline benchmark",
        "",
        f"- Measured at: {report['measured_at']}",
        f"- Session: {report['session_title']}",
        f"- Evidence blocks: {report['expected_blocks']}",
        f"- Runs per target: {report['runs_per_target']}",
        "",
        "| Target | Open median | Scroll frame p95 median | Long-task time median |",
        "| --- | ---: | ---: | ---: |",
    ]
    for target in report["targets"]:
        summary = target["summary"]
        lines.append(
            f"| {target['label']} | {summary['open_ms']['median']} ms | "
            f"{summary['scroll_frame_p95_ms']['median']} ms | "
            f"{summary['scroll_long_task_total_ms']['median']} ms |"
        )
    lines.extend(
        [
            "",
            "Method: same machine, Chromium viewport 1440x900, same stored session, repeated full timeline open and top-to-bottom animation-frame scrolling.",
            "Raw per-run values are available in the adjacent JSON report.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark large One Tap Note timelines.")
    parser.add_argument("--target", action="append", required=True, help="label=http://host:port")
    parser.add_argument("--session-title", required=True)
    parser.add_argument("--expected-blocks", type=int, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(benchmark(args))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(output.with_suffix(".json"))
    print(output.with_suffix(".md"))


if __name__ == "__main__":
    main()
