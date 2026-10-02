"""Shared output schema helpers for benchmark agent runners."""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any

from benchmark.evaluation.common.run_status import (
    agent_repeated_command_loop,
    agent_step_exhausted,
    row_repeated_command_loop,
    row_step_exhausted,
    row_submitted,
    row_timed_out,
)
from benchmark.evaluation.common.token_usage import (
    cumulative_token_records,
    token_counts_from_usage,
    token_record,
)


AGENT_METRIC_KEYS = (
    "steps",
    "input_tokens",
    "cached_input_tokens",
    "cache_creation_input_tokens",
    "output_tokens",
    "instance_cost",
    "success",
    "run_completed",
    "step_budget_exhausted",
    "timed_out",
    "repeated_command_loop",
    "repeated_command",
    "consecutive_count",
    "consecutive_command_limit",
    "exit_status",
    "patch_candidate_submitted",
    "patch_extraction_status",
    "patch_extraction_statuses",
    "error",
    "token_by_step",
    "cumulative_token_by_step",
)


def default_agent_metrics() -> dict[str, Any]:
    return {
        "steps": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "output_tokens": 0,
        "instance_cost": None,
        "success": None,
        "run_completed": None,
        "step_budget_exhausted": False,
        "timed_out": False,
        "repeated_command_loop": False,
        "repeated_command": None,
        "consecutive_count": None,
        "consecutive_command_limit": None,
        "exit_status": None,
        "patch_candidate_submitted": False,
        "patch_extraction_status": None,
        "patch_extraction_statuses": [],
        "error": None,
        "token_by_step": [],
        "cumulative_token_by_step": [],
    }


def normalize_agent_metrics(agent: dict[str, Any] | None) -> dict[str, Any]:
    normalized = default_agent_metrics()
    if isinstance(agent, dict):
        normalized.update({key: value for key, value in agent.items() if key in AGENT_METRIC_KEYS})
        token_counts = token_counts_from_usage(agent)
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "cache_creation_input_tokens",
            "output_tokens",
        ):
            if not normalized.get(key) and token_counts.get(key):
                normalized[key] = token_counts[key]
    return normalized


