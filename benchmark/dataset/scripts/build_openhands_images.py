#!/usr/bin/env python3
"""Build OpenHands images from benchmark-agent-base images."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.openhands.scripts.build_openhands_images import (
    DEFAULT_BASE_IMAGE_PREFIX,
    DEFAULT_IMAGE_PREFIX,
    DEFAULT_SAMPLES_DIR,
    OPENHANDS_BENCHMARKS,
    build_one_image,
    check_openhands_benchmarks_ready,
    ensure_openhands_vendor_imports,
    local_image_exists,
    local_image_has_command,
    local_image_workdir,
    load_specs,
    prepare_builder_image,
    retag_local_image,
    remove_existing_output_images,
)
from benchmark.dataset.scripts.framework_image_progress import (
    DEFAULT_PROGRESS_JSON,
    docker_image_id,
    ensure_progress_phase,
    now_iso,
    update_progress,
)

PHASE_NAME = "openhands_image_build"


def reexec_with_openhands_venv() -> None:
    """Run OpenHands image builds with the OpenHands-benchmarks Python env."""
    openhands_python = OPENHANDS_BENCHMARKS / ".venv" / "bin" / "python"
    if not openhands_python.exists():
        return
    current = Path(sys.executable)
    target = openhands_python
    if current == target:
        return
    os.execv(str(target), [str(target), *sys.argv])


@contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build benchmark-openhands-* images from benchmark-agent-base:* images."
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--base-image-prefix", default=DEFAULT_BASE_IMAGE_PREFIX)
    parser.add_argument("--image-prefix", default=DEFAULT_IMAGE_PREFIX)
    parser.add_argument("--filter", default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--remove-existing", action="store_true")
    parser.add_argument("--current-only", action="store_true")
    parser.add_argument("--target-workdir", default="/workspace/repo")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS_JSON)
    parser.add_argument("--log-dir", type=Path, default=None)
    return parser.parse_args()


def prepare_openhands_builder() -> tuple[str, str]:
    check_openhands_benchmarks_ready()
    ensure_openhands_vendor_imports()
    with pushd(OPENHANDS_BENCHMARKS):
        from benchmarks.swebench.build_base_images import (
            _get_sdk_submodule_info,
            builder_image_tag,
            build_builder_image,
        )

        builder_image = prepare_builder_image(builder_image_tag(), build_builder_image)
        _, sdk_git_sha, _ = _get_sdk_submodule_info()
    return builder_image, sdk_git_sha


def mark_existing(spec, progress_json: Path, reason: str) -> None:
    update_progress(
        progress_json,
        spec.sample_id,
        PHASE_NAME,
        status="passed",
        finished_at=now_iso(),
        image_id=docker_image_id(spec.output_image),
        summary=f"{reason} {spec.output_image}",
        error=None,
    )
    print(f"{spec.sample_id}: SKIP {spec.output_image}", flush=True)


def image_derives_from(child: str, parent: str) -> bool:
    import json
    import subprocess

    completed = subprocess.run(
        ["docker", "image", "inspect", child, parent],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return False
    child_meta, parent_meta = json.loads(completed.stdout)
    if child_meta.get("Id") == parent_meta.get("Id"):
        return True
    child_layers = child_meta.get("RootFS", {}).get("Layers", [])
    parent_layers = parent_meta.get("RootFS", {}).get("Layers", [])
    return child_layers[: len(parent_layers)] == parent_layers


def has_current_lineage(spec, target_workdir: str) -> bool:
    return (
        local_image_workdir(spec.output_image) == target_workdir
        and local_image_has_command(spec.output_image, "iptables")
        and image_derives_from(spec.output_image, spec.base_image)
    )


def build_one(spec, builder_image: str, sdk_git_sha: str, args, log_dir: Path) -> bool:
    log_path = log_dir / f"{spec.sample_id}.openhands.log"
    if args.current_only and has_current_lineage(spec, args.target_workdir):
        mark_existing(spec, args.progress_json, "existing current image")
        return True
    if args.skip_existing and image_derives_from(spec.output_image, spec.base_image):
        mark_existing(spec, args.progress_json, "existing image")
        return True

    started_at = now_iso()
    start = time.monotonic()
    update_progress(
        args.progress_json,
        spec.sample_id,
        PHASE_NAME,
        status="running",
        started_at=started_at,
        log_path=log_path,
        summary=f"building {spec.output_image}",
    )
    sample_id, ok, message = build_one_image(
        spec,
        builder_image,
        sdk_git_sha,
        skip_existing=False,
        current_only=False,
        target_workdir=args.target_workdir,
    )
    duration = time.monotonic() - start
    log_path.write_text(message + "\n", encoding="utf-8")
    if ok:
        update_progress(
            args.progress_json,
            sample_id,
            PHASE_NAME,
            status="passed",
            finished_at=now_iso(),
            duration_seconds=duration,
            log_path=log_path,
            image_id=docker_image_id(spec.output_image),
            summary=f"built {spec.output_image}",
            error=None,
        )
        print(message, flush=True)
        return True
    update_progress(
        args.progress_json,
        sample_id,
        PHASE_NAME,
        status="failed",
        finished_at=now_iso(),
        duration_seconds=duration,
        log_path=log_path,
        summary="OpenHands image build failed",
        error=f"OpenHands image build failed; see {log_path}",
    )
    print(message, flush=True)
    return False


def main() -> None:
    reexec_with_openhands_venv()
    args = parse_args()
    if args.remove_existing and (args.skip_existing or args.current_only):
        raise ValueError("--remove-existing cannot be combined with --skip-existing or --current-only")
    specs = load_specs(
        args.samples_dir,
        args.base_image_prefix,
        args.image_prefix,
        args.filter,
    )
    if args.remove_existing:
        remove_existing_output_images(specs)
    if args.jobs != 1:
        raise ValueError("Framework image progress currently requires --jobs 1")
    ensure_progress_phase(args.progress_json, PHASE_NAME)
    log_dir = args.log_dir or (ROOT / "benchmark" / "dataset" / "build_logs" / now_iso().replace(":", ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    builder_image, sdk_git_sha = prepare_openhands_builder()
    failures = 0
    for spec in specs:
        if not build_one(spec, builder_image, sdk_git_sha, args, log_dir):
            failures += 1
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
