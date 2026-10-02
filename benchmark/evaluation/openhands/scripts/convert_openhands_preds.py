#!/usr/bin/env python3
"""Convert OpenHands benchmark output JSONL to evaluator predictions."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.common.output_schema import (  # noqa: E402
    annotate_summary,
    default_agent_metrics,
    prediction_payload,
    prediction_row,
    trajectory_path,
    write_trajectory,
    write_preds_json,
    write_jsonl,
)
from benchmark.evaluation.common.run_io import update_prediction_files  # noqa: E402
from benchmark.evaluation.common.run_status import row_repeated_command_loop  # noqa: E402
from benchmark.evaluation.common.io_utils import read_jsonl  # noqa: E402
from benchmark.evaluation.common.model_names import (  # noqa: E402
    prediction_model_name as artifact_model_name,
)
from benchmark.evaluation.common.model_pricing import estimated_cost_usd  # noqa: E402
from benchmark.evaluation.common.token_usage import (  # noqa: E402
    cumulative_token_records,
    token_record,
    token_counts_from_usage,
    token_records_from_usages,
)
from benchmark.evaluation.openhands.scripts.run_policy import (  # noqa: E402
    count_unique_agent_steps,
    event_kind,
    event_value,
    has_completion_signal,
    row_step_budget_exhausted,
)


EXCLUDED_PATCH_PREFIXES = (
    "workspace/",
    "conversations/",
    "bash_events/",
)
REASONING_ARTIFACT_KEYS = {
    "reasoning",
    "reasoning_content",
    "reasoning_details",
    "reasoning_effort",
    "reasoning_summary",
    "responses_reasoning_item",
    "thinking",
    "thinking_blocks",
    "enable_encrypted_reasoning",
    "extended_thinking_budget",
}
REASONING_TOKEN_KEYS = {
    "reasoning_tokens",
    "internal_reasoning_tokens",
}
REASONING_ARTIFACT_MARKERS = tuple(
    f'"{key}"' for key in sorted(REASONING_ARTIFACT_KEYS | REASONING_TOKEN_KEYS)
)
REASONING_ARTIFACT_SUBSTRINGS = (
    "reasoning_content",
    "reasoning_details",
    "reasoning_effort",
    "reasoning_summary",
    "responses_reasoning_item",
    "thinking_blocks",
    "enable_encrypted_reasoning",
    "extended_thinking_budget",
    "reasoning_tokens",
    "internal_reasoning_tokens",
)
REDACTED_REASONING_TEXT = "[redacted reasoning artifact]"
REASONING_LOG_PATTERNS = (
    re.compile(r',?\s*"reasoning_tokens"\s*:\s*\d+'),
    re.compile(r',?\s*"internal_reasoning_tokens"\s*:\s*\d+'),
    re.compile(r',?\s*"reasoning_effort"\s*:\s*(null|"([^"\\]|\\.)*")'),
    re.compile(r',?\s*"reasoning_summary"\s*:\s*(null|"([^"\\]|\\.)*")'),
    re.compile(r',?\s*"enable_encrypted_reasoning"\s*:\s*(true|false|null)'),
    re.compile(r',?\s*"extended_thinking_budget"\s*:\s*\d+'),
    re.compile(r',?\s*"thinking_blocks"\s*:\s*\[[^\]]*\]'),
    re.compile(r',?\s*"thinking"\s*:\s*(null|"([^"\\]|\\.)*"|\{[^{}]*\})'),
    re.compile(r',?\s*"reasoning"\s*:\s*(null|"([^"\\]|\\.)*"|\{[^{}]*\})'),
    re.compile(r',?\s*"reasoning_content"\s*:\s*"([^"\\]|\\.)*"'),
    re.compile(r',?\s*"reasoning_content"\s*:\s*null'),
    re.compile(r',?\s*"reasoning_details"\s*:\s*\[[^\]]*\]'),
    re.compile(r',?\s*"responses_reasoning_item"\s*:\s*(null|\{[^{}]*\})'),
)


def read_output_rows(path: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(path) if path.exists() else []
    error_path = Path(str(path).replace(".jsonl", "_errors.jsonl"))
    if path.name == "output.jsonl" and error_path.exists():
        rows.extend(read_jsonl(error_path))
    return rows


def _diff_block_path(header: str) -> str | None:
    if not header.startswith("diff --git "):
        return None
    parts = header.split()
    if len(parts) < 4:
        return None
    path = parts[3]
    if path.startswith("b/"):
        path = path[2:]
    return path


def clean_patch(patch: str) -> str:
    """Drop OpenHands agent-server state files from a unified git patch."""
    if not patch:
        return ""

    kept_blocks: list[str] = []
    current: list[str] = []
    current_path: str | None = None

    def flush_current() -> None:
        if not current:
            return
        if current_path is None or not current_path.startswith(EXCLUDED_PATCH_PREFIXES):
            kept_blocks.extend(current)

    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            flush_current()
            current = [line]
            current_path = _diff_block_path(line)
            continue
        current.append(line)
    flush_current()

    return "".join(kept_blocks)


def has_native_completion(row: dict[str, Any]) -> bool:
    """Return whether OpenHands reached one of its native completion states."""
    return has_completion_signal(row.get("history") or [])


def is_manually_failed(row: dict[str, Any]) -> bool:
    """Return whether this raw run row was manually invalidated for rerun."""
    test_result = row.get("test_result") or {}
    return bool(isinstance(test_result, dict) and test_result.get("manual_failed"))


def extract_patch(row: dict[str, Any]) -> str:
    if (
        is_manually_failed(row)
        or row.get("error")
        or is_step_budget_exhausted(row)
        or is_repeated_command_loop(row)
        or not has_native_completion(row)
    ):
        return ""
    test_result = row.get("test_result") or {}
    if isinstance(test_result, dict):
        patch = test_result.get("git_patch") or test_result.get("model_patch") or ""
        return clean_patch(patch)
    return ""


def row_result_rank(row: dict[str, Any]) -> int:
    """Rank duplicate output rows for the same instance.

    OpenHands can leave an infrastructure error row in ``output_errors.jsonl``
    even when a retry later writes a successful row to ``output.jsonl``. When
    both files are merged, prefer the most useful completed row instead of
    blindly letting the later error row overwrite it.
    """
    if extract_patch(row).strip():
        return 5
    if row.get("error") or is_manually_failed(row):
        return 0
    if is_step_budget_exhausted(row) or is_repeated_command_loop(row):
        return 4
    if has_native_completion(row):
        return 3
    if row.get("metrics") or row.get("history"):
        return 2
    return 1


def select_canonical_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select one canonical row per instance while preserving first-seen order."""
    selected: dict[str, dict[str, Any]] = {}
    selected_rank: dict[str, int] = {}
    order: list[str] = []
    for row in rows:
        instance_id = row["instance_id"]
        if instance_id not in selected:
            order.append(instance_id)
        rank = row_result_rank(row)
        if instance_id not in selected or rank >= selected_rank[instance_id]:
            selected[instance_id] = row
            selected_rank[instance_id] = rank
    return [selected[instance_id] for instance_id in order]


