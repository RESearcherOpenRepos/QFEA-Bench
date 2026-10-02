#!/usr/bin/env python3
"""Build the current RQ1 table under 100- and 30-step budgets."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
RUN_OVERVIEW = ROOT / "rq" / "rq1" / "results" / "all_runs_overview.csv"
STEP_CAP_SENSITIVITY = ROOT / "rq" / "rq1" / "results" / "step_cap_sensitivity.csv"
SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
ENGINEERING_COMPLEXITY = ROOT / "rq" / "rq2" / "results" / "engineering_complexity.csv"
OUTPUT_DIR = ROOT / "rq" / "rq1" / "results"
STEP_CAPS = (100, 30)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_samples() -> dict[str, dict[str, Any]]:
    samples: dict[str, dict[str, Any]] = {}
    for path in sorted(SAMPLES_DIR.rglob("sample.json")):
        sample = load_json(path)
        instance = sample["instance"]
        metadata = sample.get("metadata", {})
        golden_patch = sample.get("golden_patch", {})
        sample_id = instance["instance_id"]
        samples[sample_id] = {
            "sample_id": sample_id,
            "repo": instance["repo"],
            "quantum_specificity": metadata.get("quantum_depth", "unknown"),
            "oracle_files": set(golden_patch.get("oracle_files", [])),
            "selected_tests": {key: sample["validation"]["patched"][key]["file_list"]
                               for key in ("fail_pass", "pass_pass")},
        }
    return samples


def load_selected_test_counts(run: dict[str, str], samples: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Count the fixed selected testcases, including nonpasses in every denominator."""
    replay_agent = {"mini-swe": "minisweagent"}.get(run["agent"], run["agent"])
    path = ROOT / "rq/rq3/results/casewise_replays" / f"{replay_agent}_{run['run_id']}.json"
    payload = load_json(path)
    replay = {row["instance_id"]: row for row in payload["results"]}
    if payload["summary"].get("pending") or set(replay) != set(samples):
        raise ValueError(f"Incomplete selected-test replay: {path}")
    counts = {}
    for sample_id, sample in samples.items():
        result = replay[sample_id]
        record = {}
        for prefix, suite in (("f2p", "fail_pass"), ("p2p", "pass_pass")):
            selected = sample["selected_tests"][suite]
            cases = result["test_cases"][suite]
            if [case["selector"] for case in cases] != selected or len(set(selected)) != len(selected):
                raise ValueError(f"Selected testcase mismatch: {path}/{sample_id}/{suite}")
            record[f"selected_{prefix}_total"] = len(selected)
            record[f"selected_{prefix}_passed"] = (
                sum(case["status"] == "passed" for case in cases)
                if result.get("patch_applied") else 0
            )
        counts[sample_id] = record
    if tuple(sum(r[f"selected_{s}_total"] for r in counts.values()) for s in ("f2p", "p2p")) != (588, 929):
        raise ValueError("Expected 588 F2P and 929 P2P selectors per setting")
    return counts


def load_oracle_footprint() -> dict[str, dict[str, float]]:
    rows = read_csv(ENGINEERING_COMPLEXITY)
    footprint: dict[str, dict[str, float]] = {}
    for row in rows:
        footprint[row["sample_id"]] = {
            "oracle_lines": float(row["gold_solution_lines"]),
            "oracle_file_count": float(row["gold_solution_files"]),
            "engineering_complexity_score": float(row["engineering_complexity_score"]),
            "engineering_complexity": row["engineering_complexity"],
        }
    return footprint


def load_complete_runs() -> list[dict[str, str]]:
    runs = []
    for row in read_csv(RUN_OVERVIEW):
        if row.get("is_complete") != "True":
            continue
        result_path = ROOT / row["result_path"]
        run_dir = ROOT / row["run_dir"]
        preds_path = run_dir / "preds.jsonl"
        if not result_path.exists() or not preds_path.exists():
            continue
        runs.append(
            {
                "agent": row["agent"],
                "model": row["model"],
                "run_id": row["run_id"],
                "result_path": str(result_path),
                "run_dir": str(run_dir),
                "preds_path": str(preds_path),
            }
        )
    return runs