def cost_value(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        cost = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(cost):
        return None
    return cost


def prediction_row(
    *,
    model_name_or_path: str,
    instance_id: str,
    model_patch: str,
    agent: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_agent = normalize_agent_metrics(agent)
    return {
        "model_name_or_path": model_name_or_path,
        "instance_id": instance_id,
        "model_patch": model_patch or "",
        "step_exhausted": agent_step_exhausted(normalized_agent),
        "timed_out": row_timed_out({"_agent": normalized_agent}),
        "repeated_command_loop": agent_repeated_command_loop(normalized_agent),
        "repeated_command": normalized_agent.get("repeated_command"),
        "consecutive_count": normalized_agent.get("consecutive_count"),
        "consecutive_command_limit": normalized_agent.get("consecutive_command_limit"),
        "patch_candidate_submitted": bool(normalized_agent.get("patch_candidate_submitted")),
        "patch_extraction_status": normalized_agent.get("patch_extraction_status"),
        "_agent": normalized_agent,
    }


def prediction_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    step_exhausted = 0
    timed_out = 0
    repeated_command_loop = 0
    submitted = 0
    total_steps = 0
    total_input_tokens = 0
    total_cached_input_tokens = 0
    total_cache_creation_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    has_cost = False
    for row in rows:
        agent = normalize_agent_metrics(
            row.get("_agent") or row.get("agent") or row.get("_summary_agent")
        )
        total_steps += agent.get("steps") or 0
        instance_cost = cost_value(agent.get("instance_cost"))
        if instance_cost is not None:
            total_cost += instance_cost
            has_cost = True
        total_input_tokens += agent.get("input_tokens") or 0
        total_cached_input_tokens += agent.get("cached_input_tokens") or 0
        total_cache_creation_input_tokens += agent.get("cache_creation_input_tokens") or 0
        total_output_tokens += agent.get("output_tokens") or 0
        row_for_status = {**row, "_agent": agent}
        if row_step_exhausted(row_for_status):
            step_exhausted += 1
        elif row_timed_out(row_for_status):
            timed_out += 1
        elif row_repeated_command_loop(row_for_status):
            repeated_command_loop += 1
        elif row_submitted(row_for_status):
            submitted += 1
    summary = {
        "total": len(rows),
        "success": submitted + step_exhausted + timed_out + repeated_command_loop,
        "submitted": submitted,
        "step_exhausted": step_exhausted,
        "timed_out": timed_out,
        "repeated_command_loop": repeated_command_loop,
        "steps": total_steps,
        "total_cost": round(total_cost, 6) if has_cost else None,
    }
    summary.update(
        {
        "input_tokens": total_input_tokens,
        "cached_input_tokens": total_cached_input_tokens,
        "cache_creation_input_tokens": total_cache_creation_input_tokens,
        "output_tokens": total_output_tokens,
        }
    )
    return summary


def prediction_payload(rows: list[dict[str, Any]] | dict[str, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(rows, dict):
        rows_by_instance = {
            instance_id: normalize_prediction_row(instance_id, row)
            for instance_id, row in rows.items()
            if isinstance(row, dict)
        }
    else:
        rows_by_instance = {
            row["instance_id"]: normalize_prediction_row(row["instance_id"], row)
            for row in rows
        }
    row_list = list(rows_by_instance.values())
    output_rows = {
        instance_id: {
            key: value
            for key, value in row.items()
            if key not in {"_summary_agent", "_agent", "agent"}
        }
        for instance_id, row in rows_by_instance.items()
    }
    return {
        "summary": prediction_summary(row_list),
        "predictions": output_rows,
    }


def normalize_prediction_row(instance_id: str, row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    normalized.setdefault("instance_id", instance_id)
    normalized.setdefault("model_name_or_path", "")
    normalized.setdefault("model_patch", "")
    existing_summary_agent = normalized.pop("_summary_agent", None)
    agent = normalize_agent_metrics(
        normalized.pop("_agent", None) or normalized.pop("agent", None) or existing_summary_agent
    )
    normalized["step_exhausted"] = row_step_exhausted({**normalized, "_agent": agent})
    normalized["timed_out"] = row_timed_out({**normalized, "_agent": agent})
    normalized["repeated_command_loop"] = row_repeated_command_loop({**normalized, "_agent": agent})
    normalized.setdefault("repeated_command", agent.get("repeated_command"))
    normalized.setdefault("consecutive_count", agent.get("consecutive_count"))
    normalized.setdefault("consecutive_command_limit", agent.get("consecutive_command_limit"))
    normalized.setdefault(
        "patch_candidate_submitted",
        bool(agent.get("patch_candidate_submitted")),
    )
    normalized.setdefault("patch_extraction_status", agent.get("patch_extraction_status"))
    instance_cost = agent.get("instance_cost")
    if instance_cost is None:
        instance_cost = normalized.get("instance_cost")
    normalized["_summary_agent"] = {
        "steps": agent.get("steps") or normalized.get("steps") or 0,
        "instance_cost": instance_cost,
        "input_tokens": agent.get("input_tokens") or normalized.get("input_tokens") or 0,
        "cached_input_tokens": agent.get("cached_input_tokens") or normalized.get("cached_input_tokens") or 0,
        "cache_creation_input_tokens": (
            agent.get("cache_creation_input_tokens")
            or normalized.get("cache_creation_input_tokens")
            or 0
        ),
        "output_tokens": agent.get("output_tokens") or normalized.get("output_tokens") or 0,
        "timed_out": bool(agent.get("timed_out") or normalized.get("timed_out")),
        "patch_candidate_submitted": bool(
            agent.get("patch_candidate_submitted")
            or normalized.get("patch_candidate_submitted")
        ),
        "patch_extraction_status": (
            agent.get("patch_extraction_status")
            or normalized.get("patch_extraction_status")
        ),
    }
    return normalized


def prediction_rows_from_payload(payload: Any) -> dict[str, dict[str, Any]]:
    if isinstance(payload, list):
        return {
            row["instance_id"]: normalize_prediction_row(row["instance_id"], row)
            for row in payload
            if isinstance(row, dict) and row.get("instance_id")
        }
    if not isinstance(payload, dict):
        return {}
    predictions = payload.get("predictions")
    if isinstance(predictions, dict):
        return {
            instance_id: normalize_prediction_row(instance_id, row)
            for instance_id, row in predictions.items()
            if isinstance(row, dict)
        }
    return {
        instance_id: normalize_prediction_row(instance_id, row)
        for instance_id, row in payload.items()
        if instance_id != "summary" and isinstance(row, dict)
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


def write_preds_json(path: Path, rows: list[dict[str, Any]] | dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prediction_payload(rows), indent=2, ensure_ascii=False), encoding="utf-8")


def enrich_prediction_rows_from_summaries(
    output_dir: Path,
    rows_by_instance: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for instance_id, row in rows_by_instance.items():
        normalized = normalize_prediction_row(instance_id, row)
        summary_file = summary_path(output_dir / instance_id, instance_id)
        if summary_file.exists():
            try:
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                summary = {}
            if isinstance(summary, dict) and isinstance(summary.get("agent"), dict):
                normalized["_summary_agent"] = normalize_agent_metrics(summary["agent"])
        enriched[instance_id] = normalized
    return enriched


def write_prediction_files(output_dir: Path, rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    jsonl_path = output_dir / "preds.jsonl"
    json_path = output_dir / "preds.json"
    rows_by_instance = {
        row["instance_id"]: normalize_prediction_row(row["instance_id"], row)
        for row in rows
    }
    rows_by_instance = enrich_prediction_rows_from_summaries(output_dir, rows_by_instance)
    payload = prediction_payload(rows_by_instance)
    normalized_rows = list(payload["predictions"].values())
    write_jsonl(jsonl_path, normalized_rows)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return jsonl_path, json_path


def atomic_update_prediction(
    preds_path: Path,
    row: dict[str, Any],
    *,
    jsonl_path: Path | None = None,
    lock: Any | None = None,
    on_corrupt: Any | None = None,
) -> None:
    def update() -> None:
        rows_by_instance: dict[str, dict[str, Any]] = {}
        if preds_path.exists() and preds_path.stat().st_size:
            try:
                rows_by_instance = prediction_rows_from_payload(
                    json.loads(preds_path.read_text(encoding="utf-8"))
                )
            except json.JSONDecodeError:
                backup_path = preds_path.with_suffix(f".corrupt-{int(time.time())}.json")
                preds_path.replace(backup_path)
                if on_corrupt is not None:
                    on_corrupt(backup_path)
        rows_by_instance[row["instance_id"]] = normalize_prediction_row(row["instance_id"], row)
        rows_by_instance = enrich_prediction_rows_from_summaries(preds_path.parent, rows_by_instance)
        payload = prediction_payload(rows_by_instance)
        tmp_path = preds_path.with_suffix(f".{os.getpid()}.tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(preds_path)
        if jsonl_path is not None:
            write_jsonl(jsonl_path, list(payload["predictions"].values()))

    if lock is None:
        update()
    else:
        with lock:
            update()


def trajectory_path(instance_dir: Path, instance_id: str) -> Path:
    return instance_dir / f"{instance_id}.traj.json"


def summary_path(instance_dir: Path, instance_id: str) -> Path:
    return instance_dir / f"{instance_id}.summary.json"


def write_trajectory(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary(path: Path, *, framework: str, instance_id: str, agent: dict[str, Any] | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "framework": framework,
                "instance_id": instance_id,
                "agent": normalize_agent_metrics(agent),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def annotate_summary(
    instance_dir: Path,
    *,
    framework: str,
    instance_id: str,
    agent: dict[str, Any] | None,
) -> Path:
    path = summary_path(instance_dir, instance_id)
    write_summary(path, framework=framework, instance_id=instance_id, agent=agent)
    return path


def annotate_trajectory(
    path: Path,
    *,
    framework: str,
    instance_id: str,
    agent: dict[str, Any] | None = None,
) -> None:
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    raw_output = payload.get("raw_output")
    if not isinstance(raw_output, dict):
        raw_output = {
            key: value
            for key, value in payload.items()
            if key not in {"schema_version", "framework", "instance_id", "agent", "raw_output"}
        }
    normalized_agent = normalize_agent_metrics(agent if agent is not None else payload.get("agent"))
    write_trajectory(
        path,
        {
            "schema_version": 1,
            "framework": framework,
            "instance_id": instance_id,
            "agent": normalized_agent,
            "raw_output": raw_output,
        },
    )
