"""Progress helpers for framework agent image builds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROGRESS_JSON = ROOT / "benchmark" / "dataset" / "build_logs" / "image_rebuild_progress.json"


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def ensure_progress_phase(progress_path: Path, phase_name: str) -> None:
    if not progress_path.exists():
        return
    progress = read_json(progress_path)
    statuses = progress.get("status_values") or ["pending", "running", "passed", "failed", "skipped", "blocked"]
    stage_order = progress.setdefault("stage_order", [])
    if phase_name not in stage_order:
        stage_order.append(phase_name)
    for sample in progress.get("samples", []):
        sample.setdefault("phases", {}).setdefault(phase_name, phase_record())
    progress.setdefault("summary", {}).setdefault("phases", {}).setdefault(
        phase_name,
        {status: 0 for status in statuses},
    )
    recompute_progress(progress)
    progress["updated_at"] = now_iso()
    write_json(progress_path, progress)


def recompute_progress(progress: dict[str, Any]) -> None:
    statuses = progress.get("status_values") or ["pending", "running", "passed", "failed", "skipped", "blocked"]
    phase_names = progress.get("stage_order") or []
    progress["summary"] = {
        "overall": {status: 0 for status in statuses},
        "phases": {},
    }
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
    phase_name: str,
    *,
    status: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_seconds: float | None = None,
    log_path: Path | None = None,
    image_id: str | None = None,
    summary: str | None = None,
    error: str | None = None,
) -> None:
    if not progress_path.exists():
        return
    ensure_progress_phase(progress_path, phase_name)
    progress = read_json(progress_path)
    for sample in progress.get("samples", []):
        if sample.get("sample_id") != sample_id:
            continue
        phase = sample.setdefault("phases", {}).setdefault(phase_name, phase_record())
        phase["status"] = status
        if started_at is not None:
            phase["started_at"] = started_at
        if finished_at is not None:
            phase["finished_at"] = finished_at
        if duration_seconds is not None:
            phase["duration_seconds"] = round(duration_seconds, 3)
        if log_path is not None:
            phase["log_path"] = str(log_path)
        if image_id is not None:
            phase["image_id"] = image_id
        if summary is not None:
            phase["summary"] = summary
        phase["error"] = error
        if error is not None:
            sample["last_error"] = error
        break
    recompute_progress(progress)
    progress["updated_at"] = now_iso()
    write_json(progress_path, progress)


def docker_image_id(image: str) -> str | None:
    completed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None
