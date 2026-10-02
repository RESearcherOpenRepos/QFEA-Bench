#!/usr/bin/env python3
"""Plot Strong/Medium split heatmaps with every instance index shown."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PLOT_CACHE_DIR = Path(tempfile.gettempdir()) / "qfea-rq-plot-cache" / "rq2"
PLOT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(PLOT_CACHE_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(PLOT_CACHE_DIR / "matplotlib"))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))

from rq.rq1.scripts.analyze_rq1 import (
    DEFAULT_RUNS,
    enriched_rows,
)

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch


DEFAULT_OUTPUT_PREFIX = (
    ROOT
    / "rq"
    / "rq2"
    / "results"
    / "rq2_quantum_specificity_split_index_heatmap"
)
DEFAULT_STRATA_CSV = ROOT / "rq" / "rq2" / "results" / "engineering_complexity.csv"
DEFAULT_SAMPLE_INDEX = ROOT / "benchmark" / "dataset" / "samples" / "index.json"
DEFAULT_TOTAL_EXPECTED = 106

AGENT_ORDER = ("mini-swe", "openhands", "autocoderover")
MODEL_ORDER = (
    "gpt-5.5",
    "glm-5.2",
    "gemini-3-flash-preview",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
)
AGENT_LABELS = {
    "mini-swe": "Mini-SWE",
    "openhands": "OpenHands",
    "autocoderover": "ACR",
}
MODEL_LABELS = {
    "gpt-5.5": "GPT-5.5",
    "glm-5.2": "GLM-5.2",
    "gemini-3-flash-preview": "Gemini-3",
    "deepseek-v4-pro": "DS-v4-Pro",
    "deepseek-v4-flash": "DS-v4-Flash",
}

UNRESOLVED_COLOR = "#F6FAFD"
MEDIUM_RESOLVED_COLOR = "#40C463"
STRONG_RESOLVED_COLOR = "#216E39"
GRID_COLOR = "#8A8A8A"
SUMMARY_CMAP = LinearSegmentedColormap.from_list(
    "github_middle_greens",
    ["#EBEDF0", MEDIUM_RESOLVED_COLOR, STRONG_RESOLVED_COLOR],
)


def load_strata(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["sample_id"]: row for row in csv.DictReader(handle)}


def load_sample_index(path: Path) -> dict[str, int]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    samples = payload.get("samples", [])
    sample_index = {str(sample["sample_id"]): sample["id"] for sample in samples}
    ids = list(sample_index.values())
    if len(sample_index) != len(samples) or len(set(ids)) != len(ids) or any(type(i) is not int or i < 1 for i in ids):
        raise ValueError("Sample index must contain unique positive stable IDs")
    return sample_index


def run_sort_key(run: dict[str, Any]) -> tuple[int, int, str]:
    return (
        MODEL_ORDER.index(run["model"]),
        AGENT_ORDER.index(run["agent"]),
        run["run_id"],
    )


def load_complete_runs() -> list[dict[str, Any]]:
    runs = []
    for spec in DEFAULT_RUNS:
        if spec.agent not in AGENT_ORDER or spec.model not in MODEL_ORDER:
            continue
        if not spec.result_path.exists():
            continue

        rows = enriched_rows(spec)
        metrics_known = sum(row["metrics_known"] for row in rows)
        if len(rows) != DEFAULT_TOTAL_EXPECTED or metrics_known != DEFAULT_TOTAL_EXPECTED:
            continue

        resolved = {
            str(row["item"]["instance_id"]): bool(row["resolved"])
            for row in rows
        }
        runs.append(
            {
                "agent": spec.agent,
                "model": spec.model,
                "run_id": spec.run_id,
                "label": f"{MODEL_LABELS[spec.model]} / {AGENT_LABELS[spec.agent]}",
                "resolved": resolved,
            }
        )
    return sorted(runs, key=run_sort_key)


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7.5,
            "axes.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def count_resolved(
    run: dict[str, object],
    sample_ids: list[str],
    depth: str,
    strata: dict[str, dict[str, str]],
) -> int:
    resolved = run["resolved"]
    assert isinstance(resolved, dict)
    return sum(
        bool(resolved.get(sample_id, False)) and strata[sample_id]["quantum_depth"] == depth
        for sample_id in sample_ids
    )


def add_cell_grid(ax: plt.Axes, n_rows: int, n_cols: int) -> None:
    ax.set_xticks([x - 0.5 for x in range(1, n_cols)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, n_rows)], minor=True)
    ax.grid(which="minor", color=GRID_COLOR, linewidth=0.32)
    ax.tick_params(which="minor", bottom=False, left=False)


def box_axes(ax: plt.Axes) -> None:
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#111111")
        spine.set_linewidth(0.8)


def group_boundaries(runs: list[dict[str, object]]) -> list[float]:
    boundaries: list[float] = []
    previous_model: object | None = None
    for index, run in enumerate(runs):
        model = run["model"]
        if index > 0 and model != previous_model:
            boundaries.append(index - 0.5)
        previous_model = model
    return boundaries


def depth_sample_ids(
    depth: str,
    strata: dict[str, dict[str, str]],
    sample_index: dict[str, int],
) -> list[str]:
    sample_ids = [
        sample_id
        for sample_id, meta in strata.items()
        if meta.get("quantum_depth") == depth
    ]
    return sorted(sample_ids, key=lambda sample_id: sample_index.get(sample_id, 10**9))


def build_matrix(
    runs: list[dict[str, object]],
    sample_ids: list[str],
) -> np.ndarray:
    rows = []
    for run in runs:
        resolved = run["resolved"]
        assert isinstance(resolved, dict)
        rows.append([1 if resolved.get(sample_id, False) else 0 for sample_id in sample_ids])
    return np.asarray(rows, dtype=int)


def draw_panel(
    ax: plt.Axes,
    runs: list[dict[str, object]],
    sample_ids: list[str],
    sample_index: dict[str, int],
    title: str,
    resolved_color: str,
    show_y_labels: bool,
) -> None:
    matrix = build_matrix(runs, sample_ids)
    n_rows, n_cols = matrix.shape
    cmap = ListedColormap([UNRESOLVED_COLOR, resolved_color])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    add_cell_grid(ax, n_rows, n_cols)

    for boundary in group_boundaries(runs):
        ax.axhline(boundary, color="#3D3D3D", linewidth=0.9)

    ax.set_title(title, fontsize=7.4, fontweight="bold", pad=5)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(
        [str(sample_index[sample_id]) for sample_id in sample_ids],
        fontsize=2.9,
        ha="center",
        va="top",
    )
    ax.tick_params(axis="x", length=1.8, pad=1)

    ax.set_yticks(range(n_rows))
    if show_y_labels:
        ax.set_yticklabels([str(run["label"]) for run in runs], fontsize=4.8)
        ax.set_ylabel("Model / Agent", fontsize=4.8, labelpad=4)
    else:
        ax.tick_params(axis="y", labelleft=False, length=0)

    ax.set_xlim(-0.5, n_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    box_axes(ax)


def draw_depth_summary(
    ax: plt.Axes,
    runs: list[dict[str, object]],
    sample_ids: list[str],
    depth: str,
    strata: dict[str, dict[str, str]],
    title: str,
) -> None:
    total = len(sample_ids)
    values = np.asarray(
        [[count_resolved(run, sample_ids, depth, strata) / total] for run in runs],
        dtype=float,
    )
    ax.imshow(values, cmap=SUMMARY_CMAP, vmin=0, vmax=1, aspect="auto", interpolation="nearest")

    n_rows = len(runs)
    ax.set_xticks([0])
    ax.set_xticklabels([title], fontsize=5.1)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=2)
    ax.set_yticks([])
    ax.set_yticks([y - 0.5 for y in range(1, n_rows)], minor=True)
    ax.grid(which="minor", color=GRID_COLOR, linewidth=0.35)
    ax.tick_params(which="minor", bottom=False, left=False)
    for boundary in group_boundaries(runs):
        ax.axhline(boundary, color="#3D3D3D", linewidth=0.9)

    for y, run in enumerate(runs):
        resolved_count = count_resolved(run, sample_ids, depth, strata)
        ax.text(0, y, f"{resolved_count}", ha="center", va="center", fontsize=5.1)

    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    box_axes(ax)


def plot(strata_csv: Path, sample_index_path: Path, output_prefix: Path) -> None:
    setup_style()
    strata = load_strata(strata_csv)
    sample_index = load_sample_index(sample_index_path)
    runs = load_complete_runs()
    strong_ids = depth_sample_ids("strong", strata, sample_index)
    medium_ids = depth_sample_ids("medium", strata, sample_index)

    fig = plt.figure(figsize=(9.1, 3.15))
    grid = fig.add_gridspec(
        1,
        4,
        width_ratios=[len(strong_ids), 2.1, len(medium_ids), 2.1],
        wspace=0.045,
    )
    strong_ax = fig.add_subplot(grid[0, 0])
    strong_summary_ax = fig.add_subplot(grid[0, 1])
    medium_ax = fig.add_subplot(grid[0, 2], sharey=strong_ax)
    medium_summary_ax = fig.add_subplot(grid[0, 3])

    draw_panel(
        strong_ax,
        runs,
        strong_ids,
        sample_index,
        "Quantum specificity = Strong",
        STRONG_RESOLVED_COLOR,
        True,
    )
    draw_panel(
        medium_ax,
        runs,
        medium_ids,
        sample_index,
        "Quantum specificity = Medium",
        MEDIUM_RESOLVED_COLOR,
        False,
    )
    draw_depth_summary(strong_summary_ax, runs, strong_ids, "strong", strata, "Total")
    draw_depth_summary(medium_summary_ax, runs, medium_ids, "medium", strata, "Total")

    legend_handles = [
        Patch(
            facecolor=STRONG_RESOLVED_COLOR,
            edgecolor=STRONG_RESOLVED_COLOR,
            label="Strong resolved",
        ),
        Patch(
            facecolor=MEDIUM_RESOLVED_COLOR,
            edgecolor=MEDIUM_RESOLVED_COLOR,
            label="Medium resolved",
        ),
        Patch(facecolor=UNRESOLVED_COLOR, edgecolor=GRID_COLOR, label="Unresolved"),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=7.0,
        bbox_to_anchor=(0.52, 0.965),
        handlelength=1.6,
        columnspacing=1.0,
    )
    fig.supxlabel("Instance index", fontsize=4.8, y=0.122)
    fig.subplots_adjust(left=0.145, right=0.99, top=0.83, bottom=0.18)

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{output_prefix}.pdf", bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strata-csv", type=Path, default=DEFAULT_STRATA_CSV)
    parser.add_argument("--sample-index", type=Path, default=DEFAULT_SAMPLE_INDEX)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_OUTPUT_PREFIX)
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    args = parse_args()
    plot(
        resolve_path(args.strata_csv),
        resolve_path(args.sample_index),
        resolve_path(args.output_prefix),
    )


if __name__ == "__main__":
    main()
