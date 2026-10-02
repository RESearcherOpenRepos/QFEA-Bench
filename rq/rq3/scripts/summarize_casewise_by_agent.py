#!/usr/bin/env python3
"""Pool exact selected-test outcomes across five LLM runs for each agent."""

from __future__ import annotations

import csv
from collections import Counter
from summarize_structured_constraint_passes import selected_test_count, selected_replays

from pathlib import Path

from summarize_structured_constraint_passes import load_test_rows, load_annotation_rows


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "rq/rq3/results/summary"
REPLAYS = ROOT / "rq/rq3/results/casewise_replays"
AGENTS = ("minisweagent", "autocoderover", "openhands")
CATEGORIES = ("general_semantics", "quantum_semantics", "interface")
SPLITS = ("F2P", "P2P")
STATUSES = ("passed", "failed", "skipped", "not_collected", "not_run")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict[str, str]], *, agent: str, run: str = "all_five_llms") -> list[dict[str, object]]:
    output = []
    for split in SPLITS:
        for category in CATEGORIES:
            selected = [row for row in rows if row["split"] == split and row["category"] == category]
            counts = Counter(row["status"] for row in selected)
            unknown = set(counts) - set(STATUSES)
            if unknown:
                raise ValueError(f"Unexpected testcase statuses: {sorted(unknown)}")
            output.append({
                "agent": agent,
                "run": run,
                "split": split,
                "category": category,
                **{status: counts[status] for status in STATUSES},
                "total": len(selected),
                "pass_rate_all_selected": f"{counts['passed'] / len(selected):.6f}",
            })
    return output


def main() -> None:
    by_agent = []
    by_run = []
    for agent in AGENTS:
        all_rows = []
        for detail_path in selected_replays(agent):
            run = detail_path.stem.removeprefix(agent + "_")
            rows = load_test_rows(detail_path, agent, run)
            if len(rows) != selected_test_count() or len({(row["sample_id"], row["split"], row["selector"]) for row in rows}) != selected_test_count():
                raise ValueError(f"Expected the current distinct selected test inventory: {detail_path}")
            all_rows.extend(rows)
            by_run.extend(aggregate(rows, agent=agent, run=run))
        by_agent.extend(aggregate(all_rows, agent=agent))
    write_csv(RESULTS / "constraint_passes_casewise_by_agent.csv", by_agent)
    write_csv(RESULTS / "constraint_passes_casewise_by_agent_llm.csv", by_run)
    for row in by_agent:
        print(row["agent"], row["split"], row["category"],
              f"{row['passed']}/{row['total']}", row["pass_rate_all_selected"])


if __name__ == "__main__":
    main()
