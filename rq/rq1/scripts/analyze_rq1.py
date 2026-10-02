#!/usr/bin/env python3
"""Generate CSV data for RQ1 agent/model outcomes and step-budget sensitivity."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.common.model_pricing import (
    estimated_cost_usd,
    pricing_for_model,
)

DEFAULT_OUTPUT_DIR = ROOT / "rq" / "rq1" / "results"
DEFAULT_STEP_CAPS = (50, 40, 30)
DEFAULT_TOTAL_EXPECTED = 106


@dataclass(frozen=True)
class RunSpec:
    agent: str
    model: str
    run_id: str
    result_path: Path
    run_dir: Path | None = None
    note: str = ""


DEFAULT_RUNS = (
    RunSpec(
        agent="mini-swe",
        model="deepseek-v4-flash",
        run_id="deepseek_v4_flash_20260602",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_deepseek_v4_flash_20260602.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "deepseek_v4_flash_20260602",
    ),
    RunSpec(
        agent="mini-swe",
        model="deepseek-v4-pro",
        run_id="deepseek_v4_pro_20260602",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_deepseek_v4_pro_20260602.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "deepseek_v4_pro_20260602",
    ),
    RunSpec(
        agent="mini-swe",
        model="gemini-3-flash-preview",
        run_id="gemini_3_flash_20260604",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_gemini_3_flash_20260604.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "gemini_3_flash_20260604",
        note="old custom Vertex adapter",
    ),
    RunSpec(
        agent="mini-swe",
        model="gemini-3-flash-preview",
        run_id="gemini3_flash_20260605",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_gemini3_flash_20260605.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "gemini3flash_20260604",
        note="newer rerun",
    ),
    RunSpec(
        agent="mini-swe",
        model="gemini-3-pro",
        run_id="gemini3pro_20260604",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_gemini3pro_20260604.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "gemini3pro_20260604",
    ),
    RunSpec(
        agent="mini-swe",
        model="glm5",
        run_id="glm5_20260604",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_glm5_20260604.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "glm5_20260604",
        note="incomplete run",
    ),
    RunSpec(
        agent="mini-swe",
        model="glm-5.2",
        run_id="glm5_2_20260626",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_glm5_2_20260626.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "glm5_2_20260626",
    ),
    RunSpec(
        agent="mini-swe",
        model="gpt-5.5",
        run_id="gpt55_20260604",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_gpt55_20260604.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "runs"
        / "gpt55_20260604",
    ),
    RunSpec(
        agent="openhands",
        model="deepseek-v4-flash",
        run_id="deepseek_v4_flash_20260608",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "results"
        / "results_deepseek_v4_flash_20260608.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "runs"
        / "deepseek_v4_flash_20260608",
    ),
    RunSpec(
        agent="openhands",
        model="deepseek-v4-pro",
        run_id="deepseek_v4_pro_20260608",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "results"
        / "results_deepseek_v4_pro_20260608.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "runs"
        / "deepseek_v4_pro_20260608",
    ),
    RunSpec(
        agent="openhands",
        model="gemini-3-flash-preview",
        run_id="gemini3_flash_20260606",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "results"
        / "results_gemini3_flash_20260606.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "runs"
        / "gemini3_flash_20260606",
    ),
    RunSpec(
        agent="openhands",
        model="glm-5.2",
        run_id="glm5_2_20260627",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "results"
        / "results_glm5_2_20260628.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "runs"
        / "glm5_2_20260627",
    ),
    RunSpec(
        agent="openhands",
        model="gpt-5.5",
        run_id="gpt55_20260625",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "results"
        / "results_gpt55_20260625.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "openhands"
        / "runs"
        / "gpt55_20260625",
    ),
    RunSpec(
        agent="autocoderover",
        model="gpt-5.5",
        run_id="gpt55_20260625",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "results"
        / "results_gpt55_20260625.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "runs"
        / "gpt55_20260625",
    ),
    RunSpec(
        agent="autocoderover",
        model="deepseek-v4-flash",
        run_id="deepseek_v4_flash_20260609",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "results"
        / "results_deepseek_v4_flash_20260609.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "runs"
        / "deepseek_v4_flash_20260609",
        note="partial run",
    ),
    RunSpec(
        agent="autocoderover",
        model="deepseek-v4-pro",
        run_id="deepseek_v4_pro_20260610",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "results"
        / "results_deepseek_v4_pro_20260610.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "runs"
        / "deepseek_v4_pro_20260610",
    ),
    RunSpec(
        agent="autocoderover",
        model="gemini-3-flash-preview",
        run_id="gemini3_flash_20260609",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "results"
        / "results_gemini3_flash_20260609.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "runs"
        / "gemini3_flash_20260609",
    ),
    RunSpec(
        agent="autocoderover",
        model="glm-5.2",
        run_id="glm5_2_openrouter_20260628",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "results"
        / "results_glm5_2_openrouter_20260628.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "autocoderover"
        / "runs"
        / "glm5_2_openrouter_20260628",
    ),
    RunSpec(
        agent="trae",
        model="gpt-5.5",
        run_id="gpt55_20260604",
        result_path=ROOT
        / "benchmark"
        / "evaluation"
        / "traeagent"
        / "results"
        / "results_gpt55_20260604.json",
        run_dir=ROOT
        / "benchmark"
        / "evaluation"
        / "traeagent"
        / "runs"
        / "gpt55_20260604",
        note="metrics recovered from per-instance summaries",
    ),
)


TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_creation_input_tokens",
    "output_tokens",
)


# Keep the original trajectories, but use the reconciled selected-test outcomes
# throughout RQ1--RQ4 once all 15 corrected settings have been published.
HISTORICAL_RUNS = DEFAULT_RUNS
_CORRECTED = ROOT / "rq/rq1/results/corrected_evaluations"
DEFAULT_RUNS = tuple(
    replace(spec, result_path=_CORRECTED / f"{spec.agent}_{spec.run_id}.json")
    if (_CORRECTED / "manifest.json").exists() and spec.result_path.exists() else spec
    for spec in HISTORICAL_RUNS
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def result_items(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    results = payload.get("results", [])
    if isinstance(results, dict):
        return list(results.values())
    return list(results)


def result_summary(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: list[float]) -> str:
    if not values:
        return ""
    return f"{statistics.fmean(values):.3f}"


def rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return ""
    return f"{numerator / denominator:.6f}"


def load_summary_agent(spec: RunSpec, item: dict[str, Any]) -> dict[str, Any]:
    agent = item.get("agent")
    if isinstance(agent, dict) and agent.get("summary_path"):
        summary_path = ROOT / str(agent["summary_path"])
        if summary_path.exists():
            summary_agent = load_json(summary_path).get("agent")
            if isinstance(summary_agent, dict):
                merged = dict(agent)
                merged.update(summary_agent)
                return merged

    instance_id = str(item.get("instance_id") or "")
    if spec.run_dir and instance_id:
        summary_path = spec.run_dir / instance_id / f"{instance_id}.summary.json"
        if summary_path.exists():
            summary_agent = load_json(summary_path).get("agent")
            if isinstance(summary_agent, dict):
                return summary_agent

    return agent if isinstance(agent, dict) else {}


def item_submitted(item: dict[str, Any], agent: dict[str, Any]) -> bool:
    if "agent_submitted" in item:
        return bool(item.get("agent_submitted"))
    return bool(agent.get("exit_status") == "Submitted" or item.get("patch_applied"))


def item_step_exhausted(item: dict[str, Any], agent: dict[str, Any]) -> bool:
    return bool(item.get("agent_step_exhausted") or agent.get("step_budget_exhausted"))


def item_repeated_loop(item: dict[str, Any], agent: dict[str, Any]) -> bool:
    return bool(item.get("agent_repeated_command_loop") or agent.get("repeated_command_loop"))


def agent_has_metrics(agent: dict[str, Any]) -> bool:
    return any(
        as_int(agent.get(key)) > 0
        for key in ("steps", "input_tokens", "cached_input_tokens", "output_tokens")
    )


def token_total(metrics: dict[str, Any]) -> int:
    return (
        as_int(metrics.get("input_tokens"))
        + as_int(metrics.get("cache_creation_input_tokens"))
        + as_int(metrics.get("output_tokens"))
    )


def format_cost(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def cumulative_at_cap(agent: dict[str, Any], cap: int) -> tuple[dict[str, int], bool]:
    records = agent.get("cumulative_token_by_step")
    if isinstance(records, list) and records:
        selected = None
        for record in records:
            if as_int(record.get("step")) <= cap:
                selected = record
            else:
                break
        if selected is not None:
            return {key: as_int(selected.get(key)) for key in TOKEN_KEYS}, True

    steps = as_int(agent.get("steps"))
    if steps and steps <= cap:
        return {key: as_int(agent.get(key)) for key in TOKEN_KEYS}, True

    return {key: 0 for key in TOKEN_KEYS}, False


def enriched_rows(spec: RunSpec, *, summary_agents: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = []
    for item in result_items(spec.result_path):
        agent = (summary_agents[item["instance_id"]] if summary_agents is not None
                 else load_summary_agent(spec, item))
        rows.append(
            {
                "item": item,
                "agent": agent,
                "resolved": bool(item.get("resolved")),
                "submitted": item_submitted(item, agent),
                "patch_applied": bool(item.get("patch_applied")),
                "timed_out": bool(item.get("timed_out")),
                "step_exhausted": item_step_exhausted(item, agent),
                "repeated_command_loop": item_repeated_loop(item, agent),
                "metrics_known": agent_has_metrics(agent),
                "steps": as_int(agent.get("steps")),
                **{key: as_int(agent.get(key)) for key in TOKEN_KEYS},
            }
        )
    return rows


def summarize_overall(spec: RunSpec) -> dict[str, Any]:
    rows = enriched_rows(spec)
    total = len(rows)
    total_expected = DEFAULT_TOTAL_EXPECTED
    resolved = sum(row["resolved"] for row in rows)
    submitted = sum(row["submitted"] for row in rows)
    patch_applied = sum(row["patch_applied"] for row in rows)
    metrics_rows = [row for row in rows if row["metrics_known"]]
    summary = result_summary(spec.result_path)
    pricing = pricing_for_model(spec.model)
    total_metrics = {
        "input_tokens": sum(row["input_tokens"] for row in metrics_rows),
        "cached_input_tokens": sum(row["cached_input_tokens"] for row in metrics_rows),
        "cache_creation_input_tokens": sum(
            row["cache_creation_input_tokens"] for row in metrics_rows
        ),
        "output_tokens": sum(row["output_tokens"] for row in metrics_rows),
    }
    fallback_total_cost = estimated_cost_usd(spec.model, total_metrics) if metrics_rows else None
    total_cost = optional_float(summary.get("total_cost"))
    if total_cost is None:
        total_cost = fallback_total_cost
    avg_cost = optional_float(summary.get("avg_cost"))
    if avg_cost is None and total_cost is not None and metrics_rows:
        avg_cost = total_cost / len(metrics_rows)

    return {
        "agent": spec.agent,
        "model": spec.model,
        "run_id": spec.run_id,
        "result_path": rel(spec.result_path),
        "run_dir": rel(spec.run_dir),
        "note": spec.note,
        "total": total,
        "total_expected": total_expected,
        "is_complete": total == total_expected,
        "resolved": resolved,
        "resolve_rate": rate(resolved, total_expected),
        "observed_resolve_rate": rate(resolved, total),
        "submitted": submitted,
        "submit_rate": rate(submitted, total),
        "patch_applied": patch_applied,
        "patch_apply_rate": rate(patch_applied, total),
        "timed_out": sum(row["timed_out"] for row in rows),
        "step_exhausted": sum(row["step_exhausted"] for row in rows),
        "repeated_command_loop": sum(row["repeated_command_loop"] for row in rows),
        "metrics_known": len(metrics_rows),
        "input_usd_per_million": pricing.input_usd_per_million if pricing else "",
        "cached_input_usd_per_million": (
            pricing.cached_input_usd_per_million if pricing else ""
        ),
        "cache_creation_input_usd_per_million": (
            pricing.input_usd_per_million if pricing else ""
        ),
        "output_usd_per_million": pricing.output_usd_per_million if pricing else "",
        "total_cost": format_cost(total_cost),
        "avg_cost": format_cost(avg_cost),
        "cost_per_resolved_usd": format_cost(
            total_cost / resolved if total_cost is not None and resolved else None
        ),
        "avg_steps": mean([row["steps"] for row in metrics_rows]),
        "median_steps": (
            statistics.median([row["steps"] for row in metrics_rows]) if metrics_rows else ""
        ),
        "total_steps": sum(row["steps"] for row in metrics_rows),
        "avg_input_tokens": mean([row["input_tokens"] for row in metrics_rows]),
        "avg_cached_input_tokens": mean([row["cached_input_tokens"] for row in metrics_rows]),
        "avg_cache_creation_input_tokens": mean(
            [row["cache_creation_input_tokens"] for row in metrics_rows]
        ),
        "avg_output_tokens": mean([row["output_tokens"] for row in metrics_rows]),
        "avg_total_tokens": mean([token_total(row) for row in metrics_rows]),
        "total_input_tokens": total_metrics["input_tokens"],
        "total_cached_input_tokens": total_metrics["cached_input_tokens"],
        "total_cache_creation_input_tokens": total_metrics["cache_creation_input_tokens"],
        "total_output_tokens": total_metrics["output_tokens"],
    }


def summarize_cap(spec: RunSpec, cap: int) -> dict[str, Any]:
    rows = enriched_rows(spec)
    total = len(rows)
    total_expected = DEFAULT_TOTAL_EXPECTED
    metrics_rows = [row for row in rows if row["metrics_known"]]
    solved = sum(row["resolved"] and row["steps"] <= cap for row in metrics_rows)
    completed_within_cap = sum(row["steps"] <= cap for row in metrics_rows)
    capped_steps = [min(row["steps"], cap) for row in metrics_rows]

    token_rows = []
    for row in metrics_rows:
        capped_tokens, known = cumulative_at_cap(row["agent"], cap)
        if known:
            token_rows.append(capped_tokens)
    total_cap_metrics = {
        "input_tokens": sum(row["input_tokens"] for row in token_rows),
        "cached_input_tokens": sum(row["cached_input_tokens"] for row in token_rows),
        "cache_creation_input_tokens": sum(
            row["cache_creation_input_tokens"] for row in token_rows
        ),
        "output_tokens": sum(row["output_tokens"] for row in token_rows),
    }
    estimated_cap_cost = estimated_cost_usd(spec.model, total_cap_metrics) if token_rows else None

    return {
        "agent": spec.agent,
        "model": spec.model,
        "run_id": spec.run_id,
        "step_cap": cap,
        "total": total,
        "total_expected": total_expected,
        "is_complete": total == total_expected,
        "metrics_known": len(metrics_rows),
        "resolved_at_cap": solved,
        "resolve_rate_at_cap": rate(solved, total_expected),
        "observed_resolve_rate_at_cap": rate(solved, total),
        "completed_within_cap": completed_within_cap,
        "completed_within_cap_rate": rate(completed_within_cap, len(metrics_rows)),
        "avg_capped_steps": mean(capped_steps),
        "total_capped_steps": sum(capped_steps),
        "token_metrics_known": len(token_rows),
        "avg_input_tokens_at_cap": mean([row["input_tokens"] for row in token_rows]),
        "avg_cached_input_tokens_at_cap": mean(
            [row["cached_input_tokens"] for row in token_rows]
        ),
        "avg_cache_creation_input_tokens_at_cap": mean(
            [row["cache_creation_input_tokens"] for row in token_rows]
        ),
        "avg_output_tokens_at_cap": mean([row["output_tokens"] for row in token_rows]),
        "avg_total_tokens_at_cap": mean([token_total(row) for row in token_rows]),
        "estimated_cost_at_cap_usd": format_cost(estimated_cap_cost),
        "avg_cost_at_cap_usd": format_cost(
            estimated_cap_cost / len(token_rows)
            if estimated_cap_cost is not None and token_rows
            else None
        ),
        "total_input_tokens_at_cap": total_cap_metrics["input_tokens"],
        "total_cached_input_tokens_at_cap": total_cap_metrics["cached_input_tokens"],
        "total_cache_creation_input_tokens_at_cap": total_cap_metrics[
            "cache_creation_input_tokens"
        ],
        "total_output_tokens_at_cap": total_cap_metrics["output_tokens"],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def format_percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return ""
    return f"{numerator / denominator * 100:.1f}%"


def format_resolved(count: Any, denominator: Any) -> str:
    count_int = as_int(count)
    denominator_int = as_int(denominator)
    return f"{count_int} ({format_percent(count_int, denominator_int)})"


def format_decimal(value: Any) -> str:
    if value == "":
        return ""
    return f"{as_float(value):.2f}"


def format_token(value: Any) -> str:
    if value == "":
        return ""
    return f"{round(as_float(value)):,}"


def format_usd(value: Any) -> str:
    if value == "":
        return ""
    return f"{as_float(value):.2f}"


def display_agent(agent: str) -> str:
    return {
        "autocoderover": "AutoCodeRover",
        "mini-swe": "Mini-SWE-Agent",
        "openhands": "OpenHands",
        "trae": "Trae-Agent",
    }.get(agent, agent)


def display_llm(row: dict[str, Any]) -> str:
    return str(row["model"])


def row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row["agent"]), str(row["model"]), str(row["run_id"]))


def complete_table_rows(
    overall: list[dict[str, Any]],
    caps: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    cap_lookup = {
        (*row_key(row), as_int(row["step_cap"])): row
        for row in caps
    }
    complete = []
    excluded = []
    for row in overall:
        total_expected = as_int(row["total_expected"])
        cap_rows = [cap_lookup.get((*row_key(row), cap)) for cap in (50, 40, 30)]
        has_full_metrics = as_int(row["metrics_known"]) == total_expected
        if row["is_complete"] and has_full_metrics:
            complete.append(row)
        else:
            excluded.append(
                (
                    row,
                    row["is_complete"],
                    as_int(row["metrics_known"]),
                    [
                        as_int(cap_row["token_metrics_known"]) if cap_row else 0
                        for cap_row in cap_rows
                    ],
                )
            )

    table_rows = []
    for row in sorted(complete, key=lambda r: (r["agent"], r["model"], r["run_id"])):
        table_row = {
            "Agent": display_agent(str(row["agent"])),
            "LLM": display_llm(row),
            "100 Resolved (%)": format_resolved(row["resolved"], row["total_expected"]),
            "100 Avg. # Token": format_token(row["avg_total_tokens"]),
            "100 Avg. Step": format_decimal(row["avg_steps"]),
            "Total Cost (USD)": format_usd(row["total_cost"]),
            "Avg Cost (USD)": format_usd(row["avg_cost"]),
        }
        for cap in (50, 40, 30):
            cap_row = cap_lookup.get((*row_key(row), cap), {})
            table_row[f"{cap} Resolved (%)"] = format_resolved(
                cap_row.get("resolved_at_cap"), row["total_expected"]
            )
            table_row[f"{cap} Avg. # Token"] = format_token(
                cap_row.get("avg_total_tokens_at_cap", "")
            )
            table_row[f"{cap} Avg. Step"] = format_decimal(
                cap_row.get("avg_capped_steps", "")
            )
        table_rows.append(table_row)

    coverage_notes = []
    for row, is_complete, metrics_known, cap_token_known in excluded:
        total_expected = as_int(row["total_expected"])
        cap_note = ", ".join(
            f"{cap}: {known}/{total_expected}"
            for cap, known in zip((50, 40, 30), cap_token_known)
        )
        coverage_notes.append(
            f"- Excluded {display_agent(str(row['agent']))} / {display_llm(row)}: "
            f"`complete_result={is_complete}`, "
            f"overall resolved {format_resolved(row['resolved'], row['total_expected'])}, "
            f"average tokens {format_token(row['avg_total_tokens'])}, "
            f"average steps {format_decimal(row['avg_steps'])}; "
            f"overall metric coverage {metrics_known}/{total_expected}; "
            f"token metric coverage under step caps ({cap_note})."
        )

    return table_rows, coverage_notes


def write_complete_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    write_csv(path, rows)


def cost_summary_rows(overall: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(overall, key=lambda item: (item["agent"], item["model"], item["run_id"])):
        if row["total_cost"] == "":
            continue
        rows.append(
            {
                "Agent": display_agent(str(row["agent"])),
                "LLM": display_llm(row),
                "run_id": row["run_id"],
                "scope": f"{row['total']}/{row['total_expected']}",
                "complete_result": row["is_complete"],
                "metrics_known": row["metrics_known"],
                "submitted": row["submitted"],
                "patch_applied": row["patch_applied"],
                "resolved": row["resolved"],
                "resolved_rate": row["resolve_rate"],
                "total_input_tokens": row["total_input_tokens"],
                "total_cached_input_tokens": row["total_cached_input_tokens"],
                "total_cache_creation_input_tokens": row[
                    "total_cache_creation_input_tokens"
                ],
                "total_output_tokens": row["total_output_tokens"],
                "input_usd_per_million": row["input_usd_per_million"],
                "cached_input_usd_per_million": row["cached_input_usd_per_million"],
                "cache_creation_input_usd_per_million": row[
                    "cache_creation_input_usd_per_million"
                ],
                "output_usd_per_million": row["output_usd_per_million"],
                "total_cost": row["total_cost"],
                "avg_cost": row["avg_cost"],
                "cost_per_resolved_usd": row["cost_per_resolved_usd"],
                "note": row["note"],
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--step-caps",
        default=",".join(str(value) for value in DEFAULT_STEP_CAPS),
        help="Comma-separated step caps to simulate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    caps = [int(value) for value in args.step_caps.split(",") if value.strip()]
    runs = [spec for spec in DEFAULT_RUNS if spec.result_path.exists()]
    overall_rows = [summarize_overall(spec) for spec in runs]
    cap_rows = [summarize_cap(spec, cap) for spec in runs for cap in caps]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "all_runs_overview.csv", overall_rows)
    write_csv(args.output_dir / "step_cap_sensitivity.csv", cap_rows)
    write_csv(args.output_dir / "cost_summary.csv", cost_summary_rows(overall_rows))
    print(f"Wrote all-run CSV to {args.output_dir / 'all_runs_overview.csv'}")
    print(f"Wrote step-cap CSV to {args.output_dir / 'step_cap_sensitivity.csv'}")
    print(f"Wrote cost-summary CSV to {args.output_dir / 'cost_summary.csv'}")


if __name__ == "__main__":
    main()
