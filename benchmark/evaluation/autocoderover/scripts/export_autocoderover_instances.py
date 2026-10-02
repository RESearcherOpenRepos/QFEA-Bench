#!/usr/bin/env python3
"""Export QuanBench samples to AutoCodeRover local-issue instances."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.common.task_format import (  # noqa: E402
    format_interface_contract,
    format_requirements,
)


DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_OUTPUT = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "autocoderover"
    / "data"
    / "instances"
    / "autocoderover.secure.jsonl"
)
DEFAULT_TASK_TEMPLATE = (
    ROOT / "benchmark" / "evaluation" / "autocoderover" / "config" / "task_spec.j2"
)
DEFAULT_SOURCE_REPO_PATH = "/workspace/repo"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_sample_entries(samples_dir: Path, sample_filter: str | None = None) -> list[dict[str, Any]]:
    index_path = samples_dir / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Sample index not found: {index_path}")
    index = read_json(index_path)
    entries = list(index.get("samples") or [])
    if sample_filter:
        entries = [
            entry
            for entry in entries
            if sample_filter in str(entry.get("sample_path") or entry.get("sample_id") or "")
        ]
    return entries


def render_task_spec(sample: dict[str, Any], template_path: Path) -> str:
    task = sample["task"]
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
    )
    template = env.get_template(template_path.name)
    return template.render(
        feature_goal=task["problem_statement"].strip(),
        acceptance_requirements=format_requirements(task.get("requirements") or []),
        public_interface_contract=format_interface_contract(
            task.get("interface") or [],
            code_spans=True,
            strip_names=True,
        ),
    ).strip() + "\n"


def build_instance(
    samples_dir: Path,
    entry: dict[str, Any],
    *,
    task_template: Path,
    source_repo_path: str,
) -> dict[str, Any]:
    sample_path = samples_dir / str(entry["sample_path"]) / "sample.json"
    sample = read_json(sample_path)
    instance = sample["instance"]
    task = sample["task"]
    sample_id = instance["instance_id"]

    return {
        "instance_id": sample_id,
        "repo": instance["repo"],
        "base_commit": instance["base_commit"],
        "image_name": entry.get("docker_image") or f"benchmark-evaluation:{sample_id}",
        "source_repo_path": source_repo_path,
        "problem_statement": task["problem_statement"].strip(),
        "requirements": task.get("requirements") or [],
        "interface": task.get("interface") or [],
        "task_spec": render_task_spec(sample, task_template),
    }


def export_instances(
    *,
    samples_dir: Path,
    output_path: Path,
    task_template: Path,
    source_repo_path: str,
    sample_filter: str | None = None,
) -> list[dict[str, Any]]:
    entries = iter_sample_entries(samples_dir, sample_filter)
    instances = [
        build_instance(
            samples_dir,
            entry,
            task_template=task_template,
            source_repo_path=source_repo_path,
        )
        for entry in entries
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
        description="Export QuanBench samples as AutoCodeRover local-issue instances."
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--task-template", type=Path, default=DEFAULT_TASK_TEMPLATE)
    parser.add_argument("--source-repo-path", default=DEFAULT_SOURCE_REPO_PATH)
    parser.add_argument(
        "--filter",
        default=None,
        help="Only export samples whose sample path or instance id contains this substring.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instances = export_instances(
        samples_dir=args.samples_dir,
        output_path=args.output,
        task_template=args.task_template,
        source_repo_path=args.source_repo_path,
        sample_filter=args.filter,
    )
    print(f"Wrote {len(instances)} AutoCodeRover instances to {args.output}")


if __name__ == "__main__":
    main()
