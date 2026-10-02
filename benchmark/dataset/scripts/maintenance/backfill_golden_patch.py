#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


NON_SOURCE_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ipynb",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".csv",
    ".tsv",
}

EXCLUDED_PREFIXES = (
    "docs/",
    "releasenotes/",
    ".github/",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill golden_patch.oracle_files for benchmark samples."
    )
    parser.add_argument(
        "--samples-root",
        type=Path,
        default=Path("benchmark/dataset/samples"),
        help="Root directory containing sample folders.",
    )
    parser.add_argument(
        "--repo-dir",
        required=True,
        help="Repository subdirectory under samples root, for example qiskit-machine-learning.",
    )
    parser.add_argument(
        "--repo-cache-root",
        type=Path,
        required=True,
        help="Root directory containing cached source repositories.",
    )
    parser.add_argument(
        "--status-json",
        type=Path,
        default=None,
        help="Path to write the processing status summary JSON.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write changes back to sample.json files. Without this flag the script only reports.",
    )
    return parser.parse_args()


def repo_cache_dir(repo_slug: str, repo_cache_root: Path) -> Path:
    return repo_cache_root / repo_slug.replace("/", "__")


def changed_files(repo_dir: Path, base_commit: str, patch_commit: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "diff", "--name-only", base_commit, patch_commit],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_test_like_path(path: str) -> bool:
    lowered = path.lower()
    parts = lowered.split("/")
    base = parts[-1]
    return (
        "test" in parts
        or "tests" in parts
        or base.startswith("test_")
        or base.endswith("_test.py")
    )


def is_golden_patch_file(path: str) -> bool:
    lowered = path.lower()
    if lowered.startswith(EXCLUDED_PREFIXES):
        return False
    if is_test_like_path(lowered):
        return False
    base = Path(lowered).name
    if base.startswith("."):
        return False
    if Path(lowered).suffix in NON_SOURCE_SUFFIXES:
        return False
    return True


def interface_paths(sample: dict) -> list[str]:
    paths = []
    for item in sample.get("task", {}).get("interface", []) or []:
        path = (item.get("Path") or "").strip()
        if path:
            paths.append(path)
    return sorted(set(paths))


def backfill_sample(sample_path: Path, repo_dir: Path, write: bool) -> dict:
    data = json.loads(sample_path.read_text())
    instance = data["instance"]
    diff_files = changed_files(repo_dir, instance["base_commit"], instance["patch"])
    oracle_files = [path for path in diff_files if is_golden_patch_file(path)]
    context_only_interface_files = [
        path for path in interface_paths(data) if path not in oracle_files
    ]

    if write:
        ordered = {
            "instance": data["instance"],
            "golden_patch": {"oracle_files": oracle_files},
        }
        for key, value in data.items():
            if key not in ordered:
                ordered[key] = value
        sample_path.write_text(json.dumps(ordered, indent=2) + "\n")

    return {
        "sample_id": instance["instance_id"],
        "sample_path": str(sample_path),
        "status": "processed" if oracle_files else "pending_review",
        "oracle_files": oracle_files,
        "oracle_file_count": len(oracle_files),
        "changed_file_count": len(diff_files),
        "excluded_files": [path for path in diff_files if path not in oracle_files],
        "context_only_interface_files": context_only_interface_files,
    }


def main() -> None:
    args = parse_args()
    samples_dir = args.samples_root / args.repo_dir
    sample_paths = sorted(samples_dir.glob("*/sample.json"))
    if not sample_paths:
        raise SystemExit(f"No sample.json files found under {samples_dir}")

    first_sample = json.loads(sample_paths[0].read_text())
    repo_slug = first_sample["instance"]["repo"]
    repo_dir = repo_cache_dir(repo_slug, args.repo_cache_root)
    if not repo_dir.exists():
        raise SystemExit(f"Cached repository not found: {repo_dir}")

    status_json = args.status_json
    if status_json is None:
        status_json = Path(
            f"benchmark/dataset/build_logs/golden_patch_backfill_status.{args.repo_dir}.json"
        )

    results = [backfill_sample(path, repo_dir, args.write) for path in sample_paths]

    processed = [item["sample_id"] for item in results if item["status"] == "processed"]
    pending = [item["sample_id"] for item in results if item["status"] != "processed"]

    status_payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_dir": args.repo_dir,
        "repo_slug": repo_slug,
        "write_mode": args.write,
        "processed_count": len(processed),
        "pending_count": len(pending),
        "processed_sample_ids": processed,
        "pending_sample_ids": pending,
        "samples": results,
    }

    status_json.parent.mkdir(parents=True, exist_ok=True)
    status_json.write_text(json.dumps(status_payload, indent=2) + "\n")
    print(json.dumps(status_payload, indent=2))


if __name__ == "__main__":
    main()
