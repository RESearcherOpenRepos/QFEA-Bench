"""Small shared I/O helpers for benchmark evaluation scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_safely(path: Path) -> Any | None:
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError):
        return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_slice_spec(slice_spec: str | None) -> slice | None:
    if not slice_spec:
        return None
    values = [int(value) if value else None for value in slice_spec.split(":")]
    return slice(*values)


def filter_by_instance_id(
    rows: Iterable[dict[str, Any]],
    pattern: str | None,
    slice_spec: str | None,
) -> list[dict[str, Any]]:
    items = list(rows)
    if pattern:
        regex = re.compile(pattern)
        items = [item for item in items if regex.search(str(item.get("instance_id") or ""))]
    parsed_slice = parse_slice_spec(slice_spec)
    if parsed_slice is not None:
        items = items[parsed_slice]
    return items
