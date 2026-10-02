#!/usr/bin/env python3
"""Check mini-SWE-agent adapter images for primary-test leakage."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.minisweagent.scripts.export_sweagent_instances import (
    DEFAULT_SAMPLES_DIR,
    adapter_image_name,
)


CHECK_SCRIPT = """\
set -euo pipefail
cd /workspace/repo
test "$(git rev-parse HEAD)" = "${BASE_COMMIT}"
test "$(git rev-list --all --count)" = "1"
test -f .git/shallow
test "$(cat .git/shallow)" = "${BASE_COMMIT}"
test -z "$(git reflog)"
test ! -e /benchmark
test -z "${FAIL_PASS_TEST_PATHS:-}"
test -z "${PASS_PASS_TEST_PATHS:-}"
test -z "${TEST_PATHS:-}"
test -z "${TEST_PATH:-}"
test -z "${REGRESSION_TEST_PATHS:-}"
test -z "${REGRESSION_TEST_PATH:-}"
if [ -n "${PATCHED_COMMIT}" ]; then
  ! git cat-file -e "${PATCHED_COMMIT}^{commit}"
fi
"""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_sample_files(samples_dir: Path, sample_filter: str | None) -> list[Path]:
    paths = sorted(samples_dir.rglob("sample.json"))
    if sample_filter:
        paths = [path for path in paths if sample_filter in str(path.parent.relative_to(samples_dir))]
    return paths


def check_image(sample_path: Path, image_prefix: str) -> tuple[str, bool, str]:
    sample = read_json(sample_path)
    instance = sample["instance"]
    sample_id = instance["instance_id"]
    image = adapter_image_name(sample_id, image_prefix)
    command = [
        "docker",
        "run",
        "--platform",
        "linux/amd64",
        "--rm",
        "--entrypoint",
        "bash",
        "-e",
        f"BASE_COMMIT={instance['base_commit']}",
        "-e",
        f"PATCHED_COMMIT={instance.get('patch', '')}",
        image,
        "-lc",
        CHECK_SCRIPT,
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = completed.stdout + completed.stderr
    return sample_id, completed.returncode == 0, output


def check_images(samples_dir: Path, image_prefix: str, sample_filter: str | None) -> int:
    failures = 0
    for sample_path in iter_sample_files(samples_dir, sample_filter):
        sample_id, ok, output = check_image(sample_path, image_prefix)
        print(f"{sample_id}: {'OK' if ok else 'FAIL'}")
        if not ok:
            failures += 1
            if output:
                print(output.rstrip())
    return failures


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
