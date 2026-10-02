#!/usr/bin/env python3
"""Check local QuanBench agent framework images."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS = ROOT / "benchmark" / "dataset" / "build_logs" / "agent_image_check_progress.jsonl"
SUPPORTED_FRAMEWORKS = ("minisweagent", "openhands", "traeagent")
DEFAULT_FRAMEWORKS = ("minisweagent", "openhands")
IMAGE_TEMPLATES = {
    "minisweagent": "benchmark-minisweagent-{sample_id}:latest",
    "openhands": "benchmark-openhands-{sample_id}:latest",
    "traeagent": "benchmark-traeagent-{sample_id}:latest",
}
DEFAULT_SMOKE_COMMAND = "test -d /workspace/repo && test -x /bin/sh"


@dataclass(frozen=True)
class CheckTarget:
    index: int
    total: int
    framework: str
    sample_id: str
    image: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local QuanBench agent images.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument(
        "--framework",
        action="append",
        choices=SUPPORTED_FRAMEWORKS,
        help="Framework image kind to check. Can be repeated. Defaults to minisweagent and openhands.",
    )
    parser.add_argument("--filter", default=None, help="Substring filter over sample_id.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--inspect-only", action="store_true", help="Only run docker image inspect.")
    parser.add_argument("--smoke-timeout", type=int, default=30)
    parser.add_argument(
        "--smoke-command",
        default=DEFAULT_SMOKE_COMMAND,
        help="Shell command executed inside each image unless --inspect-only is set.",
    )
    parser.add_argument("--progress-jsonl", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sample_ids(samples_dir: Path, filter_text: str | None) -> list[str]:
    ids: set[str] = set()
    for sample_json in samples_dir.glob("*/*/sample.json"):
        try:
            data = json.loads(sample_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sample_id = str((data.get("instance") or {}).get("instance_id") or sample_json.parent.name)
        if filter_text and filter_text not in sample_id:
            continue
        ids.add(sample_id)
    return sorted(ids)


def image_name(framework: str, sample_id: str) -> str:
    return IMAGE_TEMPLATES[framework].format(sample_id=sample_id)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_event(path: Path, **payload: object) -> None:
    payload.setdefault("ts", now_iso())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_command(command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def inspect_image(image: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    completed = run_command(["docker", "image", "inspect", image])
    if completed.returncode != 0:
        return False, None, (completed.stderr or completed.stdout).strip()
    try:
        payload = json.loads(completed.stdout)[0]
    except (json.JSONDecodeError, IndexError, TypeError) as exc:
        return False, None, f"failed to parse docker inspect output: {exc}"
    return True, payload, None


def smoke_image(image: str, command: str, timeout: int) -> tuple[bool, str | None]:
    completed = run_command(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "/bin/sh",
            image,
            "-lc",
            command,
        ],
        timeout=timeout,
    )
    if completed.returncode == 0:
        return True, None
    output = ((completed.stderr or "") + (completed.stdout or "")).strip()
    return False, output or f"docker run exited {completed.returncode}"


def check_one(target: CheckTarget, args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "framework": target.framework,
        "sample_id": target.sample_id,
        "image": target.image,
        "index": target.index,
        "total": target.total,
    }
    if args.dry_run:
        result.update(status="dry_run")
        return result

    ok, inspect_payload, error = inspect_image(target.image)
    if not ok:
        result.update(status="missing", error=error)
        return result

    result.update(
        image_id=inspect_payload.get("Id"),
        size_bytes=inspect_payload.get("Size"),
        os=inspect_payload.get("Os"),
        architecture=inspect_payload.get("Architecture"),
    )
    if args.inspect_only:
        result.update(status="ok")
        return result

    try:
        smoke_ok, smoke_error = smoke_image(target.image, args.smoke_command, args.smoke_timeout)
    except subprocess.TimeoutExpired:
        smoke_ok = False
        smoke_error = f"smoke test timed out after {args.smoke_timeout}s"
    if not smoke_ok:
        result.update(status="smoke_failed", error=smoke_error)
        return result

    result.update(status="ok")
    return result


def main() -> None:
    args = parse_args()
    frameworks = args.framework or list(DEFAULT_FRAMEWORKS)
    ids = sample_ids(args.samples_dir, args.filter)
    targets = [
        CheckTarget(
            index=index,
            total=len(ids) * len(frameworks),
            framework=framework,
            sample_id=sample_id,
            image=image_name(framework, sample_id),
        )
        for index, (sample_id, framework) in enumerate(
            ((sample_id, framework) for sample_id in ids for framework in frameworks),
            start=1,
        )
    ]

    print(f"planned {len(targets)} image checks", flush=True)
    write_event(
        args.progress_jsonl,
        event="start",
        total=len(targets),
        frameworks=frameworks,
        inspect_only=args.inspect_only,
        smoke_command=None if args.inspect_only else args.smoke_command,
    )

    results: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_to_target = {executor.submit(check_one, target, args): target for target in targets}
        for future in concurrent.futures.as_completed(future_to_target):
            target = future_to_target[future]
            try:
                result = future.result()
            except Exception as exc:  # pragma: no cover - defensive CLI guard
                result = {
                    "framework": target.framework,
                    "sample_id": target.sample_id,
                    "image": target.image,
                    "index": target.index,
                    "total": target.total,
                    "status": "error",
                    "error": str(exc),
                }
            results.append(result)
            status = str(result["status"])
            counts[status] = counts.get(status, 0) + 1
            write_event(args.progress_jsonl, event=status, **result)
            if status == "ok":
                print(f"[{target.index}/{target.total}] ok {target.image}", flush=True)
            else:
                print(
                    f"[{target.index}/{target.total}] {status} {target.image}: "
                    f"{result.get('error', '')}",
                    flush=True,
                )

    results.sort(key=lambda row: (str(row["sample_id"]), str(row["framework"])))
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    write_event(args.progress_jsonl, event="done", counts=counts)
    summary = " ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    print(f"summary: {summary}", flush=True)
    if any(status not in {"ok", "dry_run"} for status in counts):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
