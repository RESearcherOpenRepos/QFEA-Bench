#!/usr/bin/env python3
"""Build mini-SWE-agent images from benchmark-agent-base images."""

from __future__ import annotations

import argparse
import shutil
import sys
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.minisweagent.scripts.adapter_images import (
    DEFAULT_RUNTIME_IMAGE,
    DEFAULT_RUNTIME_VERSION,
    DEFAULT_WHEEL_EXTRA_INDEX_URL,
    DEFAULT_WHEEL_INDEX_URL,
    DEFAULT_WHEELS_DIR,
    RuntimeConfig,
    current_adapter_images,
    docker_build_command,
    existing_adapter_images,
    load_build_specs,
    run_preflight,
    DOCKERFILE_TEXT,
)
from benchmark.evaluation.minisweagent.scripts.export_sweagent_instances import DEFAULT_SAMPLES_DIR
from benchmark.dataset.scripts.framework_image_progress import (
    DEFAULT_PROGRESS_JSON,
    docker_image_id,
    ensure_progress_phase,
    now_iso,
    update_progress,
)

PHASE_NAME = "minisweagent_image_build"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build benchmark-minisweagent-* images from benchmark-agent-base:* images."
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--image-prefix", default="benchmark-minisweagent-")
    parser.add_argument("--runtime-image", default=DEFAULT_RUNTIME_IMAGE)
    parser.add_argument("--swe-rex-version", default=DEFAULT_RUNTIME_VERSION)
    parser.add_argument("--wheels-dir", type=Path, default=DEFAULT_WHEELS_DIR)
    parser.add_argument("--wheel-index-url", default=DEFAULT_WHEEL_INDEX_URL)
    parser.add_argument("--wheel-extra-index-url", default=DEFAULT_WHEEL_EXTRA_INDEX_URL)
    parser.add_argument("--refresh-wheels", action="store_true")
    parser.add_argument("--filter", default=None)
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument("--current-only", action="store_true")
    parser.add_argument("--target-workdir", default="/workspace/repo")
    parser.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS_JSON)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def build_one(spec, runtime: RuntimeConfig, log_dir: Path, progress_json: Path, dry_run: bool) -> bool:
    log_path = log_dir / f"{spec.sample_id}.minisweagent.log"
    with tempfile.TemporaryDirectory(prefix="quanbench-minisweagent-") as tmp:
        context_dir = Path(tmp)
        (context_dir / "Dockerfile").write_text(DOCKERFILE_TEXT, encoding="utf-8")
        shutil.copytree(runtime.wheels_dir, context_dir / "wheels")
        command = docker_build_command(spec, runtime, context_dir)
        if dry_run:
            print(" ".join(command))
            return True
        started_at = now_iso()
        start = time.monotonic()
        update_progress(
            progress_json,
            spec.sample_id,
            PHASE_NAME,
            status="running",
            started_at=started_at,
            log_path=log_path,
            summary=f"building {spec.adapter_image}",
        )
        with log_path.open("w", encoding="utf-8") as log_file:
            log_file.write(" ".join(command) + "\n\n")
            completed = subprocess.run(command, stdout=log_file, stderr=subprocess.STDOUT, text=True, check=False)
    duration = time.monotonic() - start
    if completed.returncode == 0:
        update_progress(
            progress_json,
            spec.sample_id,
            PHASE_NAME,
            status="passed",
            finished_at=now_iso(),
            duration_seconds=duration,
            log_path=log_path,
            image_id=docker_image_id(spec.adapter_image),
            summary=f"built {spec.adapter_image}",
            error=None,
        )
        print(f"{spec.sample_id}: OK {spec.adapter_image}", flush=True)
        return True
    update_progress(
        progress_json,
        spec.sample_id,
        PHASE_NAME,
        status="failed",
        finished_at=now_iso(),
        duration_seconds=duration,
        log_path=log_path,
        summary=f"docker build exited {completed.returncode}",
        error=f"mini-SWE-agent image build failed; see {log_path}",
    )
    print(f"{spec.sample_id}: FAIL see {log_path}", flush=True)
    return False


def mark_existing(spec, progress_json: Path, reason: str, dry_run: bool) -> None:
    if not dry_run:
        update_progress(
            progress_json,
            spec.sample_id,
            PHASE_NAME,
            status="passed",
            finished_at=now_iso(),
            image_id=docker_image_id(spec.adapter_image),
            summary=f"{reason} {spec.adapter_image}",
            error=None,
        )
    print(f"{spec.sample_id}: SKIP {spec.adapter_image}", flush=True)


def main() -> None:
    args = parse_args()
    runtime = RuntimeConfig(
        python_runtime_image=args.runtime_image,
        swe_rex_version=args.swe_rex_version,
        wheels_dir=args.wheels_dir,
        wheel_index_url=args.wheel_index_url,
        wheel_extra_index_url=args.wheel_extra_index_url or None,
        refresh_wheels=args.refresh_wheels,
    )
    if args.missing_only and args.current_only:
        raise ValueError("--missing-only and --current-only are mutually exclusive")
    specs = load_build_specs(args.samples_dir, args.image_prefix, args.filter)
    run_preflight(args.samples_dir, runtime, specs, dry_run=args.dry_run)
    if not args.dry_run:
        ensure_progress_phase(args.progress_json, PHASE_NAME)
    log_dir = args.log_dir or (ROOT / "benchmark" / "dataset" / "build_logs" / now_iso().replace(":", ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    current = (
        current_adapter_images(args.image_prefix, args.target_workdir)
        if args.current_only and not args.dry_run
        else set()
    )
    existing = (
        existing_adapter_images(args.image_prefix)
        if args.missing_only and not args.dry_run
        else set()
    )
    count = 0
    failures = 0
    for spec in specs:
        if spec.adapter_image in current:
            mark_existing(spec, args.progress_json, "existing current image", args.dry_run)
            continue
        if spec.adapter_image in existing:
            mark_existing(spec, args.progress_json, "existing image", args.dry_run)
            continue
        if build_one(spec, runtime, log_dir, args.progress_json, args.dry_run):
            count += 1
        else:
            failures += 1
    action = "Prepared" if args.dry_run else "Built"
    print(f"{action} {count} mini-SWE-agent images.")
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
