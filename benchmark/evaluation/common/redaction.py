"""Helpers for redacting secrets from benchmark artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REDACTED = "<redacted>"


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return (
        normalized in {"api_key", "apikey", "authorization", "secret"}
        or normalized.endswith("_api_key")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
    )


def redact_sensitive_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if is_sensitive_key(key) else redact_sensitive_values(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_values(item) for item in value]
    return value


def redact_json_file(path: Path) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    redacted = redact_sensitive_values(payload)
    if redacted != payload:
        path.write_text(json.dumps(redacted, indent=2, ensure_ascii=False), encoding="utf-8")
