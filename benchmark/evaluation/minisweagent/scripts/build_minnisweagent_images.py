#!/usr/bin/env python3
"""Build mini-SWE-agent runtime images from benchmark-agent-base images."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.minisweagent.scripts.export_sweagent_instances import DEFAULT_SAMPLES_DIR
from benchmark.evaluation.minisweagent.scripts.adapter_images import (
    DEFAULT_RUNTIME_IMAGE,
    DEFAULT_RUNTIME_VERSION,
    DEFAULT_WHEEL_EXTRA_INDEX_URL,
    DEFAULT_WHEEL_INDEX_URL,
    DEFAULT_WHEELS_DIR,
    RuntimeConfig,
    build_images,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mini-SWE-agent runtime images.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--image-prefix", default="benchmark-minisweagent-")
    parser.add_argument(
        "--runtime-image",
        default=DEFAULT_RUNTIME_IMAGE,
        help="Python runtime image used only for the isolated agent runtime layer.",
    )
    parser.add_argument(
        "--swe-rex-version",
        default=DEFAULT_RUNTIME_VERSION,
        help="swe-rex version installed into the isolated runtime layer.",
    )
    parser.add_argument(
        "--wheels-dir",
        type=Path,
        default=DEFAULT_WHEELS_DIR,
        help="Cache directory for linux wheels used by the isolated runtime layer.",
    )
    parser.add_argument(
        "--wheel-index-url",
        default=DEFAULT_WHEEL_INDEX_URL,
        help="Primary package index used to prepare runtime wheels.",
    )
    parser.add_argument(
        "--wheel-extra-index-url",
        default=DEFAULT_WHEEL_EXTRA_INDEX_URL,
        help="Optional fallback package index used when the primary mirror is incomplete.",
    )
    parser.add_argument(
        "--refresh-wheels",
        action="store_true",
        help="Re-download the isolated runtime wheels before building adapter images.",
    )
    parser.add_argument("--filter", default=None, help="Only build samples whose id contains this string.")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Skip adapter images that already exist locally.",
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Skip adapter images that already exist locally with the target working directory.",
    )
    parser.add_argument(
        "--target-workdir",
        default="/workspace/repo",
        help="Working directory expected for images skipped by --current-only.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


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
    built = build_images(
        args.samples_dir,
        args.image_prefix,
        args.filter,
        runtime,
        args.dry_run,
        args.missing_only,
        args.current_only,
        args.target_workdir,
    )
    action = "Prepared" if args.dry_run else "Built"
    print(f"{action} {len(built)} mini-SWE-agent runtime images.")


if __name__ == "__main__":
    main()
