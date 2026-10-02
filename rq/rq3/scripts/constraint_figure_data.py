#!/usr/bin/env python3
"""Load and validate constraint data for the current RQ3 figure."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from summarize_structured_constraint_passes import selected_test_count

from pathlib import Path

from summarize_structured_constraint_passes import load_annotation_rows


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "rq/rq3/results/summary/constraint_passes_casewise_by_agent.csv"
SUBCATEGORY_SOURCE = ROOT / "rq/rq3/results/summary/constraint_subcategory_casewise_by_agent.csv"
MAPPING_SOURCE = ROOT / "rq/rq3/results/constraint_subcategory_mapping.json"
AGENTS = ("minisweagent", "autocoderover", "openhands")
AGENT_LABELS = {
    "minisweagent": "Mini-SWE-Agent",
    "autocoderover": "AutoCodeRover",
    "openhands": "OpenHands",
}
CATEGORIES = (
    ("general_semantics", "Classical Semantics"),
    ("quantum_semantics", "Quantum Semantics"),
    ("interface", "Interface"),
)
EXPECTED_PER_RUN = {
    "F2P": {"general_semantics": 171, "quantum_semantics": 269, "interface": 242},
    "P2P": {"general_semantics": 339, "quantum_semantics": 354, "interface": 308},
}
SUBCATEGORIES = {
    "general_semantics": (
        ("algebraic_numeric_computation", "Mathematical Operations"),
        ("model_data_transformation", "Data Processing"),
        ("learning_optimization_outcome", "Algorithmic Solving"),
    ),
    "quantum_semantics": (
        ("operator_algebra_and_mapping", "Operator Semantics"),
        ("state_circuit_and_measurement", "Circuit Semantics"),
        ("hamiltonian_chemistry_quantum_optimization", "Application Semantics"),
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def pooled_subcategory_data(
    primary: dict[tuple[str, str, str], tuple[int, int]],
) -> tuple[
    dict[str, set[str]],
    dict[str, int],
    dict[tuple[str, str], set[str]],
    dict[tuple[str, str], set[tuple[str, str, str]]],
    dict[tuple[str, str], tuple[int, int]],
]:
    mapping_json = json.loads(MAPPING_SOURCE.read_text())
    family_for_subtype = {
        (family["category"], subtype): family["id"]
        for family in mapping_json["families"]
        for subtype in family["raw_subtypes"]
    }
    samples: dict[str, set[str]] = defaultdict(set)
    tests: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    split_samples: dict[tuple[str, str], set[str]] = defaultdict(set)
    split_tests: dict[tuple[str, str], set[tuple[str, str, str]]] = defaultdict(set)
    reference_rows = load_annotation_rows()
    if len(reference_rows) != selected_test_count():
        raise ValueError(f"Expected the full inventory of reference tests, got {len(reference_rows)}")
    for row in reference_rows:
        category = row["category"]
        family = ("interface" if category == "interface"
                  else family_for_subtype[(category, row["subtype"])])
        key = (row["sample_id"], row["split"], row["selector"])
        for group in (category, family):
            samples[group].add(row["id"])
            tests[group].add(key)
            split_samples[(group, row["split"])].add(row["id"])
            split_tests[(group, row["split"])].add(key)
    if sum(len(tests[category]) for category, _ in CATEGORIES) != selected_test_count():
        raise ValueError("Primary categories do not partition selected tests")

    pooled: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in read_csv(SUBCATEGORY_SOURCE):
        group = row["subcategory"]
        agent = row["agent"]
        if row["run"] != "all_five_llms":
            raise ValueError(f"Unexpected run in subcategory summary: {row['run']}")
        value = pooled[(group, agent)]
        value[0] += int(row["passed"])
        value[1] += int(row["total"])
    expected_groups = {family for entries in SUBCATEGORIES.values() for family, _ in entries}
    expected_groups.add("interface")
    if set(group for group, _ in pooled) != expected_groups:
        raise ValueError("Incomplete subcategory summary")
    for group in expected_groups:
        for agent in AGENTS:
            passed, total = pooled[(group, agent)]
            if total != 5 * len(tests[group]) or not 0 <= passed <= total:
                raise ValueError(f"Subcategory totals disagree with reference tests: {group}/{agent}")
    for category, _ in CATEGORIES:
        for agent in AGENTS:
            selected = sum(primary[(agent, split, category)][1] for split in EXPECTED_PER_RUN)
            if selected != 5 * len(tests[category]):
                raise ValueError(f"Primary totals disagree with reference tests: {category}/{agent}")
            families = (SUBCATEGORIES[category] if category in SUBCATEGORIES
                        else (("interface", "Interface"),))
            if selected != sum(pooled[(family, agent)][1] for family, _ in families):
                raise ValueError(f"Subcategories do not reproduce category: {category}/{agent}")
    return (
        samples,
        {group: len(keys) for group, keys in tests.items()},
        split_samples,
        split_tests,
        {key: tuple(value) for key, value in pooled.items()},
    )