def load_step_efficiency() -> dict[tuple[str, str, str, int], dict[str, float | None]]:
    metrics: dict[tuple[str, str, str, int], dict[str, float | None]] = {}
    for row in read_csv(RUN_OVERVIEW):
        if row.get("is_complete") != "True":
            continue
        metrics[(row["agent"], row["model"], row["run_id"], 100)] = {
            "avg_steps": as_float(row.get("avg_steps")),
            "avg_tokens": as_float(row.get("avg_total_tokens")),
        }
    for row in read_csv(STEP_CAP_SENSITIVITY):
        if row.get("is_complete") != "True":
            continue
        cap = as_int(row.get("step_cap"))
        if cap not in STEP_CAPS:
            continue
        metrics[(row["agent"], row["model"], row["run_id"], cap)] = {
            "avg_steps": as_float(row.get("avg_capped_steps")),
            "avg_tokens": as_float(row.get("avg_total_tokens_at_cap")),
        }
    return metrics


def load_result_agent(run: dict[str, str], result: dict[str, Any]) -> dict[str, Any]:
    agent = result.get("agent")
    base_agent = agent if isinstance(agent, dict) else {}

    summary_path_value = base_agent.get("summary_path")
    if summary_path_value:
        summary_path = ROOT / str(summary_path_value)
        if summary_path.exists():
            summary_agent = load_json(summary_path).get("agent")
            if isinstance(summary_agent, dict):
                merged = dict(base_agent)
                merged.update(summary_agent)
                return merged

    instance_id = str(result.get("instance_id") or "")
    if instance_id and run.get("run_dir"):
        summary_path = Path(run["run_dir"]) / instance_id / f"{instance_id}.summary.json"
        if summary_path.exists():
            summary_agent = load_json(summary_path).get("agent")
            if isinstance(summary_agent, dict):
                return summary_agent

    return base_agent


