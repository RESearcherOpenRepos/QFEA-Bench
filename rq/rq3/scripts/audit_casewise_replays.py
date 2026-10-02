#!/usr/bin/env python3
"""Check coverage and exceptional outcomes in all structured agent replays."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPLAYS = ROOT / "rq/rq3/results/casewise_replays"
OUTPUT = ROOT / "rq/rq3/results/summary/casewise_replay_quality.csv"
AGENTS = ("minisweagent", "autocoderover", "openhands")
SPLITS = ("fail_pass", "pass_pass")


def main() -> None:
    indexed = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())["samples"]
    from summarize_structured_constraint_passes import selected_test_count, selected_replays
    rows = []
    for agent in AGENTS:
        for replay in selected_replays(agent):
            run = replay.stem.removeprefix(agent + "_")
            data = json.loads(replay.read_text())
            results = data["results"]
            if len(results) != len(indexed) or data["summary"]["pending"]:
                raise ValueError(f"Incomplete replay: {replay}")
            counts = Counter()
            cases = 0
            for result in results:
                if result.get("eval_infra_failed"):
                    counts["infra_samples"] += 1
                if result.get("timed_out"):
                    counts["timed_out_samples"] += 1
                for split in SPLITS:
                    suite = result[split]
                    selected = result["test_cases"][split]
                    cases += len(selected)
                    if suite["total"] != len(selected) or suite["passed"] != sum(
                        case["status"] == "passed" for case in selected
                    ):
                        raise ValueError(f"Case/suite count mismatch: {agent}/{run}/{result['instance_id']}/{split}")
                    if suite.get("report_missing"):
                        counts["missing_reports"] += 1
                    counts["unmatched_report_items"] += len(suite.get("unmatched_report_nodeids", []))
                    for case in selected:
                        counts[case["status"]] += 1
                        if suite.get("pytest_exit_code") == 0 and case["status"] != "passed":
                            counts["exit_zero_nonpasses"] += 1
            if cases != selected_test_count():
                raise ValueError(f"Expected selected-test inventory: {replay}; got {cases}")
            rows.append({
                "agent": agent, "run": run, "samples": len(results), "testcases": cases,
                "resolved": data["summary"]["resolved"],
                **{key: counts[key] for key in (
                    "passed", "failed", "skipped", "not_collected", "not_run",
                    "infra_samples", "timed_out_samples", "missing_reports", "unmatched_report_items",
                    "exit_zero_nonpasses",
                )},
            })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
