#!/usr/bin/env python3
"""Merge JSONL rows by instance_id while preserving dataset order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def instance_id(row: dict[str, Any]) -> str:
    value = row.get("instance_id")
    if not value:
        raise ValueError(f"JSONL row has no instance_id: {row}")
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge updated per-instance JSONL rows into an existing JSONL file."
    )
    parser.add_argument("--base", type=Path, required=True, help="Existing full JSONL file.")
    parser.add_argument("--updates", type=Path, required=True, help="New JSONL rows to overlay.")
    parser.add_argument(
        "--instances",
        type=Path,
        required=True,
        help="Full instance JSONL used only to preserve benchmark order.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows: dict[str, dict[str, Any]] = {}
    for path in (args.base, args.updates):
        for row in read_jsonl(path):
            rows[instance_id(row)] = row

    order = [instance_id(row) for row in read_jsonl(args.instances)]
    ordered_ids = [item for item in order if item in rows]
    extra_ids = sorted(set(rows) - set(ordered_ids))
    output_rows = [rows[item] for item in ordered_ids + extra_ids]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output_rows),
        encoding="utf-8",
    )
    nonempty = sum(1 for row in output_rows if str(row.get("model_patch", "")).strip())
    print(f"Wrote {len(output_rows)} rows to {args.output} ({nonempty} nonempty model_patch rows)")


if __name__ == "__main__":
    main()
