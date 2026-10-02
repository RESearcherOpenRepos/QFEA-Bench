#!/usr/bin/env python3
"""Generate benchmark/dataset/samples/index.json from per-sample sample.json files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"
INDEX_FILENAME = "index.json"
SAMPLE_FILENAME = "sample.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def build_index_entry(sample_path: Path, samples_dir: Path) -> dict[str, Any]:
    sample = read_json(sample_path)
    instance = sample.get("instance", {})
    runtime = sample.get("runtime", {})
    docker = runtime.get("docker", {})

    return {
        "id": instance.get("id"),
        "sample_id": instance.get("instance_id"),
        "repo": instance.get("repo"),
        "sample_path": str(sample_path.parent.relative_to(samples_dir)),
        "docker_build_success": docker.get("build_success"),
        "docker_platform": docker.get("platform"),
        "docker_image": docker.get("image"),
    }


def find_sample_files(samples_dir: Path) -> list[Path]:
    return sorted(
        sample_file
        for sample_file in samples_dir.rglob(SAMPLE_FILENAME)
        if sample_file.parent != samples_dir
    )


def build_index(samples_dir: Path) -> dict[str, Any]:
    sample_files = find_sample_files(samples_dir)
    samples = [build_index_entry(sample_file, samples_dir) for sample_file in sample_files]
    ids = [sample["id"] for sample in samples]
    # Preserve published identities when an excluded sample leaves a gap.
    if any(type(sample_id) is not int or sample_id < 1 for sample_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("Sample IDs must be unique positive integers")
    samples.sort(key=lambda sample: sample["id"])
    return {
        "total_samples": len(samples),
        "samples": samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate benchmark/dataset/samples/index.json from sample.json files."
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=DEFAULT_SAMPLES_DIR,
        help="Directory containing per-sample subdirectories.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples_dir = args.samples_dir
    index = build_index(samples_dir)
    write_json(samples_dir / INDEX_FILENAME, index)


if __name__ == "__main__":
    main()
