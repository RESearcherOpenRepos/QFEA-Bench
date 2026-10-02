#!/usr/bin/env python3
"""Build Trae-agent images from benchmark-agent-base images."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from benchmark.dataset.scripts.framework_image_progress import (
    DEFAULT_PROGRESS_JSON,
    docker_image_id,
    ensure_progress_phase,
    now_iso,
    read_json,
    update_progress,
)

PHASE_NAME = "traeagent_image_build"
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_SOURCE_IMAGE_PREFIX = "benchmark-agent-base:"
DEFAULT_IMAGE_PREFIX = "benchmark-traeagent-"


def iter_sample_files(samples_dir: Path, sample_filter: str | None) -> list[Path]:
    index_path = samples_dir / "index.json"
    if index_path.exists():
        paths = [
            samples_dir / item["sample_path"] / "sample.json"
            for item in read_json(index_path).get("samples", [])
        ]
    else:
        paths = sorted(samples_dir.rglob("sample.json"))
    if sample_filter:
        paths = [path for path in paths if sample_filter in str(path.parent.relative_to(samples_dir))]
    return paths


def image_name(sample_id: str, prefix: str) -> str:
    if prefix.endswith(":"):
        return f"{prefix}{sample_id}"
    return f"{prefix}{sample_id}:latest"


def local_image_exists(image: str) -> bool:
    return docker_image_id(image) is not None


def retag_image(source: str, target: str) -> None:
    subprocess.run(["docker", "tag", source, target], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build benchmark-traeagent-* images from benchmark-agent-base:* images."
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--source-image-prefix", default=DEFAULT_SOURCE_IMAGE_PREFIX)
    parser.add_argument("--image-prefix", default=DEFAULT_IMAGE_PREFIX)
    parser.add_argument("--filter", default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS_JSON)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def mark_existing(sample_id: str, target: str, progress_json: Path) -> None:
    update_progress(
        progress_json,
        sample_id,
        PHASE_NAME,
        status="passed",
        finished_at=now_iso(),
        image_id=docker_image_id(target),
        summary=f"existing image {target}",
        error=None,
    )
    print(f"{sample_id}: SKIP {target}", flush=True)


def same_image(source: str, target: str) -> bool:
    source_id = docker_image_id(source)
    target_id = docker_image_id(target)
    return source_id is not None and source_id == target_id


def tag_one(sample_id: str, source: str, target: str, args, log_dir: Path) -> bool:
    log_path = log_dir / f"{sample_id}.traeagent.log"
    if args.skip_existing and same_image(source, target):
        mark_existing(sample_id, target, args.progress_json)
        return True
    if not local_image_exists(source):
        message = f"{sample_id}: missing source image {source}; build benchmark-agent-base images first"
        update_progress(
            args.progress_json,
            sample_id,
            PHASE_NAME,
            status="failed",
            finished_at=now_iso(),
            log_path=log_path,
            summary="missing source image",
            error=message,
        )
        log_path.write_text(message + "\n", encoding="utf-8")
        print(message, flush=True)
        return False
    if args.dry_run:
        print(f"{sample_id}: WOULD BUILD {source} -> {target}", flush=True)
        return True

    update_progress(
        args.progress_json,
        sample_id,
        PHASE_NAME,
        status="running",
        started_at=now_iso(),
        log_path=log_path,
        summary=f"building {source} -> {target}",
    )
    start = time.monotonic()
    try:
        retag_image(source, target)
    except Exception as exc:
        duration = time.monotonic() - start
        message = str(exc)
        log_path.write_text(message + "\n", encoding="utf-8")
        update_progress(
            args.progress_json,
            sample_id,
            PHASE_NAME,
            status="failed",
            finished_at=now_iso(),
            duration_seconds=duration,
            log_path=log_path,
        summary="docker build failed",
            error=message,
        )
        print(f"{sample_id}: FAIL see {log_path}", flush=True)
        return False
    duration = time.monotonic() - start
    log_path.write_text(f"docker build {source} -> {target}\n", encoding="utf-8")
    update_progress(
        args.progress_json,
        sample_id,
        PHASE_NAME,
        status="passed",
        finished_at=now_iso(),
        duration_seconds=duration,
        log_path=log_path,
        image_id=docker_image_id(target),
        summary=f"built {target}",
        error=None,
    )
    print(f"{sample_id}: OK {target}", flush=True)
    return True


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        ensure_progress_phase(args.progress_json, PHASE_NAME)
    log_dir = args.log_dir or (ROOT / "benchmark" / "dataset" / "build_logs" / now_iso().replace(":", ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    tagged = []
    failures = 0
    for sample_path in iter_sample_files(args.samples_dir, args.filter):
        sample_id = read_json(sample_path)["instance"]["instance_id"]
        source = image_name(sample_id, args.source_image_prefix)
        target = image_name(sample_id, args.image_prefix)
        if tag_one(sample_id, source, target, args, log_dir):
            tagged.append(target)
        else:
            failures += 1
    action = "Prepared" if args.dry_run else "Built"
    print(f"{action} {len(tagged)} Trae-agent images.")
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
