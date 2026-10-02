#!/usr/bin/env python3
"""Check evaluator images can checkout base and patched commits offline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS_JSON = ROOT / "benchmark" / "dataset" / "build_logs" / "image_rebuild_progress.json"

CHECK_SCRIPT = """\
set -euo pipefail
cd /workspace/repo
GIT_NO_LAZY_FETCH=1 git cat-file -e "${BASE_COMMIT}^{commit}"
GIT_NO_LAZY_FETCH=1 git cat-file -e "${PATCHED_COMMIT}^{commit}"
GIT_NO_LAZY_FETCH=1 git checkout --force "${BASE_COMMIT}"
GIT_NO_LAZY_FETCH=1 git reset --hard "${BASE_COMMIT}"
git clean -fdx
GIT_NO_LAZY_FETCH=1 git checkout --force "${PATCHED_COMMIT}"
GIT_NO_LAZY_FETCH=1 git reset --hard "${PATCHED_COMMIT}"
git clean -fdx
"""


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluation_image(sample_id: str) -> str:
    return f"benchmark-evaluation:{sample_id}"


def iter_specs(samples_dir: Path, sample_filter: str | None, limit: int | None) -> list[tuple[str, Path, str]]:
    index = read_json(samples_dir / "index.json")
    specs = []
    for item in index.get("samples", []):
        sample_id = item["sample_id"]
        if sample_filter and sample_filter not in sample_id and sample_filter not in item.get("sample_path", ""):
            continue
        image = item.get("docker_image") or evaluation_image(sample_id)
        if not image.startswith("benchmark-evaluation:"):
            image = evaluation_image(sample_id)
        specs.append((sample_id, samples_dir / item["sample_path"] / "sample.json", image))
    if limit is not None:
        specs = specs[:limit]
    return specs


def phase_record() -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "duration_seconds": None,
        "log_path": None,
        "image_id": None,
        "summary": None,
        "error": None,
    }


def recompute_progress(progress: dict[str, Any]) -> None:
    statuses = progress.get("status_values") or ["pending", "running", "passed", "failed", "skipped", "blocked"]
    phase_names = progress.get("stage_order") or []
    progress["summary"] = {"overall": {status: 0 for status in statuses}, "phases": {}}
    for sample in progress.get("samples", []):
        overall = sample.get("overall_status") or "pending"
        progress["summary"]["overall"][overall] = progress["summary"]["overall"].get(overall, 0) + 1
    for phase_name in phase_names:
        counts = {status: 0 for status in statuses}
        for sample in progress.get("samples", []):
            status = (sample.get("phases", {}).get(phase_name) or {}).get("status") or "pending"
            counts[status] = counts.get(status, 0) + 1
        progress["summary"]["phases"][phase_name] = counts


def update_progress(
    progress_path: Path,
    sample_id: str,
    *,
    status: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_seconds: float | None = None,
    log_path: Path | None = None,
    summary: str | None = None,
    error: str | None = None,
) -> None:
    if not progress_path.exists():
        return
    progress = read_json(progress_path)
    for sample in progress.get("samples", []):
        if sample.get("sample_id") != sample_id:
            continue
        phase = sample.setdefault("phases", {}).setdefault("evaluator_offline_check", phase_record())
        phase["status"] = status
        if started_at is not None:
            phase["started_at"] = started_at
        if finished_at is not None:
            phase["finished_at"] = finished_at
        if duration_seconds is not None:
            phase["duration_seconds"] = round(duration_seconds, 3)
        if log_path is not None:
            phase["log_path"] = str(log_path)
        if summary is not None:
            phase["summary"] = summary
        if error is not None:
            phase["error"] = error
            sample["last_error"] = error
        break
    progress["updated_at"] = now_iso()
    recompute_progress(progress)
    progress_path.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_one(sample_id: str, sample_path: Path, image: str, log_dir: Path, progress_path: Path) -> bool:
    sample = read_json(sample_path)
    instance = sample["instance"]
    log_path = log_dir / f"{sample_id}.offline_check.log"
    started = now_iso()
    update_progress(progress_path, sample_id, status="running", started_at=started, log_path=log_path)
    start = time.monotonic()
    command = [
        "docker",
        "run",
        "--platform",
        "linux/amd64",
        "--rm",
        "--network",
        "none",
        "--entrypoint",
        "bash",
        "-e",
        f"BASE_COMMIT={instance['base_commit']}",
        "-e",
        f"PATCHED_COMMIT={instance['patch']}",
        image,
        "-lc",
        CHECK_SCRIPT,
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(" ".join(command) + "\n\n")
        completed = subprocess.run(command, stdout=log_file, stderr=subprocess.STDOUT, text=True, check=False)
    duration = time.monotonic() - start
    if completed.returncode == 0:
        update_progress(
            progress_path,
            sample_id,
            status="passed",
            finished_at=now_iso(),
            duration_seconds=duration,
            log_path=log_path,
            summary=f"{image} can checkout base/patched offline",
            error=None,
        )
        print(f"{sample_id}: OK {image}", flush=True)
        return True
    update_progress(
        progress_path,
        sample_id,
        status="failed",
        finished_at=now_iso(),
        duration_seconds=duration,
        log_path=log_path,
        summary=f"docker run exited {completed.returncode}",
        error=f"evaluator offline check failed; see {log_path}",
    )
    print(f"{sample_id}: FAIL see {log_path}", flush=True)
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check evaluator images for offline checkout support.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS_JSON)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--filter", default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    specs = iter_specs(args.samples_dir, args.filter, args.limit)
    if not specs:
        raise SystemExit("No samples matched.")
    log_dir = args.log_dir or (ROOT / "benchmark" / "dataset" / "build_logs" / now_iso().replace(":", ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for sample_id, sample_path, image in specs:
        if not check_one(sample_id, sample_path, image, log_dir, args.progress_json):
            failures += 1
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
