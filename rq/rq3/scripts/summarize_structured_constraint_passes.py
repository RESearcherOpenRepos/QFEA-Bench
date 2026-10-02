"""Join hand-reviewed labels to exact testcase outcomes from a casewise replay.

This script reads structured testcase outcomes rather than parsing pytest stdout.
It requires one structured testcase record for every selected F2P/P2P selector.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SUITES = (("F2P", "fail_pass"), ("P2P", "pass_pass"))


def selected_replays(agent: str) -> list[Path]:
    """Select released replays from the current analysis manifest, not local runs."""
    manifest = ROOT / "rq/rq1/results/current/all_runs_overview.csv"
    with manifest.open(newline="") as handle:
        settings = list(csv.DictReader(handle))
    manifest_agent = "mini-swe" if agent == "minisweagent" else agent
    paths = sorted(ROOT / "rq/rq3/results/casewise_replays" / f"{agent}_{r['run_id']}.json"
                   for r in settings if r["agent"] == manifest_agent)
    if len(paths) != 5 or len(set(paths)) != 5:
        raise ValueError(f"Expected five distinct selected settings for {agent}")
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing released testcase replay: {path}")
    return paths


def selected_test_count() -> int:
    index = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())["samples"]
    return sum(len(json.loads((ROOT / "benchmark/dataset/samples" / item["sample_path"] / "sample.json").read_text())["validation"]["patched"][suite]["file_list"]) for item in index for suite in ("fail_pass", "pass_pass"))


def load_annotation_rows() -> list[dict[str, str]]:
    """Read the selected test inventory directly from the manual annotations."""
    index = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())["samples"]
    rows = []
    for item in index:
        annotation = json.loads((ROOT / "rq/rq3/results/sample_constraint_annotations"
                                 / f"{item['id']:03d}_{item['sample_id']}.json").read_text())
        if annotation["id"] != item["id"] or annotation["sample_id"] != item["sample_id"]:
            raise ValueError(f"Annotation identity mismatch: {item['sample_id']}")
        for test in annotation["tests"]:
            category, subtype = test["label"].split("/", 1)
            rows.append({"id": str(item["id"]), "sample_id": item["sample_id"],
                         "split": test["split"], "test_number": str(test["test_number"]),
                         "selector": test["selector"], "category": category, "subtype": subtype})
    if len(rows) != selected_test_count() or len({(r["sample_id"], r["split"], r["selector"]) for r in rows}) != selected_test_count():
        raise ValueError("Expected exactly the selected test inventory")
    return rows


def load_test_rows(input_path: Path, agent: str, run: str) -> list[dict[str, str]]:
    index = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())["samples"]
    by_sample = {item["sample_id"]: item for item in index}
    payload = json.loads(input_path.read_text())
    if payload["summary"].get("pending"):
        raise ValueError("The casewise evaluation is incomplete")
    results = {result["instance_id"]: result for result in payload["results"]}
    if set(results) != set(by_sample):
        raise ValueError("Casewise replay must include all indexed samples")

    detail = []
    for item in index:
        sample_id = item["sample_id"]
        annotation = json.loads(
            (ROOT / "rq/rq3/results/sample_constraint_annotations"
             / f"{item['id']:03d}_{sample_id}.json").read_text()
        )
        result = results[sample_id]
        if "test_cases" not in result:
            raise ValueError(f"Missing structured test cases: {sample_id}")
        for split, key in SUITES:
            tests = [test for test in annotation["tests"] if test["split"] == split]
            cases = result["test_cases"][key]
            if [case["selector"] for case in cases] != [test["selector"] for test in tests]:
                raise ValueError(f"Case selectors differ from annotations: {sample_id}/{split}")
            fraction = result[key]
            passed = sum(case["status"] == "passed" for case in cases)
            if fraction["passed"] != passed or fraction["total"] != len(cases):
                raise ValueError(f"Suite fraction disagrees with cases: {sample_id}/{split}")
            if fraction["status"] == "passed" and passed != len(cases):
                raise ValueError(f"Incomplete suite marked passed: {sample_id}/{split}")
            for test, case in zip(tests, cases):
                category, subtype = test["label"].split("/", 1)
                detail.append({
                    "agent": agent,
                    "run": run,
                    "id": item["id"],
                    "sample_id": sample_id,
                    "split": split,
                    "test_number": test["test_number"],
                    "selector": case["selector"],
                    "category": category,
                    "subtype": subtype,
                    "status": case["status"],
                    "failure_phase": case.get("phase", ""),
                })

    if len(detail) != selected_test_count() or len({(r["sample_id"], r["split"], r["selector"]) for r in detail}) != selected_test_count():
        raise ValueError("Expected exactly the selected test inventory")
    return [{key: str(value) for key, value in row.items()} for row in detail]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Casewise evaluator JSON")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "rq/rq3/results/intermediate")
    args = parser.parse_args()

    detail = load_test_rows(args.input, args.agent, args.run)

    summary = []
    for split, _ in SUITES:
        for category in ("general_semantics", "quantum_semantics", "interface"):
            rows = [row for row in detail if row["split"] == split and row["category"] == category]
            counts = Counter(row["status"] for row in rows)
            summary.append({
                "agent": args.agent,
                "run": args.run,
                "split": split,
                "category": category,
                "passed": counts["passed"],
                "failed": counts["failed"],
                "skipped": counts["skipped"],
                "not_collected": counts["not_collected"],
                "not_run": counts["not_run"],
                "total": len(rows),
                "pass_rate_all_selected": f"{counts['passed'] / len(rows):.6f}" if rows else "",
            })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"constraint_passes_casewise_{args.agent}_{args.run}"
    for suffix, rows in (("by_test", detail), ("by_run", summary)):
        path = args.output_dir / f"{stem}_{suffix}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"{path}: {len(rows)} rows")


if __name__ == "__main__":
    main()
