#!/usr/bin/env python3
"""Local preview server with incremental rebuilds for site pages."""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCH_DIRS = ["base", "jobs", "reports", "templates", "styles", "scripts"]
WATCH_SUFFIXES = {".yaml", ".yml", ".md", ".j2", ".css", ".py", ".tex", ".sty", ".cls"}
EXCLUDE_PARTS = {"output", ".git", "__pycache__", ".venv"}


def run_step(cmd: list[str], label: str) -> bool:
    print(f"[preview] {label}...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"[preview] {label} failed (exit {result.returncode}).")
        return False
    print(f"[preview] {label} done.")
    return True


def build_site() -> bool:
    ok = run_step([sys.executable, str(ROOT / "scripts" / "insights.py")], "Build insights")
    if not ok:
        return False
    return run_step(
        [sys.executable, str(ROOT / "scripts" / "report.py"), "--output", str(ROOT / "output" / "site")],
        "Build report site",
    )


def should_watch(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in WATCH_SUFFIXES:
        return False
    rel_parts = set(path.relative_to(ROOT).parts)
    return not bool(rel_parts.intersection(EXCLUDE_PARTS))


def iter_watch_files() -> list[Path]:
    files: list[Path] = []
    for rel_dir in WATCH_DIRS:
        base = ROOT / rel_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if should_watch(path):
                files.append(path)
    return files


def snapshot_files() -> dict[str, int]:
    snap: dict[str, int] = {}
    for path in iter_watch_files():
        try:
            snap[str(path)] = path.stat().st_mtime_ns
        except FileNotFoundError:
            continue
    return snap


def diff_changed(old: dict[str, int], new: dict[str, int]) -> list[str]:
    keys = set(old) | set(new)
    changed = [k for k in keys if old.get(k) != new.get(k)]
    changed.sort()
    return changed


def watch_loop(stop_event: threading.Event, interval: float) -> None:
    previous = snapshot_files()
    print("[preview] Watch mode enabled. Rebuilding when source files change.")
    while not stop_event.wait(interval):
        current = snapshot_files()
        changed = diff_changed(previous, current)
        if not changed:
            continue

        time.sleep(0.35)
        current = snapshot_files()
        changed = diff_changed(previous, current)
        if not changed:
            previous = current
            continue

        shown = changed[:5]
        suffix = "" if len(changed) <= 5 else f" (+{len(changed) - 5} more)"
        print(f"[preview] Change detected: {', '.join(Path(c).name for c in shown)}{suffix}")

        if build_site():
            print("[preview] Site rebuilt. Refresh browser to view latest changes.")
        else:
            print("[preview] Build failed. Server stays up; fix files and save again.")
        previous = current


def serve(site_dir: Path, host: str, port: int) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"[preview] Serving {site_dir} at http://{host}:{port}")
    print("[preview] Press Ctrl+C to stop.")
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local preview server with auto rebuild.")
    parser.add_argument("--host", default="127.0.0.1", help="Server host, default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Server port, default: 8000")
    parser.add_argument("--interval", type=float, default=1.0, help="Watch interval in seconds")
    parser.add_argument("--no-watch", action="store_true", help="Disable watch mode")
    parser.add_argument("--build-only", action="store_true", help="Build insights + report once, then exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not build_site():
        return 1
    if args.build_only:
        return 0

    stop_event = threading.Event()
    watcher = None
    if not args.no_watch:
        watcher = threading.Thread(target=watch_loop, args=(stop_event, args.interval), daemon=True)
        watcher.start()

    try:
        serve(ROOT / "output" / "site", args.host, args.port)
    except KeyboardInterrupt:
        print("\n[preview] Stopping preview server.")
    finally:
        stop_event.set()
        if watcher:
            watcher.join(timeout=1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
