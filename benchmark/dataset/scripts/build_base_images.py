#!/usr/bin/env python3
"""Build benchmark-base images from sample Dockerfile.repo-base files."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS = ROOT / "benchmark" / "dataset" / "build_logs" / "base_image_build_progress.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build benchmark-base:<sample_id> images.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--filter", default=None, help="Substring filter over sample_id.")
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument("--platform", default="linux/amd64")
    parser.add_argument("--progress-jsonl", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_specs(samples_dir: Path, filter_text: str | None) -> list[dict[str, Path | str]]:
    specs = []
    for sample_json in samples_dir.glob("*/*/sample.json"):
        sample_dir = sample_json.parent
        dockerfile = sample_dir / "Dockerfile.repo-base"
        if not dockerfile.exists():
            continue
        try:
            data = json.loads(sample_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sample_id = str((data.get("instance") or {}).get("instance_id") or sample_dir.name)
        if filter_text and filter_text not in sample_id:
            continue
        specs.append({"sample_id": sample_id, "sample_dir": sample_dir, "dockerfile": dockerfile})
    return sorted(specs, key=lambda spec: str(spec["sample_id"]))


def image_exists(image: str) -> bool:
    return subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def event(path: Path, **payload: object) -> None:
    payload.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    specs = load_specs(args.samples_dir, args.filter)
    total = len(specs)
    print(f"planned {total} benchmark-base builds", flush=True)
    event(args.progress_jsonl, event="start", total=total, platform=args.platform)
    failures = 0
    for index, spec in enumerate(specs, 1):
        sample_id = str(spec["sample_id"])
        image = f"benchmark-base:{sample_id}"
        event(args.progress_jsonl, event="begin", index=index, total=total, sample_id=sample_id, image=image)
        if args.missing_only and image_exists(image):
            print(f"[{index}/{total}] skip existing {image}", flush=True)
            event(args.progress_jsonl, event="skip_existing", index=index, total=total, sample_id=sample_id, image=image)
            continue
        command = [
            "docker",
            "build",
            "--platform",
            args.platform,
            "-f",
            str(spec["dockerfile"]),
            "-t",
            image,
            str(spec["sample_dir"]),
        ]
        print(" ".join(command), flush=True)
        if not args.dry_run and subprocess.run(command, check=False).returncode != 0:
            failures += 1
            print(f"[{index}/{total}] FAILED {image}", flush=True)
            event(args.progress_jsonl, event="failed", index=index, total=total, sample_id=sample_id, image=image)
            continue
        print(f"[{index}/{total}] built {image}", flush=True)
        event(args.progress_jsonl, event="built", index=index, total=total, sample_id=sample_id, image=image)
    event(args.progress_jsonl, event="done", failures=failures)
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
