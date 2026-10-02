#!/usr/bin/env python3
"""Count descriptions and complete reference programs in QuanBench's 44 tasks.

Reads source as data, without executing the quantum programs. Each nonempty
canonical_solution is one Python source unit, as used by QuanBench's evaluator.
Solution lines include imports, signatures, comments, and blank lines.
"""

import argparse
import ast
import csv
import hashlib
import json
import statistics
from pathlib import Path


def summarize(path):
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(tasks) != 44 or len({task["task_id"] for task in tasks}) != 44:
        raise ValueError("Expected the original 44-task QuanBench dataset")
    rows = []
    for task in tasks:
        functions = [
            node for node in ast.walk(ast.parse(task["complete_prompt"]))
            if isinstance(node, ast.FunctionDef) and node.name == task["entry_point"]
        ]
        if len(functions) != 1 or not ast.get_docstring(functions[0]):
            raise ValueError(f"Missing unique task docstring: {task['task_id']}")
        source = task["canonical_solution"]
        module = ast.parse(source)
        if not any(
            isinstance(node, ast.FunctionDef) and node.name == task["entry_point"]
            for node in module.body
        ):
            raise ValueError(f"Missing reference entry point: {task['task_id']}")
        rows.append({
            "task_id": task["task_id"],
            "statement_words": len(ast.get_docstring(functions[0]).split()),
            "solution_files": 1,
            "solution_lines": len(source.splitlines()),
        })
    summary = {
        "instances": len(rows),
        **{f"median_{key}": statistics.median(r[key] for r in rows)
           for key in ("statement_words", "solution_files", "solution_lines")},
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    return rows, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    rows, summary = summarize(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "quanbench_solution_stats.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "quanbench_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
