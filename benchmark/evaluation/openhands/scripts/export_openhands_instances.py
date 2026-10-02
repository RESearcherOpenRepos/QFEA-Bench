#!/usr/bin/env python3
"""Export benchmark samples to OpenHands local-dataset JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_OUTPUT = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "openhands"
    / "data"
    / "instances"
    / "openhands.secure.jsonl"
)
DEFAULT_IMAGE_PREFIX = "benchmark-openhands-"
DEFAULT_SOURCE_REPO_PATH = "/workspace/repo"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_sample_files(samples_dir: Path, sample_filter: str | None = None) -> list[Path]:
    index_path = samples_dir / "index.json"
    if index_path.exists():
        index = read_json(index_path)
        paths = [
            samples_dir / item["sample_path"] / "sample.json"
            for item in index.get("samples", [])
        ]
    else:
        paths = sorted(samples_dir.rglob("sample.json"))
    if sample_filter:
        paths = [
            path
            for path in paths
            if sample_filter in str(path.parent.relative_to(samples_dir))
        ]
    return paths


def openhands_image_name(sample_id: str, image_prefix: str) -> str:
    return f"{image_prefix}{sample_id}:latest"


def build_instance(
    sample_path: Path,
    image_prefix: str,
    source_repo_path: str,
) -> dict[str, Any]:
    sample = read_json(sample_path)
    instance = sample["instance"]
    task = sample["task"]
    sample_id = instance["instance_id"]
    validation = sample.get("validation", {})

    return {
        "instance_id": sample_id,
        "repo": instance["repo"],
        "base_commit": instance["base_commit"],
        "problem_statement": task["problem_statement"].strip(),
        "requirements": task.get("requirements") or [],
        "interface": task.get("interface") or [],
        "image_name": openhands_image_name(sample_id, image_prefix),
        "platform": sample.get("runtime", {}).get("docker", {}).get("platform", "linux/amd64"),
        "source_repo_path": source_repo_path,
        "fail_pass": (
            validation.get("patched", {}).get("fail_pass", {}).get("file_list", [])
        ),
        "pass_pass": (
            validation.get("patched", {}).get("pass_pass", {}).get("file_list", [])
        ),
        "metadata": {
            "issue_url": instance.get("issue_url"),
            "pr_url": instance.get("pr_url"),
            "patch_commit": instance.get("patch"),
        },
    }


def export_instances(
    samples_dir: Path,
    output_path: Path,
    image_prefix: str,
    source_repo_path: str,
    sample_filter: str | None = None,
) -> list[dict[str, Any]]:
    instances = [
        build_instance(path, image_prefix, source_repo_path)
        for path in iter_sample_files(samples_dir, sample_filter)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(instance, ensure_ascii=False) for instance in instances)
        + ("\n" if instances else ""),
        encoding="utf-8",
    )
    return instances


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export QuanBench samples as an OpenHands local JSONL dataset."
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-prefix", default=DEFAULT_IMAGE_PREFIX)
    parser.add_argument("--source-repo-path", default=DEFAULT_SOURCE_REPO_PATH)
    parser.add_argument(
        "--filter",
        default=None,
        help="Only export samples whose sample path contains this substring.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instances = export_instances(
        args.samples_dir,
        args.output,
        args.image_prefix,
        args.source_repo_path,
        args.filter,
    )
    print(f"Wrote {len(instances)} OpenHands instances to {args.output}")


if __name__ == "__main__":
    main()
