#!/usr/bin/env python3
"""Reproduce Table 1 patch medians using the SWE-bench non-test patch split.

Requires pandas, pyarrow, and unidiff. QFEA inputs are complete base-to-patched
git diffs named <instance_id>.patch; external inputs are official test parquet
files. This does not change the task-specific implementation scope used in RQ2.
"""

import argparse
import ast
import csv
import hashlib
import json
import statistics
from pathlib import Path

import pandas as pd
from unidiff import PatchSet


def patch_stats(benchmark, instance_id, patch, split_tests=False):
    files = list(PatchSet(patch))
    if split_tests:
        # Match swebench.collect.utils.extract_patches, including case sensitivity.
        files = [
            f for f in files
            if not any(word in f.path for word in ("test", "tests", "e2e", "testing"))
        ]
    return {
        "benchmark": benchmark,
        "instance_id": instance_id,
        "files": len(files),
        "added_lines": sum(f.added for f in files),
        "deleted_lines": sum(f.removed for f in files),
        "changed_lines": sum(f.added + f.removed for f in files),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qfea-patches", required=True, type=Path)
    parser.add_argument("--swe-verified-test", required=True, type=Path)
    parser.add_argument("--pro-v1-test", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    paths = sorted(args.qfea_patches.glob("*.patch"))
    sample_root = Path(__file__).resolve().parents[1] / "samples"
    expected = {
        json.loads(p.read_text())["instance"]["instance_id"]
        for p in sample_root.rglob("sample.json")
    }
    if {p.stem for p in paths} != expected:
        raise ValueError("QFEA patch IDs must match the complete sample inventory")
    rows = [patch_stats("QFEA-Bench", p.stem, p.read_text(), True) for p in paths]
    sources = {}
    task_rows = []
    for name, path, count in (
        ("SWE-bench Verified", args.swe_verified_test, 500),
        ("SWE-bench Pro v1", args.pro_v1_test, 731),
    ):
        data = pd.read_parquet(path)
        if len(data) != count or data.instance_id.nunique() != count:
            raise ValueError(f"Unexpected {name} split: expected {count} unique tasks")
        rows.extend(patch_stats(name, r.instance_id, r.patch) for r in data.itertuples())
        for r in data.to_dict('records'):
            counts = {}
            for output, candidates in (
                ('fail_to_pass', ('FAIL_TO_PASS', 'fail_to_pass')),
                ('pass_to_pass', ('PASS_TO_PASS', 'pass_to_pass')),
            ):
                value = next(r[k] for k in candidates if k in r)
                try:
                    tests = json.loads(value)
                except json.JSONDecodeError:
                    tests = ast.literal_eval(value)
                if not isinstance(tests, list):
                    raise ValueError(f'Expected a test list for {r["instance_id"]}')
                counts[output] = len(tests)
            task_rows.append(dict(benchmark=name, instance_id=r['instance_id'],
                                  statement_words=len(r['problem_statement'].split()), **counts))
        sources[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    summary = {}
    for name in ("QFEA-Bench", "SWE-bench Pro v1", "SWE-bench Verified"):
        group = [r for r in rows if r["benchmark"] == name]
        summary[name] = {
            "instances": len(group),
            "median_files": statistics.median(r["files"] for r in group),
            "median_changed_lines": statistics.median(r["changed_lines"] for r in group),
        }
        tasks = [r for r in task_rows if r['benchmark'] == name]
        if tasks:
            summary[name].update({f'median_{key}': statistics.median(r[key] for r in tasks)
                                  for key in ('statement_words', 'fail_to_pass', 'pass_to_pass')})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "instance_patch_stats.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (args.output_dir / 'external_task_stats.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(task_rows[0]))
        writer.writeheader()
        writer.writerows(task_rows)
    report = {"summary": summary, "external_inputs": sources}
    (args.output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
