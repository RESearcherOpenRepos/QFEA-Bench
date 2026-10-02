"""Shared task text formatting for benchmark runner prompts."""

from __future__ import annotations

from typing import Any


def format_requirements(requirements: list[str]) -> str:
    if not requirements:
        return "(No explicit acceptance requirements were provided.)"
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(requirements, start=1))


def format_interface_contract(
    interface_items: list[dict[str, Any]],
    *,
    code_spans: bool = False,
    strip_names: bool = False,
) -> str:
    if not interface_items:
        return "(No explicit public interface contract was provided.)"
    lines = []
    for idx, item in enumerate(interface_items, start=1):
        item_type = str(item.get("Type") or "Interface")
        item_name = str(item.get("Name") or "<unnamed>")
        if strip_names:
            item_type = item_type.strip() or "Interface"
            item_name = item_name.strip() or "<unnamed>"
        if code_spans:
            parts = [f"{idx}. `{item_type}` `{item_name}`"]
        else:
            parts = [f"{idx}. {item_type} {item_name}"]
        for key in ("Path", "Input", "Output", "Description"):
            value = item.get(key)
            if value:
                parts.append(f"   - {key}: {value}")
        lines.append("\n".join(parts))
    return "\n".join(lines)
