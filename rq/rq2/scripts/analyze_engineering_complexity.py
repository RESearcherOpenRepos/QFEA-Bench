#!/usr/bin/env python3
"""Post-evaluation engineering-complexity analysis for QuanBench samples."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_OUTPUT_CSV = ROOT / "rq" / "rq2" / "results" / "engineering_complexity.csv"
DEFAULT_RESULT_FILES = (
    (
        "deepseek_pro",
        ROOT
        / "benchmark"
        / "evaluation"
        / "minisweagent"
        / "results"
        / "results_deepseek_v4_pro_20260602.json",
    ),
)


_CORRECTED = ROOT / "rq/rq1/results/corrected_evaluations/mini-swe_deepseek_v4_pro_20260602.json"
if _CORRECTED.exists():
    DEFAULT_RESULT_FILES = (("deepseek_pro", _CORRECTED),)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_samples(samples_dir: Path) -> list[dict[str, Any]]:
    samples = []
    for path in sorted(samples_dir.rglob("sample.json")):
        sample = load_json(path)
        instance = sample["instance"]
        metadata = sample.get("metadata", {})
        golden_patch = sample.get("golden_patch", {})
        samples.append(
            {
                "sample_path": str(path.relative_to(ROOT)),
                "sample_id": instance["instance_id"],
                "repo": instance["repo"],
                "base_commit": instance["base_commit"],
                "patch_commit": instance["patch"],
                "quantum_depth": metadata.get("quantum_depth", "unknown"),
                "oracle_files": golden_patch.get("oracle_files", []),
                "image": sample.get("runtime", {})
                .get("docker", {})
                .get("image")
                or f"benchmark-evaluation:{instance['instance_id']}",
            }
        )
    return samples


def load_resolved_map(result_file: Path) -> dict[str, bool]:
    result = load_json(result_file)
    results = result.get("results", [])
    if isinstance(results, dict):
        items = results.values()
    else:
        items = results
    return {
        item["instance_id"]: bool(item.get("resolved", False))
        for item in items
    }


def count_changed_nonempty_lines(diff_text: str) -> int:
    total = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            if line[1:].strip():
                total += 1
    return total


def docker_git_diff(sample: dict[str, Any]) -> str:
    files = sample["oracle_files"]
    if not files:
        return ""
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "--entrypoint",
        "git",
        sample["image"],
        "-C",
        "/workspace/repo",
        "diff",
        "--unified=0",
        "--no-color",
        "--no-ext-diff",
        sample["base_commit"],
        sample["patch_commit"],
        "--",
        *files,
    ]
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def attach_footprint(samples: list[dict[str, Any]]) -> None:
    for sample in samples:
        diff = docker_git_diff(sample)
        sample["gold_solution_lines"] = count_changed_nonempty_lines(diff)
        sample["gold_solution_files"] = len(sample["oracle_files"])


def zscores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0 for _ in values]
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if stdev == 0:
        return [0.0 for _ in values]
    return [(value - mean) / stdev for value in values]


def assign_engineering_complexity(samples: list[dict[str, Any]]) -> None:
    line_logs = [math.log1p(sample["gold_solution_lines"]) for sample in samples]
    file_logs = [math.log1p(sample["gold_solution_files"]) for sample in samples]
    line_z = zscores(line_logs)
    file_z = zscores(file_logs)

    for sample, lz, fz in zip(samples, line_z, file_z, strict=True):
        sample["engineering_complexity_score"] = lz + fz

    ranked = sorted(
        samples,
        key=lambda item: (item["engineering_complexity_score"], item["sample_id"]),
    )
    n = len(ranked)
    small_count = math.ceil(n / 3)
    medium_count = (n - small_count) // 2
    for rank, sample in enumerate(ranked):
        if rank < small_count:
            tier = "small"
        elif rank < small_count + medium_count:
            tier = "medium"
        else:
            tier = "large"
        sample["engineering_complexity"] = tier


def attach_results(
    samples: list[dict[str, Any]], result_maps: dict[str, dict[str, bool]]
) -> None:
    for sample in samples:
        for alias, resolved_map in result_maps.items():
            value = resolved_map.get(sample["sample_id"])
            sample[f"resolved_{alias}"] = value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def output_rows(
    samples: list[dict[str, Any]], result_aliases: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for sample in sorted(samples, key=lambda item: item["sample_id"]):
        row = {
            "sample_id": sample["sample_id"],
            "repo": sample["repo"],
            "quantum_depth": sample["quantum_depth"],
            "gold_solution_lines": sample["gold_solution_lines"],
            "gold_solution_files": sample["gold_solution_files"],
            "engineering_complexity_score": sample["engineering_complexity_score"],
            "engineering_complexity": sample["engineering_complexity"],
        }
        for alias in result_aliases:
            row[f"resolved_{alias}"] = sample.get(f"resolved_{alias}")
        rows.append(row)
    return rows


def parse_result_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = resolve_path(value)
        return path.stem, path
    alias, path = value.split("=", 1)
    return alias, resolve_path(path)


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--refresh-outcomes", action="store_true", help="Refresh only resolved columns; preserve measured patch sizes")
    parser.add_argument(
        "--result",
        action="append",
        default=None,
        help="Result file as alias=path. Defaults to DeepSeek Pro.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_files = (
        [parse_result_arg(value) for value in args.result]
        if args.result
        else DEFAULT_RESULT_FILES
    )

    if args.refresh_outcomes:
        with args.output_csv.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        for alias,path in result_files:
            outcomes = load_resolved_map(path)
            assert set(outcomes) == {r["sample_id"] for r in rows}
            for row in rows:
                row[f"resolved_{alias}"] = outcomes[row["sample_id"]]
        write_csv(args.output_csv, rows)
        print(f"Refreshed outcomes in {args.output_csv}")
        return

    samples = iter_samples(args.samples_dir)
    if not samples:
        raise SystemExit(f"No sample.json files found under {args.samples_dir}")

    attach_footprint(samples)
    assign_engineering_complexity(samples)

    result_maps = {alias: load_resolved_map(path) for alias, path in result_files}
    attach_results(samples, result_maps)

    result_aliases = [alias for alias, _ in result_files]
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_csv, output_rows(samples, result_aliases))

    print(f"Wrote CSV for {len(samples)} samples to {args.output_csv}")


if __name__ == "__main__":
    main()
