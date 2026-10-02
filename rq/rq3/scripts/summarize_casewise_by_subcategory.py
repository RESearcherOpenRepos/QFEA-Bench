#!/usr/bin/env python3
"""Aggregate exact test outcomes using a hand-reviewed subtype-to-family map."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from summarize_structured_constraint_passes import selected_test_count, selected_replays

from pathlib import Path

from summarize_structured_constraint_passes import load_test_rows, load_annotation_rows


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "rq/rq3/results/summary"
REPLAYS = ROOT / "rq/rq3/results/casewise_replays"
MAP_PATH = ROOT / "rq/rq3/results/constraint_subcategory_mapping.json"
AGENTS = ("minisweagent", "autocoderover", "openhands")
STATUSES = ("passed", "failed", "skipped", "not_collected", "not_run")
SPLITS = ("F2P", "P2P")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_mapping() -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    data = json.loads(MAP_PATH.read_text())
    mapping: dict[tuple[str, str], str] = {}
    labels: dict[str, str] = {"interface": "Interface"}
    for family in data["families"]:
        family_id = family["id"]
        if family_id in labels:
            raise ValueError(f"Duplicate family id: {family_id}")
        labels[family_id] = family["label"]
        for subtype in family["raw_subtypes"]:
            key = family["category"], subtype
            if key in mapping:
                raise ValueError(f"Subtype mapped twice: {key}")
            mapping[key] = family_id
    inventory = load_annotation_rows()
    expected = {(r["category"], r["subtype"]) for r in inventory
                if r["category"] in ("general_semantics", "quantum_semantics")}
    # The taxonomy also retains subtypes from archived, excluded samples.
    if not expected <= set(mapping):
        raise ValueError(f"Mapping mismatch: missing {sorted(expected - set(mapping))}, "
                         f"extra {sorted(set(mapping) - expected)}")
    return mapping, labels


def attach_family(rows: list[dict[str, str]], mapping: dict[tuple[str, str], str]) -> None:
    if len(rows) != selected_test_count():
        raise ValueError(f"Expected the full inventory of selected tests, got {len(rows)}")
    keys = {(r["sample_id"], r["split"], r["selector"]) for r in rows}
    if len(keys) != selected_test_count():
        raise ValueError("Duplicate sample/split/selector in run")
    for row in rows:
        if row["status"] not in STATUSES or row["split"] not in SPLITS:
            raise ValueError(f"Invalid test outcome: {row}")
        category = row["category"]
        row["subcategory"] = "interface" if category == "interface" else mapping[(category, row["subtype"])]


def summarize(rows: list[dict[str, str]], agent: str, run: str,
              labels: dict[str, str]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["split"], row["category"], row["subcategory"])].append(row)
    output = []
    for (split, category, family), group in sorted(groups.items()):
        counts = Counter(r["status"] for r in group)
        sample_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in group:
            sample_groups[row["sample_id"]].append(row)
        sample_equal = sum(
            sum(r["status"] == "passed" for r in sample_rows) / len(sample_rows)
            for sample_rows in sample_groups.values()
        ) / len(sample_groups)
        output.append({
            "agent": agent,
            "run": run,
            "split": split,
            "category": category,
            "subcategory": family,
            "subcategory_label": labels[family],
            "samples": len(sample_groups),
            "raw_subtypes": len({r["subtype"] for r in group}),
            **{status: counts[status] for status in STATUSES},
            "total": len(group),
            "pass_rate_all_selected": f"{counts['passed'] / len(group):.6f}",
            "sample_equal_pass_rate": f"{sample_equal:.6f}",
        })
    return output


def main() -> None:
    mapping, labels = read_mapping()
    inventory: list[dict[str, object]] = []
    by_agent: list[dict[str, object]] = []
    by_run: list[dict[str, object]] = []
    reference: set[tuple[str, str, str, str, str, str]] | None = None
    for agent in AGENTS:
        all_rows: list[dict[str, str]] = []
        for detail_path in selected_replays(agent):
            run = detail_path.stem.removeprefix(agent + "_")
            rows = load_test_rows(detail_path, agent, run)
            attach_family(rows, mapping)
            current = {
                (r["sample_id"], r["split"], r["selector"], r["category"],
                 r["subtype"], r["subcategory"])
                for r in rows
            }
            if reference is None:
                reference = current
                for item in summarize(rows, "inventory", "one_run", labels):
                    inventory.append({
                        "split": item["split"],
                        "category": item["category"],
                        "subcategory": item["subcategory"],
                        "subcategory_label": item["subcategory_label"],
                        "selected_tests": item["total"],
                        "samples": item["samples"],
                        "raw_subtypes": item["raw_subtypes"],
                    })
            elif current != reference:
                raise ValueError(f"Selected testcase labels differ from reference: {path}")
            all_rows.extend(rows)
            by_run.extend(summarize(rows, agent, run, labels))
        by_agent.extend(summarize(all_rows, agent, "all_five_llms", labels))

    write_csv(RESULTS / "constraint_subcategory_casewise_inventory.csv", inventory)
    write_csv(RESULTS / "constraint_subcategory_casewise_by_agent.csv", by_agent)
    write_csv(RESULTS / "constraint_subcategory_casewise_by_agent_llm.csv", by_run)

    original = read_csv(RESULTS / "constraint_passes_casewise_by_agent.csv")
    for row in original:
        agent, split, category = row["agent"], row["split"], row["category"]
        parts = [r for r in by_agent if r["agent"] == agent
                 and r["split"] == split and r["category"] == category]
        if sum(int(r["passed"]) for r in parts) != int(row["passed"]):
            raise ValueError(f"Pass count does not reproduce top-level category: {agent}/{split}/{category}")
        if sum(int(r["total"]) for r in parts) != int(row["total"]):
            raise ValueError(f"Test count does not reproduce top-level category: {agent}/{split}/{category}")
    print(f"Validated {len(mapping)} hand-reviewed raw subtype mappings, "
          f"{len(inventory)} split/subcategory groups, and 15 complete Agent-LLM runs.")
    for row in inventory:
        print(row)


if __name__ == "__main__":
    main()
