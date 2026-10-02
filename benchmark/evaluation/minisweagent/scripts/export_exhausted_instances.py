#!/usr/bin/env python3
"""Export mini-SWE-agent instances that exhausted their step budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RESULTS = (
    Path("benchmark")
    / "evaluation"
    / "minisweagent"
    / "results"
    / "results_deepseek_v4_flash_20260531.json"
)
DEFAULT_INSTANCES = (
    Path("benchmark")
    / "evaluation"
    / "minisweagent"
    / "data"
    / "instances"
    / "sweagent.secure.jsonl"
)
DEFAULT_OUTPUT = (
    Path("benchmark")
    / "evaluation"
    / "minisweagent"
    / "data"
    / "instances"
    / "sweagent.deepseek_v4_flash_20260531.exhausted.jsonl"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def instance_id_from_row(row: dict[str, Any]) -> str:
    if "instance_id" in row:
        return str(row["instance_id"])
    if isinstance(row.get("problem_statement"), dict):
        return str(row["problem_statement"].get("id", ""))
    return ""


def exhausted_ids(results_path: Path) -> set[str]:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    ids = set()
    for result in payload.get("results") or []:
        if result.get("agent_step_exhausted"):
            ids.add(str(result["instance_id"]))
    return ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the subset of instances whose mini-SWE-agent result was step-exhausted."
    )
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--instances", type=Path, default=DEFAULT_INSTANCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exhausted = exhausted_ids(args.results)
    rows = [
        row
        for row in read_jsonl(args.instances)
        if instance_id_from_row(row) in exhausted
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    missing = exhausted - {instance_id_from_row(row) for row in rows}
    print(f"Wrote {len(rows)} exhausted instances to {args.output}")
    if missing:
        print(f"Missing {len(missing)} exhausted ids from instances file: {sorted(missing)}")


if __name__ == "__main__":
    main()
