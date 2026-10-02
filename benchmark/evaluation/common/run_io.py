"""Shared artifact writing helpers for benchmark agent runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark.evaluation.common.model_names import prediction_model_name
from benchmark.evaluation.common.output_schema import (
    annotate_summary,
    atomic_update_prediction,
    prediction_row,
    write_prediction_files,
)


def prediction_json_path(output_dir: Path) -> Path:
    return output_dir / "preds.json"


def prediction_jsonl_path(output_dir: Path) -> Path:
    return output_dir / "preds.jsonl"


def status_jsonl_path(output_dir: Path) -> Path:
    return output_dir / "status.jsonl"


def update_prediction_files(
    output_dir: Path,
    row: dict[str, Any],
    *,
    lock: Any | None = None,
    on_corrupt: Any | None = None,
) -> None:
    atomic_update_prediction(
        prediction_json_path(output_dir),
        row,
        jsonl_path=prediction_jsonl_path(output_dir),
        lock=lock,
        on_corrupt=on_corrupt,
    )


def write_prediction_artifacts(
    output_dir: Path,
    *,
    framework: str,
    instance_id: str,
    model_name: str,
    patch: str,
    agent: dict[str, Any] | None,
    lock: Any | None = None,
    on_corrupt: Any | None = None,
) -> dict[str, Any]:
    annotate_summary(
        output_dir / instance_id,
        framework=framework,
        instance_id=instance_id,
        agent=agent,
    )
    row = prediction_row(
        model_name_or_path=prediction_model_name(model_name),
        instance_id=instance_id,
        model_patch=patch,
        agent=agent,
    )
    update_prediction_files(output_dir, row, lock=lock, on_corrupt=on_corrupt)
    return row


def write_batch_prediction_files(output_dir: Path, rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    return write_prediction_files(output_dir, rows)


def append_status_row(
    output_dir: Path,
    row: dict[str, Any],
    *,
    lock: Any | None = None,
) -> None:
    def write() -> None:
        path = status_jsonl_path(output_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    if lock is None:
        write()
    else:
        with lock:
            write()
