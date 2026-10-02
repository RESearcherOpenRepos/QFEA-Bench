#!/usr/bin/env python3
"""Run all repository checks in their respective Python environments."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("all", "core", "openhands"), default="all")
    parser.add_argument("--core-python", type=Path, default=ROOT / ".venv/bin/python")
    parser.add_argument(
        "--openhands-python", type=Path,
        default=ROOT / "external/OpenHands-benchmarks/.venv/bin/python",
    )
    args = parser.parse_args()
    suites = {
        "core": (args.core_python, "benchmark/evaluation/tests"),
        "openhands": (args.openhands_python, "benchmark/evaluation/openhands/tests"),
    }
    selected = suites if args.suite == "all" else {args.suite: suites[args.suite]}
    failed = []
    for name, (python, test_path) in selected.items():
        print(f"Running {name} tests with {python}", flush=True)
        try:
            result = subprocess.run(
                [str(python), "-m", "pytest", "-q", test_path], cwd=ROOT,
                check=False,
            )
        except OSError as exc:
            print(f"Cannot start {name} tests: {exc}", flush=True)
            failed.append(name)
            continue
        if result.returncode:
            failed.append(name)
    if failed:
        print(f"Failed suites: {', '.join(failed)}", flush=True)
        return 1
    print(f"All requested suites passed: {', '.join(selected)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