def is_step_budget_exhausted(row: dict[str, Any]) -> bool:
    if is_manually_failed(row):
        return False
    return row_step_budget_exhausted(row)


def is_repeated_command_loop(row: dict[str, Any]) -> bool:
    test_result = row.get("test_result") or {}
    return row_repeated_command_loop(row) or bool(
        isinstance(test_result, dict) and test_result.get("repeated_command_loop")
    )


def unique_token_usages(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    usages: list[dict[str, Any]] = []
    seen_response_ids: set[str] = set()
    for usage in metrics.get("token_usages") or []:
        if not isinstance(usage, dict):
            continue
        response_id = usage.get("response_id")
        if response_id:
            response_id = str(response_id)
            if response_id in seen_response_ids:
                continue
            seen_response_ids.add(response_id)
        usages.append(usage)
    return usages


def action_response_ids(events: list[Any]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for event in events:
        if event_kind(event) != "ActionEvent":
            continue
        if not event_value(event, "tool_name"):
            continue
        response_id = event_value(event, "llm_response_id")
        if not response_id:
            continue
        response_id = str(response_id)
        if response_id in seen:
            continue
        seen.add(response_id)
        ids.append(response_id)
    return ids


def add_token_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key in (
        "input_tokens",
        "cached_input_tokens",
        "cache_creation_input_tokens",
        "output_tokens",
    ):
        target[key] += source.get(key, 0)


def row_model_name(row: dict[str, Any], fallback: str = "") -> str:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    llm = metadata.get("llm") if isinstance(metadata.get("llm"), dict) else {}
    if llm.get("model"):
        return str(llm["model"])

    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    for usage in metrics.get("token_usages") or []:
        if isinstance(usage, dict) and usage.get("model"):
            return str(usage["model"])
    for cost in metrics.get("costs") or []:
        if isinstance(cost, dict) and cost.get("model"):
            return str(cost["model"])
    return fallback


def estimated_row_cost(
    row: dict[str, Any],
    fallback_model_name: str = "",
) -> float | None:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    token_usage = metrics.get("accumulated_token_usage") or {}
    token_totals = token_counts_from_usage(token_usage)
    return estimated_cost_usd(row_model_name(row, fallback_model_name), token_totals)


def token_usage_by_step(
    metrics: dict[str, Any],
    events: list[Any],
) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    """Return token usage aligned to OpenHands action steps.

    OpenHands may record a small LLM usage before the first ActionEvent. That
    usage is real cost, but it is not an action step. Fold such unmatched usage
    into step 1 so step-limited post-processing keeps total cost conservative
    while keeping one token record per action step.
    """
    usages = unique_token_usages(metrics)
    response_ids = action_response_ids(events)
    if not response_ids:
        return token_records_from_usages(usages)

    response_index = {response_id: index for index, response_id in enumerate(response_ids)}
    per_step = [
        {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 0,
        }
        for _ in response_ids
    ]
    unmatched = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "output_tokens": 0,
    }

    for usage in usages:
        counts = token_counts_from_usage(usage)
        response_id = usage.get("response_id")
        index = response_index.get(str(response_id)) if response_id else None
        if index is None:
            add_token_counts(unmatched, counts)
            continue
        add_token_counts(per_step[index], counts)

    add_token_counts(per_step[0], unmatched)
    records = [
        token_record(
            step=index + 1,
            input_tokens=counts["input_tokens"],
            output_tokens=counts["output_tokens"],
            cached_input_tokens=counts["cached_input_tokens"],
            cache_creation_input_tokens=counts["cache_creation_input_tokens"],
        )
        for index, counts in enumerate(per_step)
    ]
    return records, cumulative_token_records(records)


def extract_agent_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Extract native OpenHands step and token metrics for evaluator summaries."""
    test_result = row.get("test_result") or {}
    metrics = row.get("metrics") or {}
    if not metrics and isinstance(test_result, dict):
        metrics = test_result.get("metrics") or {}
    token_usage = metrics.get("accumulated_token_usage") or {}
    token_totals = token_counts_from_usage(token_usage)
    instance_cost = estimated_row_cost(row)
    if instance_cost is None:
        instance_cost = metrics.get("accumulated_cost")
    response_steps = count_unique_agent_steps(row.get("history") or [])
    budget_exhausted = is_step_budget_exhausted(row)
    repeated_loop = is_repeated_command_loop(row)
    submitted_patch = bool(extract_patch(row).strip())
    run_completed = bool(
        row.get("error") is None
        and (submitted_patch or budget_exhausted or repeated_loop)
    )
    token_by_step, cumulative_token_by_step = token_usage_by_step(
        metrics,
        row.get("history") or [],
    )

    agent = default_agent_metrics()
    agent.update(
        {
            "steps": response_steps,
            "input_tokens": token_totals["input_tokens"],
            "output_tokens": token_totals["output_tokens"],
            "instance_cost": instance_cost,
            "success": run_completed,
            "run_completed": run_completed,
            "step_budget_exhausted": budget_exhausted,
            "repeated_command_loop": repeated_loop,
            "repeated_command": (
                test_result.get("repeated_command")
                if isinstance(test_result, dict)
                else None
            ),
            "consecutive_count": (
                test_result.get("consecutive_count")
                if isinstance(test_result, dict)
                else None
            ),
            "consecutive_command_limit": (
                test_result.get("consecutive_command_limit") if isinstance(test_result, dict) else None
            ),
            "exit_status": "RepeatedCommandLoop" if repeated_loop else None if row.get("error") is None else "error",
            "cached_input_tokens": token_totals["cached_input_tokens"],
            "cache_creation_input_tokens": token_totals["cache_creation_input_tokens"],
            "token_by_step": token_by_step,
            "cumulative_token_by_step": cumulative_token_by_step,
        }
    )
    return agent


def convert_rows(rows: list[dict[str, Any]], model_name: str) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    output_model_name = artifact_model_name(model_name)
    for row in select_canonical_rows(rows):
        patch = extract_patch(row)
        converted.append(
            {
                **prediction_row(
                    model_name_or_path=output_model_name,
                    instance_id=row["instance_id"],
                    model_patch=patch,
                    agent=extract_agent_metrics(row),
                ),
            }
        )
    return converted


def convert_row(row: dict[str, Any], model_name: str) -> dict[str, Any]:
    return convert_rows([row], model_name)[0]


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    write_preds_json(path, rows)


def make_jsonable(value: Any) -> Any:
    """Convert SDK objects to a JSON-safe shape before trajectory export."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): make_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_jsonable(item) for item in value]
    if isinstance(value, set):
        return [make_jsonable(item) for item in sorted(value, key=repr)]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return make_jsonable(model_dump(mode="json"))
        except TypeError:
            try:
                return make_jsonable(model_dump())
            except Exception:
                pass
        except Exception:
            pass

    model_dump_json = getattr(value, "model_dump_json", None)
    if callable(model_dump_json):
        try:
            return make_jsonable(json.loads(model_dump_json()))
        except Exception:
            pass

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return make_jsonable(to_dict())
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        return make_jsonable(vars(value))
    return repr(value)


def sanitize_reasoning_artifacts(value: Any) -> Any:
    """Remove provider reasoning artifacts from data persisted for analysis."""
    if isinstance(value, str):
        if any(marker in value for marker in REASONING_ARTIFACT_MARKERS) or any(
            marker in value for marker in REASONING_ARTIFACT_SUBSTRINGS
        ):
            return REDACTED_REASONING_TEXT
        return value
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in REASONING_ARTIFACT_KEYS or key_text in REASONING_TOKEN_KEYS:
                continue
            sanitized[key_text] = sanitize_reasoning_artifacts(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_reasoning_artifacts(item) for item in value]
    return value


def sanitize_reasoning_log_text(text: str) -> str:
    """Best-effort scrub for reasoning fields in copied OpenHands logs."""
    lines = []
    for line in text.splitlines(keepends=True):
        if any(marker in line for marker in REASONING_ARTIFACT_MARKERS) or any(
            marker in line for marker in REASONING_ARTIFACT_SUBSTRINGS
        ):
            newline = "\n" if line.endswith("\n") else ""
            lines.append(REDACTED_REASONING_TEXT + newline)
        else:
            lines.append(line)
    return "".join(lines)


def scrub_reasoning_log_file(path: Path) -> None:
    try:
        path.write_text(
            sanitize_reasoning_log_text(path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
    except UnicodeDecodeError:
        pass


def write_openhands_trajectories(rows: list[dict[str, Any]], output_dir: Path) -> None:
    for row in select_canonical_rows(rows):
        write_openhands_trajectory(row, output_dir)


def copy_openhands_logs(instance_id: str, output_dir: Path) -> None:
    """Mirror OpenHands centralized per-instance logs into the instance directory."""
    instance_dir = output_dir / instance_id
    instance_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir / "logs"
    log_pairs = (
        (log_dir / f"instance_{instance_id}.log", instance_dir / "openhands.log"),
        (log_dir / f"instance_{instance_id}.output.log", instance_dir / "openhands.output.log"),
    )
    for source, target in log_pairs:
        if source.exists():
            scrub_reasoning_log_file(source)
            shutil.copy2(source, target)
            scrub_reasoning_log_file(target)


def write_openhands_trajectory(row: dict[str, Any], output_dir: Path) -> Path:
    instance_id = row["instance_id"]
    instance_dir = output_dir / instance_id
    agent = extract_agent_metrics(row)
    summary_path = annotate_summary(
        instance_dir,
        framework="openhands",
        instance_id=instance_id,
        agent=agent,
    )
    traj_path = trajectory_path(instance_dir, instance_id)
    write_trajectory(
        traj_path,
        {
            "schema_version": 1,
            "framework": "openhands",
            "instance_id": instance_id,
            "agent": agent,
            "trajectory_format": "openhands-output-row-1",
            "raw_output": sanitize_reasoning_artifacts(make_jsonable(row)),
        },
    )
    copy_openhands_logs(instance_id, output_dir)
    return summary_path


def write_incremental_outputs(
    output_dir: Path,
    row: dict[str, Any],
    model_name: str,
    *,
    lock: Any | None = None,
) -> None:
    prediction = convert_row(row, model_name)
    write_openhands_trajectory(row, output_dir)
    update_prediction_files(
        output_dir,
        prediction,
        lock=lock,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert OpenHands output.jsonl to model_patch predictions."
    )
    parser.add_argument("input", type=Path, help="OpenHands output.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional preds.json output path. Defaults to the JSONL output with .json suffix.",
    )
    parser.add_argument("--model-name", default="openhands")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_rows = read_output_rows(args.input)
    rows = convert_rows(raw_rows, args.model_name)
    payload = prediction_payload(rows)
    output_rows = list(payload["predictions"].values())
    write_jsonl(args.output, output_rows)
    json_output = args.json_output or args.output.with_suffix(".json")
    json_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_openhands_trajectories(raw_rows, json_output.parent)
    nonempty = sum(1 for row in output_rows if row["model_patch"].strip())
    print(f"Wrote {len(output_rows)} predictions to {args.output} ({nonempty} nonempty)")
    print(f"Wrote {len(output_rows)} predictions to {json_output} ({nonempty} nonempty)")


if __name__ == "__main__":
    main()
