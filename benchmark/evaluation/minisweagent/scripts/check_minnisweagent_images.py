#!/usr/bin/env python3
"""Check mini-SWE-agent adapter images for primary-test leakage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.minisweagent.scripts.export_sweagent_instances import DEFAULT_SAMPLES_DIR
from benchmark.evaluation.minisweagent.scripts.check_adapter_images import check_images


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check mini-SWE-agent adapter images for leakage.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--image-prefix", default="benchmark-sweagent-")
    parser.add_argument("--filter", default=None, help="Only check samples whose id contains this string.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    failures = check_images(args.samples_dir, args.image_prefix, args.filter)
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
