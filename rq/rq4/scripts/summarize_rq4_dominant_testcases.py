"""Validate the manual testcase audit and summarize already assigned labels.

This script never infers a root cause; it only counts saved manual decisions.
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "results"
AUDIT = ROOT / "rq4_dominant_testcases"
TAXONOMY = ROOT.parent.parent / "rq3/results/constraint_subcategory_mapping.json"
CAUSES = ("contract", "representation", "state_propagation", "computation")
GROUPS = (
    ("general_semantics", "algebraic_numeric_computation", "Mathematical Operations"),
    ("general_semantics", "model_data_transformation", "Data Processing"),
    ("general_semantics", "learning_optimization_outcome", "Algorithmic Solving"),
    ("interface", "interface", "Interface"),
    ("quantum_semantics", "operator_algebra_and_mapping", "Operator Semantics"),
    ("quantum_semantics", "state_circuit_and_measurement", "Circuit Semantics"),
    ("quantum_semantics", "hamiltonian_chemistry_quantum_optimization", "Application Semantics"),
)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    queue = read_jsonl(AUDIT / "audit_queue.jsonl")
    manual = read_jsonl(AUDIT / "manual.jsonl")
    key = lambda x: (x["sample_id"], x["split"], x["selector"])
    cohort = json.loads((AUDIT / "cohort.json").read_text())
    assert len(queue) == len(manual) == cohort["eligible_ever_failed_tests"]
    indexed = {key(x): x for x in queue}
    assert len(indexed) == len(queue)
    assert len({key(x) for x in manual}) == len(manual)
    assert set(map(key, manual)) == set(indexed)

    mapping = {"interface": "interface"}
    taxonomy = json.loads(TAXONOMY.read_text())
    for family in taxonomy["families"]:
        for subtype in family["raw_subtypes"]:
            mapping[f"{family['category']}/{subtype}"] = family["id"]

    totals = defaultdict(Counter)
    observations = defaultdict(Counter)
    observation_rows = []
    for row in manual:
        source = indexed[key(row)]
        assert (row["id"], row["test_number"], row["constraint_label"]) == (
            source["id"], source["test_number"], source["constraint_label"]
        )
        observed = row["reviewed_observations"]
        assert len(observed) == 15
        assert [
            (x["agent"], x["run"], x["observed_status"]) for x in observed
        ] == [(x["agent"], x["run"], x["status"]) for x in source["observations"]]
        statuses = Counter(x["observed_status"] for x in observed)
        assert dict(statuses) == source["status_counts"]
        supports = Counter(
            x["cause"] for x in observed if x["observed_status"] == "failed" and x["cause"]
        )
        assert dict(supports) == row["cause_support"]
        assert sum(supports.values()) + row["unresolved_failure_count"] == statuses["failed"]
        root = row["dominant_root_cause"]
        if root:
            assert root in CAUSES and supports[root] == max(supports.values())
            assert list(supports.values()).count(supports[root]) == 1
            assert row["status"] == "reviewed"
        else:
            assert row["status"] in ("undetermined", "invalid_test")
        group = mapping[row["constraint_label"].split("/")[0]] if row["constraint_label"].startswith("interface/") else mapping[row["constraint_label"]]
        totals[group][root or row["status"]] += 1
        for observation in observed:
            if observation["observed_status"] != "failed":
                assert observation["cause"] is None
                continue
            cause = observation["cause"]
            assert cause in CAUSES, "Every observed failure must have an audited cause"
            observations[group][cause] += 1
            observation_rows.append((row["sample_id"], row["split"], row["selector"],
                                     observation["agent"], observation["run"], group, cause))

    output = AUDIT / "constraint_root_cause_summary.csv"
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("category", "subcategory", "testcases", *CAUSES, "undetermined", "invalid_test"))
        for category, group, label in GROUPS:
            count = totals[group]
            writer.writerow((category, label, sum(count.values()), *(count[c] for c in CAUSES), count["undetermined"], count["invalid_test"]))
    print(output)
    print("total", Counter(row["dominant_root_cause"] or row["status"] for row in manual))
    for category, group, label in GROUPS:
        print(label, dict(totals[group]))

    # The main-paper table counts actual testcase--configuration failures.
    # The original testcase-dominant summary above is retained as historical analysis data.
    ordered_causes = ("contract", "representation", "computation", "state_propagation")
    assert len(set(row[:5] for row in observation_rows)) == len(observation_rows)
    assert len(observation_rows) == sum(observations[g].total() for _, g, _ in GROUPS)
    with (AUDIT / "failure_observations.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("sample_id", "split", "selector", "agent", "run", "subcategory", "cause"))
        writer.writerows(observation_rows)
    with (AUDIT / "constraint_root_cause_observations.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("category", "subcategory", "testcases", "failure_observations", *ordered_causes))
        for category, group, label in GROUPS:
            count = observations[group]
            row = (category, label, totals[group].total(), count.total(), *(count[c] for c in ordered_causes))
            writer.writerow(row)
            print("OBSERVATIONS", label, dict(count), "total", count.total())
    audit_summary = {
        "tasks": len({r["sample_id"] for r in manual}),
        "testcases": len(manual),
        "failure_observations": len(observation_rows),
        "testcases_with_multiple_causes": sum(len(r["cause_support"]) > 1 for r in manual),
        "causes": dict(Counter(r[-1] for r in observation_rows)),
        "unit": "One observed failed testcase per Agent--LLM configuration; no evaluator-repeat expansion",
    }
    (AUDIT / "observation_summary.json").write_text(json.dumps(audit_summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
