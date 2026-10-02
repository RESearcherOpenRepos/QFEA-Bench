#!/usr/bin/env python3
"""Plot step-limit results for the two interactive agents and five models."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PLOT_CACHE_DIR = Path(tempfile.gettempdir()) / "qfea-rq-plot-cache" / "rq1"
PLOT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(PLOT_CACHE_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(PLOT_CACHE_DIR / "matplotlib"))
sys.path.insert(0, str(ROOT))

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt

from rq.rq1.scripts.analyze_rq1 import DEFAULT_RUNS, DEFAULT_TOTAL_EXPECTED, enriched_rows
MODEL_ORDER = (
    "gpt-5.5",
    "glm-5.2",
    "gemini-3-flash-preview",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
)


MODEL_LABELS = {
    "gpt-5.5": "GPT-5.5",
    "glm-5.2": "GLM-5.2",
    "gemini-3-flash-preview": "Gemini-3-Flash",
    "deepseek-v4-pro": "DS-v4-Pro",
    "deepseek-v4-flash": "DS-v4-Flash",
}


MODEL_COLORS = {
    "gpt-5.5": "#D55E00",
    "glm-5.2": "#6A3D9A",
    "gemini-3-flash-preview": "#0072B2",
    "deepseek-v4-pro": "#009E73",
    "deepseek-v4-flash": "#CC79A7",
}


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7.4,
            "axes.linewidth": 0.65,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )



DEFAULT_MAIN_TABLE = ROOT / "rq" / "rq1" / "results" / "rq1_step_cap_main_table.csv"
DEFAULT_OUTPUT_PREFIX = ROOT / "rq" / "rq1" / "results" / "rq1_interactive_agents_step_limit_sweep"
PAPER_OUTPUT_PREFIX = ROOT / "paper" / "figures" / "rq1_interactive_agents_step_limit_sweep"
STEP_CAPS = tuple(range(10, 101, 10))
AGENT_ORDER = ("mini-swe", "openhands")
AGENT_LABELS = {
    "mini-swe": "Mini-SWE-Agent",
    "openhands": "OpenHands",
}


def selected_runs(main_table: Path) -> tuple[list[Any], dict[tuple[str, str], dict[str, str]]]:
    with main_table.open("r", encoding="utf-8", newline="") as handle:
        main_rows = list(csv.DictReader(handle))
    selected = {
        (row["agent"], row["model"]): row
        for row in main_rows
        if row["agent"] in AGENT_ORDER and row["model"] in MODEL_ORDER
    }
    specs = {(spec.agent, spec.model, spec.run_id): spec for spec in DEFAULT_RUNS}
    runs = []
    for agent in AGENT_ORDER:
        for model in MODEL_ORDER:
            row = selected[(agent, model)]
            runs.append(specs[(agent, model, row["run_id"])])
    return runs, selected


def compute_rows(main_table: Path) -> list[dict[str, Any]]:
    runs, main_rows = selected_runs(main_table)
    output = []
    for spec in runs:
        task_rows = enriched_rows(spec)
        if len(task_rows) != DEFAULT_TOTAL_EXPECTED:
            raise ValueError(f"{spec.agent}/{spec.model}: expected 106 tasks, got {len(task_rows)}")
        known_rows = [row for row in task_rows if row["metrics_known"]]
        if len(known_rows) != DEFAULT_TOTAL_EXPECTED:
            raise ValueError(f"{spec.agent}/{spec.model}: missing step metrics")
        for cap in STEP_CAPS:
            resolved = sum(row["resolved"] and row["steps"] <= cap for row in known_rows)
            output.append(
                {
                    "agent": spec.agent,
                    "model": spec.model,
                    "run_id": spec.run_id,
                    "step_cap": cap,
                    "resolved": resolved,
                    "resolved_rate": resolved / DEFAULT_TOTAL_EXPECTED,
                }
            )
            if cap in (30, 100):
                reported = int(main_rows[(spec.agent, spec.model)][f"{cap}_resolved"])
                if resolved != reported:
                    raise ValueError(
                        f"{spec.agent}/{spec.model} at {cap} steps: "
                        f"computed {resolved}, reported {reported}"
                    )
    return output


def write_rows(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("agent", "model", "run_id", "step_cap", "resolved", "resolved_rate"),
        )
        writer.writeheader()
        writer.writerows(rows)


def draw(rows: list[dict[str, Any]], output_prefix: Path) -> None:
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(5.15, 1.5), sharex=True, sharey=False)
    for index, (agent, ax) in enumerate(zip(AGENT_ORDER, axes, strict=True)):
        ax.axvline(30, color="#9AA3AD", linewidth=0.8, linestyle="--", zorder=0)
        for model in MODEL_ORDER:
            series = sorted(
                (row for row in rows if row["agent"] == agent and row["model"] == model),
                key=lambda row: row["step_cap"],
            )
            ax.plot(
                [row["step_cap"] for row in series],
                [row["resolved"] for row in series],
                color=MODEL_COLORS[model],
                marker="o",
                markersize=2.0,
                linewidth=1.1,
                label=MODEL_LABELS[model],
            )
        ax.set_title(f"({chr(ord('a') + index)}) {AGENT_LABELS[agent]}", loc="left", fontsize=7.2, pad=4)
        ax.set_xlim(8, 102)
        ax.set_ylim(0, max(62, max(row["resolved"] for row in rows) + 3))
        ax.set_yticks((0, 20, 40, 60))
        ax.set_ylabel("Resolved instances", fontsize=7.2)
        ax.set_xticks((10, 30, 50, 70, 100))
        ax.grid(axis="y", color="#D8DEE4", linewidth=0.45)
        ax.tick_params(labelsize=6.4)

    fig.supxlabel("Step limit", y=0.035, fontsize=7.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.005),
        ncol=5,
        frameon=False,
        fontsize=7,
        handlelength=1.4,
        handletextpad=0.4,
        columnspacing=0.8,
    )
    fig.subplots_adjust(left=0.105, right=0.99, top=0.74, bottom=0.28, wspace=0.28)

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    PAPER_OUTPUT_PREFIX.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_prefix.with_suffix(".pdf"))
    fig.savefig(PAPER_OUTPUT_PREFIX.with_suffix(".pdf"))
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-table", type=Path, default=DEFAULT_MAIN_TABLE)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_PREFIX.with_suffix(".csv"),
    )
    args = parser.parse_args()
    rows = compute_rows(args.main_table)
    write_rows(rows, args.output_csv)
    draw(rows, args.output_prefix)
    print(f"Wrote {len(rows)} points to {args.output_csv}")
    print(f"Wrote figure to {PAPER_OUTPUT_PREFIX.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
