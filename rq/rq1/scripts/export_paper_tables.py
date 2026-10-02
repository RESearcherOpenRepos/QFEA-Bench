#!/usr/bin/env python3
"""Export the current RQ1 overall and RQ2 task-property tables."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from rq.rq1.scripts.analyze_rq1 import (  # noqa: E402
    DEFAULT_RUNS,
    enriched_rows,
    token_total,
)
from rq.rq2.scripts.analyze_rq2 import (  # noqa: E402
    DEFAULT_STRATA_CSV,
    ENGINEERING_COMPLEXITIES,
    QUANTUM_DEPTHS,
    complete_run_rows,
    load_strata,
)


RQ_ROOT = ROOT / "rq"
TOTAL_INSTANCES = 106
RQ2_GROUP_SIZES = {
    ("medium", "small"): 26,
    ("medium", "medium"): 21,
    ("medium", "large"): 16,
    ("strong", "small"): 10,
    ("strong", "medium"): 14,
    ("strong", "large"): 19,
}

AGENT_LABELS = {
    "mini-swe": "Mini-SWE-Agent",
    "openhands": "OpenHands",
    "autocoderover": "AutoCodeRover",
}

MODEL_LABELS = {
    "gpt-5.5": "GPT-5.5",
    "glm-5.2": "GLM-5.2",
    "gemini-3-flash-preview": "Gemini-3-Flash",
    "deepseek-v4-pro": "DeepSeek-v4-Pro",
    "deepseek-v4-flash": "DeepSeek-v4-Flash",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def as_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def pct(rate: float) -> str:
    return f"{100 * rate:.1f}%"


def count_rate(count: int, total: int) -> str:
    return f"{count}/{total} ({pct(count / total if total else 0.0)})"


def count_percent(count: int, rate: float) -> str:
    return f"{count} ({pct(rate)})"


def fmt_step(value: Any) -> str:
    return f"{as_float(value):.2f}"


def fmt_token(value: Any) -> str:
    return f"{round(as_float(value)):,}"


def fmt_cost(value: Any) -> str:
    return f"{as_float(value):.3f}"


def export_rq1_overall() -> Path:
    main_rows = read_csv(RQ_ROOT / "rq1" / "results" / "rq1_step_cap_main_table.csv")
    cost_rows = read_csv(RQ_ROOT / "rq1" / "results" / "cost_summary.csv")
    cap_rows = read_csv(RQ_ROOT / "rq1" / "results" / "step_cap_sensitivity.csv")

    cost_by_key = {
        (row["Agent"], row["LLM"], row["run_id"]): row for row in cost_rows
    }
    cap_cost_by_key = {
        (row["agent"], row["model"], row["run_id"], row["step_cap"]): row
        for row in cap_rows
    }

    rows: list[dict[str, Any]] = []
    for row in main_rows:
        agent = row["agent"]
        model = row["model"]
        run_id = row["run_id"]
        agent_label = AGENT_LABELS[agent]
        model_label = MODEL_LABELS[model]
        cost_row = cost_by_key[(agent_label, model, run_id)]
        cap_cost_row = cap_cost_by_key[(agent, model, run_id, "30")]
        rows.append(
            {
                "Agent": agent_label,
                "LLM": model_label,
                "Run ID": run_id,
                "100 Submitted": count_percent(
                    as_int(row["100_submitted"]), as_float(row["100_submitted_rate"])
                ),
                "100 Resolved": count_percent(
                    as_int(row["100_resolved"]), as_float(row["100_resolved_rate"])
                ),
                "100 F2P": pct(as_float(row["100_f2p"])),
                "100 P2P": pct(as_float(row["100_p2p"])),
                "100 Avg. Step": fmt_step(row["100_avg_steps"]),
                "100 Avg. Token": fmt_token(row["100_avg_tokens"]),
                "100 Avg. Cost": fmt_cost(cost_row["avg_cost"]),
                "30 Submitted": count_percent(
                    as_int(row["30_submitted"]), as_float(row["30_submitted_rate"])
                ),
                "30 Resolved": count_percent(
                    as_int(row["30_resolved"]), as_float(row["30_resolved_rate"])
                ),
                "30 F2P": pct(as_float(row["30_f2p"])),
                "30 P2P": pct(as_float(row["30_p2p"])),
                "30 Avg. Step": fmt_step(row["30_avg_steps"]),
                "30 Avg. Token": fmt_token(row["30_avg_tokens"]),
                "30 Avg. Cost": fmt_cost(cap_cost_row["avg_cost_at_cap_usd"]),
            }
        )

    output = RQ_ROOT / "rq1" / "results" / "overall_results.csv"
    write_csv(output, rows)
    return output


def export_rq2_difficulty() -> Path:
    main_rows = read_csv(RQ_ROOT / "rq1" / "results" / "rq1_step_cap_main_table.csv")
    if len(main_rows) != 15:
        raise ValueError(f"Expected 15 paper settings, got {len(main_rows)}")
    all_rows, excluded = complete_run_rows(load_strata(DEFAULT_STRATA_CSV))
    if excluded:
        raise ValueError(f"Incomplete RQ2 runs: {excluded}")
    rows_by_run: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        rows_by_run[(row["agent"], row["model"], row["run_id"])].append(row)

    output_rows: list[dict[str, Any]] = []
    for selected in main_rows:
        agent, model, run_id = (
            selected["agent"],
            selected["model"],
            selected["run_id"],
        )
        rows = rows_by_run[(agent, model, run_id)]
        if len(rows) != TOTAL_INSTANCES:
            raise ValueError(f"{agent}/{model}/{run_id}: expected 106 rows, got {len(rows)}")
        resolved_total = sum(bool(row["resolved"]) for row in rows)
        if resolved_total != as_int(selected["100_resolved"]):
            raise ValueError(f"{agent}/{model}/{run_id}: RQ2 count differs from RQ1")
        record: dict[str, Any] = {
            "Agent": AGENT_LABELS[agent],
            "LLM": MODEL_LABELS[model],
            "Run ID": run_id,
        }
        for quantum_depth in QUANTUM_DEPTHS:
            depth_resolved = 0
            depth_total = 0
            for complexity in ENGINEERING_COMPLEXITIES:
                group = [
                    row
                    for row in rows
                    if row["quantum_depth"] == quantum_depth
                    and row["engineering_complexity"] == complexity
                ]
                expected_total = RQ2_GROUP_SIZES[(quantum_depth, complexity)]
                if len(group) != expected_total:
                    raise ValueError(
                        f"{agent}/{model}: {quantum_depth}/{complexity} "
                        f"has {len(group)} instances, expected {expected_total}"
                    )
                resolved = sum(bool(row["resolved"]) for row in group)
                total = len(group)
                record[f"{quantum_depth.title()} {complexity.title()}"] = count_rate(resolved, total)
                depth_resolved += resolved
                depth_total += total
            record[f"{quantum_depth.title()} Total"] = count_rate(depth_resolved, depth_total)
        for complexity in ENGINEERING_COMPLEXITIES:
            group = [row for row in rows if row["engineering_complexity"] == complexity]
            resolved = sum(bool(row["resolved"]) for row in group)
            record[f"Overall {complexity.title()}"] = count_rate(resolved, len(group))
        record["Overall"] = count_rate(resolved_total, TOTAL_INSTANCES)
        output_rows.append(record)

    output = RQ_ROOT / "rq2" / "results" / "difficulty_by_specificity_complexity.csv"
    write_csv(output, output_rows)
    write_rq2_difficulty_latex(output_rows)
    return output


def write_rq2_difficulty_latex(rows: list[dict[str, Any]], output: Path | None = None) -> None:
    def mini_cell(row: dict[str, Any], key: str, shade: bool) -> str:
        count, percentage = row[key].split(" (", 1)
        percentage = percentage.removesuffix(")").removesuffix("%")
        content = f"\\rqtwocell{{{count}}}{{{percentage}\\%}}"
        if not shade:
            return content
        rate = float(percentage)
        color = (
            "rqheatlow" if rate < 20 else
            "rqheatmidlow" if rate < 40 else
            "rqheatmid" if rate < 60 else
            "rqheatmidhigh" if rate < 80 else
            "rqheathigh"
        )
        return f"\\cellcolor{{{color}}}{content}"

    agents = ("Mini-SWE-Agent", "OpenHands", "AutoCodeRover")
    lines = [
        "% Generated by rq/rq1/scripts/export_paper_tables.py from complete 100-step runs.",
        "\\begin{table}[t]",
        "\\caption{Resolved/total (rate) by quantum specificity and patch size across all 15 Agent--LLM settings. Each panel has specificity rows M/S/All and patch-size columns Sm/Md/Lg/All. Darker green denotes higher rates. DS abbreviates DeepSeek.}",
        "\\label{tab:rq2-difficulty}",
        "\\centering",
        "\\scriptsize",
        "\\setlength{\\arrayrulewidth}{0.4pt}",
        "\\setlength{\\tabcolsep}{1.3pt}",
        "\\renewcommand{\\arraystretch}{1.0}",
        "\\resizebox{\\columnwidth}{!}{%",
        "\\begin{tabular}{@{}l|lcccc@{\\hspace{0.7em}}lcccc@{\\hspace{0.7em}}lcccc@{}}",
        "\\hline",
        "\\multirow{2}{*}{\\textbf{LLM}} & "
        + " & ".join(f"\\multicolumn{{5}}{{c}}{{\\textbf{{{agent}}}}}" for agent in agents)
        + " \\\\",
        "\\cline{2-16}",
        " & " + " & ".join(
            cell for _ in agents
            for cell in ("", "\\textbf{Sm}", "\\textbf{Md}", "\\textbf{Lg}", "\\textbf{All}")
        ) + " \\\\",
        "\\hline",
    ]
    by_key = {(row["Agent"], row["LLM"]): row for row in rows}
    models = (
        ("GPT-5.5", "GPT-5.5"),
        ("GLM-5.2", "GLM-5.2"),
        ("Gemini-3-Flash", "Gemini-3-Flash"),
        ("DeepSeek-v4-Pro", "DS-v4-Pro"),
        ("DeepSeek-v4-Flash", "DS-v4-Flash"),
    )
    for model, short_model in models:
        for row_index, (label, depth) in enumerate(
            (("M", "Medium"), ("S", "Strong"), ("All", "Overall"))
        ):
            cells = [f"\\multirow{{3}}{{*}}{{{short_model}}}" if row_index == 0 else ""]
            for agent in agents:
                record = by_key[(agent, model)]
                cells.append(f"\\textbf{{{label}}}")
                cells.extend(
                    mini_cell(record, f"{depth} {complexity.title()}", depth == "Overall")
                    for complexity in ENGINEERING_COMPLEXITIES
                )
                total_key = f"{depth} Total" if depth != "Overall" else "Overall"
                cells.append(mini_cell(record, total_key, depth != "Overall"))
            lines.append(" & ".join(cells) + " \\\\")
        lines.append("\\hline")
    lines.extend(["\\end{tabular}}", "\\end{table}"])
    output = output or RQ_ROOT / "rq2" / "results" / "rq2_difficulty_all_settings.tex"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_rq1_test_cells(*, include_resolution: bool = False) -> None:
    """Update Table 2 test rates and optionally resolution, retaining the layout."""
    rows = read_csv(RQ_ROOT / "rq1/results/rq1_step_cap_main_table.csv")
    path = ROOT / "paper/6_evaluation_results.tex"
    source = path.read_text()
    label = source.index(r"\label{tab:overall-results}")
    end = source.index(r"\end{table}", label)
    lines = source[label:end].splitlines(keepends=True)
    fields = ((4, "100_f2p"), (5, "100_p2p"), (10, "30_f2p"), (11, "30_p2p"))
    if include_resolution:
        fields += ((3, "100_resolved_rate"), (9, "30_resolved_rate"))
    maxima = {(agent, field): max(float(r[field]) for r in rows if r["agent"] == agent)
              for agent in AGENT_LABELS for _, field in fields}
    index = 0
    for n, line in enumerate(lines):
        cells = line.split(" & ")
        if len(cells) != 14 or not any(label in cells[1] for label in MODEL_LABELS.values()):
            continue
        row = rows[index]
        if MODEL_LABELS[row["model"]] not in cells[1]:
            raise ValueError("Table 2 model order differs from the result CSV")
        background = r"\cellcolor{tablerowgray}" if r"\cellcolor{tablerowgray}" in cells[1] else ""
        for column, field in fields:
            value = float(row[field])
            color = r"\cellcolor{rowmaxfill}" if value == maxima[row["agent"], field] else background
            number = f"{100 * value:.1f}" + r"\%"
            if "resolved" in field and value == maxima[row["agent"], field]:
                number = r"\textbf{" + number + "}"
            cells[column] = color + number
        lines[n] = " & ".join(cells)
        index += 1
    if index != len(rows) or index != 15:
        raise ValueError(f"Expected to update 15 Table 2 rows, found {index}")
    path.write_text(source[:label] + "".join(lines) + source[end:])


def update_rq3_sample_table() -> None:
    rows = read_csv(RQ_ROOT / "rq3/results/summary/sample_resolution_by_f2p_quantum_constraint.csv")
    data = {(r["agent"],r["has_quantum_semantic_f2p"]):r for r in rows
            if r["quantum_specificity"] == "all"}
    path = ROOT / "paper/6_evaluation_results.tex"
    source = path.read_text()
    lines = source.splitlines(keepends=True)
    for i,line in enumerate(lines):
        for label,key in (("With quantum-semantic F2P tests", "true"),
                          ("Without quantum-semantic F2P tests", "false")):
            if not line.startswith(label+" & "):
                continue
            pooled = data["all_agents",key]
            total,never = int(pooled["samples"]),int(pooled["never_resolved_samples"])
            rates = [f'{100*float(data[agent,key]["resolved_rate"]):.1f}'
                     for agent in ("mini-swe","openhands","autocoderover")]
            lines[i] = " & ".join([label,str(total),*rates,
                                  f"{never}/{total} ({100*never/total:.1f}\\%)"])+" \\\\\n"
    path.write_text("".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-rq1-paper", action="store_true",
                        help="Export RQ1 CSV and update only Table 2 F2P/P2P cells")
    parser.add_argument("--update-resolution-paper", action="store_true",
                        help="Update Tables 2--4 from reconciled outcomes (rebuild RQ3 summaries first)")
    args = parser.parse_args()
    if args.update_resolution_paper:
        export_rq1_overall()
        export_rq2_difficulty()
        update_rq1_test_cells(include_resolution=True)
        table = RQ_ROOT / "rq2/results/rq2_difficulty_all_settings.tex"
        paper = ROOT / "paper/6_evaluation_results.tex"
        source = paper.read_text()
        start = source.index("% Generated by rq/rq1/scripts/export_paper_tables.py")
        end = source.index(r"\end{table}", start) + len(r"\end{table}")
        paper.write_text(source[:start] + table.read_text().rstrip() + source[end:])
        table.unlink()
        update_rq3_sample_table()
        return
    if args.update_rq1_paper:
        print(export_rq1_overall())
        update_rq1_test_cells()
        return
    outputs = [
        export_rq1_overall(),
        export_rq2_difficulty(),
    ]
    for path in outputs:
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
