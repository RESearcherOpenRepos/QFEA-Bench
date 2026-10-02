#!/usr/bin/env python3
"""Export benchmark samples to mini-SWE-agent batch instances."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.common.network_isolation import (  # noqa: E402
    AGENT_EGRESS_FIREWALL_COMMAND,
    NET_ADMIN_DOCKER_ARGS,
)

DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_OUTPUT = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "minisweagent"
    / "data"
    / "instances"
    / "sweagent.secure.jsonl"
)
DEFAULT_REPO_NAME = "repo"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_sample_files(samples_dir: Path) -> list[Path]:
    index_path = samples_dir / "index.json"
    if index_path.exists():
        index = read_json(index_path)
        return [
            samples_dir / item["sample_path"] / "sample.json"
            for item in index.get("samples", [])
        ]
    return sorted(samples_dir.rglob("sample.json"))


def format_problem_statement(sample: dict[str, Any]) -> str:
    task = sample["task"]
    sections = [
        "# Benchmark Task Specification",
        "## Feature Goal\n" + task["problem_statement"].strip(),
    ]

    requirements = task.get("requirements") or []
    if requirements:
        requirement_lines = [f"{idx}. {item}" for idx, item in enumerate(requirements, start=1)]
        sections.append("## Acceptance Requirements\n" + "\n".join(requirement_lines))

    interfaces = task.get("interface") or []
    if interfaces:
        lines = []
        for idx, item in enumerate(interfaces, start=1):
            item_type = item.get("Type", "").strip() or "Interface"
            item_name = item.get("Name", "").strip() or "<unnamed>"
            parts = [f"{idx}. `{item_type}` `{item_name}`"]
            for key in ("Path", "Input", "Output", "Description"):
                value = item.get(key)
                if value:
                    parts.append(f"   - {key}: {value}")
            lines.append("\n".join(parts))
        sections.append("## Public Interface Contract\n" + "\n".join(lines))

    return "\n\n".join(sections) + "\n"


def adapter_image_name(sample_id: str, prefix: str) -> str:
    return f"{prefix}{sample_id}:latest"


def build_instance(sample_path: Path, image_prefix: str, repo_name: str) -> dict[str, Any]:
    sample = read_json(sample_path)
    instance = sample["instance"]
    sample_id = instance["instance_id"]
    return {
        "image_name": adapter_image_name(sample_id, image_prefix),
        "problem_statement": format_problem_statement(sample),
        "instance_id": sample_id,
        "repo_name": repo_name,
        "base_commit": instance["base_commit"],
    }


def build_expert_instance(sample_path: Path, image_prefix: str, repo_name: str) -> dict[str, Any]:
    simple = build_instance(sample_path, image_prefix, repo_name)
    return {
        "env": {
            "deployment": {
                "type": "docker",
                "image": simple["image_name"],
                "docker_args": NET_ADMIN_DOCKER_ARGS,
                "python_standalone_dir": "",
                "platform": "linux/amd64",
            },
            "repo": {
                "type": "preexisting",
                "repo_name": repo_name,
                "base_commit": simple["base_commit"],
                "reset": True,
            },
            "post_startup_commands": [AGENT_EGRESS_FIREWALL_COMMAND],
            "post_startup_command_timeout": 30,
            "name": "main",
        },
        "problem_statement": {
            "type": "text",
            "text": simple["problem_statement"],
            "id": simple["instance_id"],
        },
    }


def export_instances(
    samples_dir: Path,
    output_path: Path,
    image_prefix: str,
    repo_name: str,
    export_format: str = "simple",
) -> list[dict[str, Any]]:
    if export_format == "simple":
        instances = [build_instance(path, image_prefix, repo_name) for path in iter_sample_files(samples_dir)]
    elif export_format == "expert":
        instances = [build_expert_instance(path, image_prefix, repo_name) for path in iter_sample_files(samples_dir)]
    else:
        raise ValueError(f"Unsupported export format: {export_format}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(instance, ensure_ascii=False) for instance in instances) + "\n",
        encoding="utf-8",
    )
    return instances


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export mini-SWE-agent instances for benchmark samples.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--format", choices=["simple", "expert"], default="expert")
    parser.add_argument("--image-prefix", default="benchmark-minisweagent-")
    parser.add_argument(
        "--repo-name",
        default=DEFAULT_REPO_NAME,
        help="Slashless repository name exposed at the container root for SWE-agent PreExistingRepoConfig.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instances = export_instances(args.samples_dir, args.output, args.image_prefix, args.repo_name, args.format)
    print(f"Wrote {len(instances)} mini-SWE-agent instances to {args.output}")


if __name__ == "__main__":
    main()
