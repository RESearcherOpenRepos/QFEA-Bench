#!/usr/bin/env python3
"""Compare official sample resolution by presence of quantum-semantic F2P tests.

The robustness output keeps the indexed samples as the units of comparison. Each
sample contributes one outcome per official Agent--LLM setting; repeated runs
of the same sample are not treated as independent samples in the bootstrap.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from summarize_structured_constraint_passes import load_annotation_rows
from random import Random


ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "rq/rq1/results/current/all_runs_overview.csv"
SPECIFICITY = ROOT / "rq/rq2/results/current/engineering_complexity.csv"
OUTPUT = ROOT / "rq/rq3/results/summary/sample_resolution_by_f2p_quantum_constraint.csv"
ROBUSTNESS_OUTPUT = ROOT / "rq/rq3/results/summary/sample_resolution_robustness.csv"
BOOTSTRAP_OUTPUT = ROOT / "rq/rq3/results/summary/sample_resolution_gap_bootstrap.csv"
AGENTS = ("mini-swe", "openhands", "autocoderover")
BOOTSTRAP_REPLICATES = 20_000


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def main() -> None:
    selected = load_annotation_rows()
    sample_ids = {row["sample_id"] for row in selected}
    quantum_f2p = {
        row["sample_id"]
        for row in selected
        if row["split"] == "F2P" and row["category"] == "quantum_semantics"
    }
    if not quantum_f2p or not quantum_f2p < sample_ids:
        raise ValueError("Reference test inventory has changed")
    f2p_counts = Counter(row["sample_id"] for row in selected if row["split"] == "F2P")
    if set(f2p_counts) != sample_ids:
        raise ValueError("Every sample must have selected F2P tests")

    metadata = {row["sample_id"]: row for row in read_csv(SPECIFICITY)}
    if set(metadata) != sample_ids:
        raise ValueError("Quantum-specificity inventory does not match the benchmark")

    runs = read_csv(RUNS)
    if len(runs) != 15:
        raise ValueError(f"Expected 15 official agent-LLM settings, got {len(runs)}")
    outcomes: dict[str, list[tuple[str, dict[str, dict[str, bool]]]]] = defaultdict(list)
    for run in runs:
        path = ROOT / run["result_path"]
        result = json.loads(path.read_text())
        by_sample = {
            item["instance_id"]: {
                "resolved": item["resolved"],
                # Non-submitted runs store null here; only an explicit true
                # counts as an applied patch in the official overview.
                "patch_applied": item["patch_applied"] is True,
            }
            for item in result["results"]
        }
        if any(type(item["resolved"]) is not bool or item["patch_applied"] not in (True, False, None)
               for item in result["results"]):
            raise ValueError(f"Non-Boolean official outcomes: {run['run_id']}")
        if (
            set(by_sample) != sample_ids
            or sum(value["resolved"] for value in by_sample.values()) != int(run["resolved"])
            or sum(value["patch_applied"] for value in by_sample.values()) != int(run["patch_applied"])
            or any(value["resolved"] and not value["patch_applied"] for value in by_sample.values())
        ):
            raise ValueError(f"Official run disagrees with its overview: {run['run_id']}")
        outcomes[run["agent"]].append((run["run_id"], by_sample))
    if set(outcomes) != set(AGENTS) or any(len(outcomes[agent]) != 5 for agent in AGENTS):
        raise ValueError("Expected five official LLM runs per agent")

    summary: list[dict[str, object]] = []
    robustness: list[dict[str, object]] = []
    bootstrap: list[dict[str, object]] = []
    for agent in (*AGENTS, "all_agents"):
        agent_runs = (
            [run for agent_name in AGENTS for run in outcomes[agent_name]]
            if agent == "all_agents" else outcomes[agent]
        )
        strata = [("overall", "all", sample_ids)]
        strata += [
            ("engineering_complexity", level, {
                sample_id for sample_id in sample_ids
                if metadata[sample_id]["engineering_complexity"] == level
            })
            for level in ("small", "medium", "large")
        ]
        strata += [
            ("f2p_test_count", label, {
                sample_id for sample_id in sample_ids
                if lower <= f2p_counts[sample_id] <= upper
            })
            for label, lower, upper in (("1-2", 1, 2), ("3-5", 3, 5), ("6+", 6, 10**9))
        ]
        strata += [
            ("repository", repo, {
                sample_id for sample_id in sample_ids
                if metadata[sample_id]["repo"] == repo
            })
            for repo in sorted({metadata[sample_id]["repo"] for sample_id in sample_ids})
        ]
        strata += [("repository_sensitivity", "exclude_qiskit_nature", {
            sample_id for sample_id in sample_ids
            if metadata[sample_id]["repo"] != "qiskit-community/qiskit-nature"
        })]
        strata += [
            ("quantum_specificity", level, {
                sample_id for sample_id in sample_ids
                if metadata[sample_id]["quantum_depth"] == level
            })
            for level in ("medium", "strong")
        ]

        for kind, stratum, members in strata:
            for has_quantum_f2p in (True, False):
                samples = sorted(
                    sample_id for sample_id in members
                    if (sample_id in quantum_f2p) == has_quantum_f2p
                )
                resolved = sum(
                    outcome[sample_id]["resolved"]
                    for _, outcome in agent_runs for sample_id in samples
                )
                applied = sum(
                    outcome[sample_id]["patch_applied"]
                    for _, outcome in agent_runs for sample_id in samples
                )
                total = len(samples) * len(agent_runs)
                robustness.append({
                    "agent": agent,
                    "stratum_type": kind,
                    "stratum": stratum,
                    "has_quantum_semantic_f2p": str(has_quantum_f2p).lower(),
                    "samples": len(samples),
                    "task_runs": total,
                    "resolved": resolved,
                    "resolved_rate": f"{resolved / total:.6f}" if total else "",
                    "patch_applied": applied,
                    "patch_applied_rate": f"{applied / total:.6f}" if total else "",
                    "resolved_given_applied": f"{resolved / applied:.6f}" if applied else "",
                })

        for depth in ("all", "medium", "strong"):
            for has_quantum_f2p in (True, False):
                samples = sorted(
                    sample_id for sample_id in sample_ids
                    if (sample_id in quantum_f2p) == has_quantum_f2p
                    and (depth == "all" or metadata[sample_id]["quantum_depth"] == depth)
                )
                resolved = sum(
                    outcome[sample_id]["resolved"]
                    for _, outcome in agent_runs for sample_id in samples
                )
                total = len(samples) * len(agent_runs)
                never_resolved = sum(
                    not any(outcome[sample_id]["resolved"] for _, outcome in agent_runs)
                    for sample_id in samples
                )
                summary.append({
                    "agent": agent,
                    "quantum_specificity": depth,
                    "has_quantum_semantic_f2p": str(has_quantum_f2p).lower(),
                    "samples": len(samples),
                    "agent_llm_runs": len(agent_runs),
                    "resolved": resolved,
                    "total": total,
                    "resolved_rate": f"{resolved / total:.6f}" if total else "",
                    "never_resolved_samples": never_resolved,
                })

        per_sample_rate = {
            sample_id: sum(outcome[sample_id]["resolved"] for _, outcome in agent_runs)
            / len(agent_runs)
            for sample_id in sample_ids
        }
        quantum_rates = [per_sample_rate[sample_id] for sample_id in sorted(quantum_f2p)]
        other_rates = [per_sample_rate[sample_id] for sample_id in sorted(sample_ids - quantum_f2p)]
        gap = sum(other_rates) / len(other_rates) - sum(quantum_rates) / len(quantum_rates)
        random = Random(20260925)
        draws = [
            sum(random.choices(other_rates, k=len(other_rates))) / len(other_rates)
            - sum(random.choices(quantum_rates, k=len(quantum_rates))) / len(quantum_rates)
            for _ in range(BOOTSTRAP_REPLICATES)
        ]
        bootstrap.append({
            "agent": agent,
            "quantum_f2p_samples": len(quantum_rates),
            "other_samples": len(other_rates),
            "gap_other_minus_quantum": f"{gap:.6f}",
            "ci_95_lower": f"{percentile(draws, 0.025):.6f}",
            "ci_95_upper": f"{percentile(draws, 0.975):.6f}",
            "resampling_unit": "sample_within_group",
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "seed": 20260925,
        })

    write_csv(OUTPUT, summary)
    write_csv(ROBUSTNESS_OUTPUT, robustness)
    write_csv(BOOTSTRAP_OUTPUT, bootstrap)
    for path in (OUTPUT, ROBUSTNESS_OUTPUT, BOOTSTRAP_OUTPUT):
        print(path)


if __name__ == "__main__":
    main()
