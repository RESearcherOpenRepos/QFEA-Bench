#!/usr/bin/env python3
"""Shared task-property data for the current RQ2 table; exported by export_paper_tables.py."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STRATA_CSV = ROOT / "rq" / "rq2" / "results" / "engineering_complexity.csv"
DEFAULT_TOTAL_EXPECTED = 106
QUANTUM_DEPTHS = ("medium", "strong")
ENGINEERING_COMPLEXITIES = ("small", "medium", "large")

sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from rq.rq1.scripts.analyze_rq1 import (  # noqa: E402
    DEFAULT_RUNS,
    as_int,
    display_agent,
    display_llm,
    enriched_rows,
    token_total,
)


def load_strata(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["sample_id"]: row for row in csv.DictReader(handle)}


def complete_run_rows(strata: dict[str, dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    excluded = []
    for spec in DEFAULT_RUNS:
        if not spec.result_path.exists():
            continue
        run_rows = enriched_rows(spec)
        total = len(run_rows)
        metrics_known = sum(row["metrics_known"] for row in run_rows)
        if total != DEFAULT_TOTAL_EXPECTED or metrics_known != DEFAULT_TOTAL_EXPECTED:
            excluded.append(
                f"{display_agent(spec.agent)} / {spec.model}: "
                f"total {total}/{DEFAULT_TOTAL_EXPECTED}, "
                f"metric coverage {metrics_known}/{DEFAULT_TOTAL_EXPECTED}"
            )
            continue

        for row in run_rows:
            item = row["item"]
            sample_id = str(item["instance_id"])
            meta = strata.get(sample_id)
            if meta is None:
                raise ValueError(f"Missing {sample_id} in {DEFAULT_STRATA_CSV}")
            rows.append(
                {
                    "agent": spec.agent,
                    "model": spec.model,
                    "Agent": display_agent(spec.agent),
                    "LLM": display_llm(
                        {"model": spec.model, "run_id": spec.run_id, "note": spec.note}
                    ),
                    "run_id": spec.run_id,
                    "sample_id": sample_id,
                    "quantum_depth": meta["quantum_depth"],
                    "engineering_complexity": meta["engineering_complexity"],
                    "resolved": bool(row["resolved"]),
                    "steps": as_int(row["steps"]),
                    "total_tokens": token_total(row),
                }
            )
    return rows, excluded
