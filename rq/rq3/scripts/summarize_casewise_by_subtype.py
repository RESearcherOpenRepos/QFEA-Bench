#!/usr/bin/env python3
"""Aggregate manually reviewed raw test subtypes and structured pytest outcomes."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from summarize_structured_constraint_passes import load_test_rows, load_annotation_rows


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "rq/rq3/results/intermediate"
REPLAYS = ROOT / "rq/rq3/results/casewise_replays"
AGENTS = ("minisweagent", "autocoderover", "openhands")
SPLITS = ("F2P", "P2P")
STATUSES = ("passed", "failed", "skipped", "not_collected", "not_run")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1517:
        raise ValueError(f"Expected 1,517 selected tests: {path}")
    keys = {(r["sample_id"], r["split"], r["selector"]) for r in rows}
    if len(keys) != 1517:
        raise ValueError(f"Duplicate sample/split/selector: {path}")
    if any(not r["category"] or not r["subtype"] for r in rows):
        raise ValueError(f"Missing manual subtype: {path}")
    if set(r["status"] for r in rows) - set(STATUSES):
        raise ValueError(f"Unexpected testcase status: {path}")
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, str]], agent: str, run: str) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["split"], row["category"], row["subtype"])].append(row)
    output = []
    for (split, category, subtype), group in sorted(groups.items()):
        counts = Counter(row["status"] for row in group)
        output.append({
            "agent": agent,
            "run": run,
            "split": split,
            "category": category,
            "subtype": subtype,
            "samples": len({r["sample_id"] for r in group}),
            **{status: counts[status] for status in STATUSES},
            "total": len(group),
            "pass_rate_all_selected": f"{counts['passed'] / len(group):.6f}",
        })
    return output


def main() -> None:
    inventory: list[dict[str, object]] = []
    by_agent: list[dict[str, object]] = []
    by_run: list[dict[str, object]] = []
    reference: set[tuple[str, str, str, str, str]] | None = None
    for agent in AGENTS:
        all_rows: list[dict[str, str]] = []
        predictions = sorted((ROOT / "benchmark/evaluation" / agent / "runs").glob("*/preds.json"))
        if len(predictions) != 5:
            raise ValueError(f"Expected five saved runs for {agent}")
        for predictions_file in predictions:
            run = predictions_file.parent.name
            path = REPLAYS / f"{agent}_{run}.json"
            rows = load_test_rows(path, agent, run)
            current = {
                (r["sample_id"], r["split"], r["selector"], r["category"], r["subtype"])
                for r in rows
            }
            if reference is None:
                reference = current
                groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
                sizes: Counter[tuple[str, str, str]] = Counter()
                for sample, split, _, category, subtype in current:
                    groups[(split, category, subtype)].add(sample)
                    sizes[(split, category, subtype)] += 1
                inventory = [
                    {"split": split, "category": category, "subtype": subtype,
                     "selected_tests": sizes[(split, category, subtype)],
                     "samples": len(groups[(split, category, subtype)])}
                    for split, category, subtype in sorted(sizes)
                ]
            elif current != reference:
                raise ValueError(f"Selected testcase labels differ from the reference: {path}")
            all_rows.extend(rows)
            by_run.extend(summarize(rows, agent, run))
        by_agent.extend(summarize(all_rows, agent, "all_five_llms"))
    write_csv(RESULTS / "constraint_subtype_casewise_inventory.csv", inventory)
    write_csv(RESULTS / "constraint_subtype_casewise_by_agent.csv", by_agent)
    write_csv(RESULTS / "constraint_subtype_casewise_by_agent_llm.csv", by_run)
    for split in SPLITS:
        subset = [r for r in inventory if r["split"] == split]
        print(f"{split}: {sum(r['selected_tests'] for r in subset)} selected tests, "
              f"{len(subset)} raw subtypes; "
              f"{sum(r['selected_tests'] == 1 for r in subset)} singleton subtypes")


if __name__ == "__main__":
    main()
