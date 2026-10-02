"""Write one manually reviewed sample annotation from stdin JSON decisions.

Input shape: {"rationale": "...", "decisions": [{"label": "category/subtype",
"assertions": [{"line": 1, "expected": "..."}]}]}. Decisions follow F2P then
P2P selector order in sample.json. Source line locations are checked before write.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from inspect_sample_tests import test_node


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = Path("/tmp/qfea-test-sources")
CATEGORIES = {"general_semantics", "quantum_semantics", "interface"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", type=int)
    args = parser.parse_args()
    decisions = json.load(sys.stdin)
    item = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())["samples"][args.id - 1]
    if item["id"] != args.id:
        raise ValueError("Dataset ID does not match index order")
    sample = json.loads(
        (ROOT / "benchmark/dataset/samples" / item["sample_path"] / "sample.json").read_text()
    )
    selectors = [
        (split, selector)
        for split, key in (("F2P", "fail_pass"), ("P2P", "pass_pass"))
        for selector in sample["validation"]["patched"][key]["file_list"]
    ]
    if len(decisions["decisions"]) != len(selectors):
        raise ValueError(f"Expected {len(selectors)} decisions")
    tests = []
    for number, ((split, selector), decision) in enumerate(
        zip(selectors, decisions["decisions"]), 1
    ):
        if isinstance(decision, list):
            label, evidence = decision
            decision = {
                "label": label,
                "assertions": [
                    {"line": line, "expected": expected} for line, expected in evidence
                ],
            }
        label = decision["label"]
        if "/" not in label or label.split("/", 1)[0] not in CATEGORIES:
            raise ValueError(f"Invalid label at test {number}: {label}")
        source_file = decision.get("source_file") or selector.split("::")[0]
        source_selector = decision.get("source_selector") or selector
        path = SOURCE_ROOT / item["sample_id"] / source_file
        source = path.read_text()
        node = test_node(source, source_selector)
        assertions = decision["assertions"]
        if not assertions:
            raise ValueError(f"No assertion evidence at test {number}")
        for evidence in assertions:
            line = evidence["line"]
            if evidence.get("via_helper") is not None:
                call_line = evidence["via_helper"]
                if not (node.lineno <= call_line <= node.end_lineno):
                    raise ValueError(f"Test {number}: helper call is outside the test body")
                helper_selector = evidence.get("helper_selector")
                if not helper_selector:
                    raise ValueError(f"Test {number}: missing helper selector")
                helper = test_node(source, helper_selector)
                if not (helper.lineno <= line <= helper.end_lineno):
                    raise ValueError(f"Test {number}: assertion line is outside the helper")
            elif not (node.lineno <= line <= node.end_lineno):
                raise ValueError(f"Test {number}: line {line} is outside the test body")
            if not evidence["expected"].strip():
                raise ValueError(f"Test {number}: empty expected behavior")
        test_record = {
            "test_number": number,
            "split": split,
            "selector": selector,
            "label": label,
            "assertions": assertions,
        }
        if decision.get("rationale"):
            test_record["rationale"] = decision["rationale"]
        if decision.get("source_file"):
            test_record["source_file"] = source_file
            test_record["source_selector"] = source_selector
        tests.append(test_record)
    counts = collections.Counter(test["label"] for test in tests)
    source_paths = {
        path
        for test in tests
        for path in (
            test["selector"].split("::")[0],
            test.get("source_file") or test["selector"].split("::")[0],
        )
    }
    source_files = sorted(
        f"https://github.com/{item['repo']}/blob/{sample['instance']['patch']}/{path}"
        for path in source_paths
    )
    annotation = {
        "id": args.id,
        "sample_id": item["sample_id"],
        "repo": item["repo"],
        "patch_commit": sample["instance"]["patch"],
        "status": "manually_reviewed",
        "summary": {
            "f2p_tests": sum(split == "F2P" for split, _ in selectors),
            "p2p_tests": sum(split == "P2P" for split, _ in selectors),
            "subtype_test_counts": dict(counts),
        },
        "tests": tests,
        "source_files": source_files,
        "rationale": decisions["rationale"],
    }
    if decisions.get("review_provenance"):
        annotation["review_provenance"] = decisions["review_provenance"]
    path = (
        ROOT / "rq/rq3/results/sample_constraint_annotations"
        / f"{args.id:03d}_{item['sample_id']}.json"
    )
    with path.open("x") as handle:
        json.dump(annotation, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(path)


if __name__ == "__main__":
    main()