def load_results(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    items = data.get("results", [])
    if isinstance(items, dict):
        iterable = items.values()
    else:
        iterable = items
    return {str(item["instance_id"]): item for item in iterable}


def load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    preds: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            preds[str(item["instance_id"])] = item
    return preds


DIFF_GIT_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$")


def parse_patch(patch: str | None) -> dict[str, Any]:
    """Return changed files and changed non-empty line count from a unified diff."""
    if not patch:
        return {
            "agent_files": set(),
            "agent_changed_lines": 0,
            "has_patch_text": False,
        }

    files: set[str] = set()
    changed_lines = 0
    current_file: str | None = None

    for raw_line in patch.splitlines():
        line = raw_line.rstrip("\n")
        match = DIFF_GIT_RE.match(line)
        if match:
            a_path, b_path = match.groups()
            current_file = b_path if b_path != "/dev/null" else a_path
            if current_file and current_file != "/dev/null":
                files.add(current_file)
            continue
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/") :]
            if current_file != "/dev/null":
                files.add(current_file)
            continue
        if line.startswith("--- a/"):
            if current_file is None:
                current_file = line[len("--- a/") :]
                if current_file != "/dev/null":
                    files.add(current_file)
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            if line[1:].strip():
                changed_lines += 1

    return {
        "agent_files": files,
        "agent_changed_lines": changed_lines,
        "has_patch_text": bool(patch.strip()),
    }


def pass_rate(test_summary: dict[str, Any] | None) -> float | None:
    if not isinstance(test_summary, dict):
        return None
    total = test_summary.get("total")
    passed = test_summary.get("passed")
    if total in (None, 0) or passed is None:
        return None
    return float(passed) / float(total)


def test_count(test_summary: dict[str, Any] | None, field: str) -> int | None:
    if not isinstance(test_summary, dict):
        return None
    value = test_summary.get(field)
    return int(value) if value is not None else None


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def mean(values: Iterable[float | None]) -> float | None:
    data = [float(value) for value in values if value is not None and not math.isnan(float(value))]
    if not data:
        return None
    return sum(data) / len(data)


def classify_funnel(row: dict[str, Any]) -> str:
    if row["resolved"]:
        return "Resolved"
    if not row["agent_submitted"]:
        return "No submitted patch"
    if not row["patch_applied"]:
        return "Patch not applied"
    if not row["oracle_hit"]:
        return "No oracle file touched"
    f2p = row["f2p_pass_rate"]
    p2p = row["p2p_pass_rate"]
    if f2p is None:
        return "Evaluation unavailable"
    if f2p == 0:
        return "Oracle touched, no F2P passed"
    if f2p < 1:
        return "Partial F2P"
    if p2p is not None and p2p < 1:
        return "All F2P, P2P regression"
    return "Unresolved despite test pass"


def row_for_instance(
    run: dict[str, str],
    sample: dict[str, Any],
    footprint: dict[str, float],
    result: dict[str, Any],
    pred: dict[str, Any] | None,
    selected_counts: dict[str, int],
) -> dict[str, Any]:
    agent = load_result_agent(run, result)
    patch_info = parse_patch((pred or {}).get("model_patch"))
    agent_files = patch_info["agent_files"]
    oracle_files = sample["oracle_files"]
    intersection = agent_files & oracle_files
    union = agent_files | oracle_files

    oracle_file_count = float(footprint.get("oracle_file_count", len(oracle_files)))
    oracle_lines = float(footprint.get("oracle_lines", 0.0))
    agent_file_count = float(len(agent_files))
    agent_changed_lines = float(patch_info["agent_changed_lines"])

    f2p = pass_rate(result.get("fail_pass"))
    p2p = pass_rate(result.get("pass_pass"))
    row: dict[str, Any] = {
        "agent": run["agent"],
        "model": run["model"],
        "run_id": run["run_id"],
        "sample_id": sample["sample_id"],
        "steps": as_int(agent.get("steps")),
        "repo": sample["repo"],
        "quantum_specificity": sample["quantum_specificity"],
        "engineering_complexity": footprint.get("engineering_complexity"),
        "resolved": bool(result.get("resolved")),
        "agent_submitted": bool(result.get("agent_submitted")),
        "patch_applied": bool(result.get("patch_applied")),
        "has_patch_text": bool(patch_info["has_patch_text"]),
        **selected_counts,
        "f2p_passed": test_count(result.get("fail_pass"), "passed"),
        "f2p_total": test_count(result.get("fail_pass"), "total"),
        "f2p_pass_rate": f2p,
        "p2p_passed": test_count(result.get("pass_pass"), "passed"),
        "p2p_total": test_count(result.get("pass_pass"), "total"),
        "p2p_pass_rate": p2p,
        "oracle_file_count": int(oracle_file_count),
        "agent_file_count": int(agent_file_count),
        "oracle_overlap_count": len(intersection),
        "extra_file_count": len(agent_files - oracle_files),
        "missing_oracle_file_count": len(oracle_files - agent_files),
        "oracle_hit": bool(intersection),
        "oracle_file_recall": safe_ratio(len(intersection), oracle_file_count),
        "oracle_file_precision": safe_ratio(len(intersection), agent_file_count),
        "file_jaccard": safe_ratio(len(intersection), float(len(union))),
        "extra_file_ratio": safe_ratio(len(agent_files - oracle_files), agent_file_count),
        "agent_changed_lines": int(agent_changed_lines),
        "oracle_changed_lines": int(oracle_lines),
        "file_footprint_ratio": safe_ratio(agent_file_count, oracle_file_count),
        "line_footprint_ratio": safe_ratio(agent_changed_lines, oracle_lines),
        "oracle_files": ";".join(sorted(oracle_files)),
        "agent_files": ";".join(sorted(agent_files)),
        "overlap_files": ";".join(sorted(intersection)),
        "extra_files": ";".join(sorted(agent_files - oracle_files)),
        "missing_oracle_files": ";".join(sorted(oracle_files - agent_files)),
    }
    row["funnel_stage"] = classify_funnel(row)
    return row


SETTING_ORDER = {
    ("mini-swe", "gpt-5.5"): 0,
    ("mini-swe", "glm-5.2"): 1,
    ("mini-swe", "gemini-3-flash-preview"): 2,
    ("mini-swe", "deepseek-v4-pro"): 3,
    ("mini-swe", "deepseek-v4-flash"): 4,
    ("openhands", "gpt-5.5"): 5,
    ("openhands", "glm-5.2"): 6,
    ("openhands", "gemini-3-flash-preview"): 7,
    ("openhands", "deepseek-v4-pro"): 8,
    ("openhands", "deepseek-v4-flash"): 9,
    ("autocoderover", "gpt-5.5"): 10,
    ("autocoderover", "glm-5.2"): 11,
    ("autocoderover", "gemini-3-flash-preview"): 12,
    ("autocoderover", "deepseek-v4-pro"): 13,
    ("autocoderover", "deepseek-v4-flash"): 14,
}


def sorted_setting_rows(setting_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        setting_rows,
        key=lambda row: SETTING_ORDER.get((row["agent"], row["model"]), 999),
    )


def aggregate_step_caps(
    rows: list[dict[str, Any]],
    efficiency: dict[tuple[str, str, str, int], dict[str, float | None]],
    caps: tuple[int, ...] = STEP_CAPS,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["agent"], row["model"], row["run_id"])].append(row)

    out: list[dict[str, Any]] = []
    for key, items in groups.items():
        agent, model, run_id = key
        record: dict[str, Any] = {
            "agent": agent,
            "model": model,
            "run_id": run_id,
            "total": len(items),
        }
        for cap in caps:
            cap_efficiency = efficiency.get((agent, model, run_id, cap), {})
            submitted = sum(
                row["agent_submitted"] and 0 < as_int(row.get("steps")) <= cap
                for row in items
            )
            resolved = sum(
                row["resolved"] and 0 < as_int(row.get("steps")) <= cap
                for row in items
            )
            unresolved_at_cap = [
                row for row in items
                if not (row["resolved"] and 0 < as_int(row.get("steps")) <= cap)
            ]

            oracle_file_recall_values: list[float] = []
            applied_within_cap = 0
            for row in unresolved_at_cap:
                has_applied_patch = (
                    0 < as_int(row.get("steps")) <= cap
                    and row["patch_applied"]
                )
                if has_applied_patch:
                    applied_within_cap += 1
                    oracle_file_recall_values.append(float(row["oracle_file_recall"] or 0.0))
                else:
                    oracle_file_recall_values.append(0.0)

            # Pool counts across ALL instances, including resolved instances.
            totals = {suite: sum(row[f"selected_{suite}_total"] for row in items)
                      for suite in ("f2p", "p2p")}
            passed = {suite: sum(row[f"selected_{suite}_passed"] for row in items
                                 if row["agent_submitted"] and 0 < as_int(row.get("steps")) <= cap)
                      for suite in ("f2p", "p2p")}
            record.update(
                {
                    f"{cap}_completed": sum(0 < as_int(row.get("steps")) <= cap for row in items),
                    f"{cap}_submitted": submitted,
                    f"{cap}_submitted_rate": safe_ratio(submitted, len(items)),
                    f"{cap}_resolved": resolved,
                    f"{cap}_resolved_rate": safe_ratio(resolved, len(items)),
                    f"{cap}_avg_steps": cap_efficiency.get("avg_steps"),
                    f"{cap}_avg_tokens": cap_efficiency.get("avg_tokens"),
                    f"{cap}_unresolved": len(unresolved_at_cap),
                    f"{cap}_unresolved_applied": applied_within_cap,
                    f"{cap}_oracle_file_recall": mean(oracle_file_recall_values),
                    f"{cap}_f2p": safe_ratio(passed["f2p"], totals["f2p"]),
                    f"{cap}_p2p": safe_ratio(passed["p2p"], totals["p2p"]),
                    **{f"{cap}_{suite}_{kind}": values[suite]
                       for kind, values in (("passed", passed), ("total", totals))
                       for suite in ("f2p", "p2p")},
                }
            )
        out.append(record)
    return sorted_setting_rows(out)


def main() -> None:
    samples = load_samples()
    footprint = load_oracle_footprint()
    runs = load_complete_runs()
    efficiency = load_step_efficiency()
    rows: list[dict[str, Any]] = []

    for run in runs:
        results = load_results(Path(run["result_path"]))
        preds = load_predictions(Path(run["preds_path"]))
        selected_counts = load_selected_test_counts(run, samples)
        for sample_id, sample in samples.items():
            if sample_id not in results:
                continue
            rows.append(
                row_for_instance(
                    run=run,
                    sample=sample,
                    footprint=footprint.get(sample_id, {}),
                    result=results[sample_id],
                    pred=preds.get(sample_id),
                    selected_counts=selected_counts[sample_id],
                )
            )

    step_cap_rows = aggregate_step_caps(rows, efficiency)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "rq1_step_cap_main_table.csv", step_cap_rows)

    print(f"Wrote {len(rows)} setting-instance rows for {len(runs)} complete runs.")
    print(f"Outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
