#!/usr/bin/env python3
"""Task-clustered logistic regression for the fixed 106-task paper cohort.

Requires numpy, pandas, scipy, patsy, and statsmodels. Run from any directory.
Uses one recorded outcome per task/configuration, never evaluator repeats.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import linprog
from scipy.stats import pointbiserialr, spearmanr
import statsmodels
import statsmodels.api as sm
import statsmodels.formula.api as smf


ROOT = Path(__file__).resolve().parents[3]
RQ1 = ROOT / "rq/rq1/results"
RQ2 = ROOT / "rq/rq2/results"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_data():
    paths = [RQ1 / "rq1_step_cap_main_table.csv", RQ2 / "engineering_complexity.csv"]
    settings = pd.read_csv(paths[0])
    tasks = pd.read_csv(paths[1]).drop(columns="resolved_deepseek_pro")
    require(len(tasks) == tasks.sample_id.nunique() == 106, "Expected 106 unique tasks")
    require(len(settings) == 15, "Expected 15 settings")
    require(set(tasks.quantum_depth) == {"medium", "strong"}, "Unexpected specificity")
    tasks["strong"] = (tasks.quantum_depth == "strong").astype(int)
    reconstructed = sum(
        (np.log1p(tasks[c]) - np.log1p(tasks[c]).mean()) / np.log1p(tasks[c]).std(ddof=0)
        for c in ["gold_solution_lines", "gold_solution_files"]
    )
    require(np.allclose(reconstructed, tasks.engineering_complexity_score), "Patch score mismatch")
    counts, selectors, records = {}, {}, []
    for setting in settings.to_dict("records"):
        key = f"{setting['agent']}_{setting['run_id']}"
        path = RQ1 / "corrected_evaluations" / f"{key}.json"
        paths.append(path)
        rows = json.loads(path.read_text())["results"]
        require(len(rows) == 106 and {r['instance_id'] for r in rows} == set(tasks.sample_id), key)
        require(sum(r["resolved"] for r in rows) == setting["100_resolved"], f"Resolution mismatch: {key}")
        for phase, total in [("fail_pass", 588), ("pass_pass", 929)]:
            require(sum(len(r["test_cases"][phase]) for r in rows) == total, f"Test count: {key}")
        for row in rows:
            sid = row["instance_id"]
            current = {p: sorted(t["selector"] for t in row["test_cases"][p])
                       for p in ["fail_pass", "pass_pass"]}
            require(sid not in selectors or selectors[sid] == current, f"Selector mismatch: {sid}")
            selectors[sid] = current
            counts[sid] = {"f2p_count": len(current["fail_pass"]), "p2p_count": len(current["pass_pass"])}
            if row["resolved"]:
                require(row["agent_submitted"] and row["agent"]["steps"] <= 100, f"Budget mismatch: {sid}")
            records.append(dict(sample_id=sid, setting=key, agent=setting["agent"],
                                model=setting["model"], resolved=int(row["resolved"])))
    tasks = tasks.merge(pd.DataFrame.from_dict(counts, orient="index"),
                        left_on="sample_id", right_index=True, validate="one_to_one")
    tasks["test_count"] = tasks.f2p_count + tasks.p2p_count
    scaling = {}
    for name, values in {
        "patch_z": tasks.engineering_complexity_score,
        "tests_z": np.log1p(tasks.test_count),
        "f2p_z": np.log1p(tasks.f2p_count),
        "p2p_z": np.log1p(tasks.p2p_count),
    }.items():
        scaling[name] = {"mean": float(values.mean()), "sd_population": float(values.std(ddof=0))}
        tasks[name] = (values - values.mean()) / values.std(ddof=0)
    data = pd.DataFrame(records).merge(tasks, on="sample_id", validate="many_to_one")
    require(len(data) == 1590 and not data.isna().any().any(), "Missing/extra regression data")
    require(not data.duplicated(["sample_id", "setting"]).any(), "Duplicate outcomes")
    return tasks, data, paths, scaling


def separation_check(x, y):
    """Feasibility of a nonzero separating margin, including quasi separation."""
    signed = x * (2 * y - 1)[:, None]
    # Nonnegative margins with total >= 1 exist iff (quasi-)separation exists.
    result = linprog(np.zeros(x.shape[1]), A_ub=np.vstack([-signed, -signed.sum(axis=0)]),
                     b_ub=np.r_[np.zeros(len(y)), -1.], bounds=[(None, None)] * x.shape[1],
                     method="highs")
    require(result.status in (0, 2), f"Separation diagnostic failed: {result.message}")
    return bool(result.success)


def fit_model(name, formula, data):
    model = smf.gee(formula, groups="sample_id", data=data, family=sm.families.Binomial(),
                    cov_struct=sm.cov_struct.Independence())
    rank = np.linalg.matrix_rank(model.exog)
    require(rank == model.exog.shape[1], f"Rank-deficient design: {name}")
    separated = separation_check(model.exog, model.endog)
    require(not separated, f"(Quasi-)separation in {name}; ordinary logit inference is invalid")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = model.fit(maxiter=200, ctol=1e-9, cov_type="robust")
    require(result.converged and np.isfinite(result.params).all() and np.isfinite(result.bse).all(),
            f"Unstable fit: {name}")
    # Working-independence GEE must give the same coefficients as binomial GLM.
    glm = sm.GLM(model.endog, model.exog, family=sm.families.Binomial()).fit(tol=1e-10)
    require(np.allclose(result.params, glm.params, atol=1e-7), f"GLM cross-check failed: {name}")
    ci = result.conf_int()
    table = pd.DataFrame({"model": name, "term": result.params.index,
                          "coefficient": result.params.values, "cluster_robust_se": result.bse.values,
                          "odds_ratio": np.exp(result.params.values),
                          "ci95_low": np.exp(ci[0].values), "ci95_high": np.exp(ci[1].values),
                          "p_value": result.pvalues.values})
    info = {"name": name, "formula": formula, "observations": len(data),
            "task_clusters": data.sample_id.nunique(), "resolved": int(data.resolved.sum()),
            "design_columns": model.exog.shape[1], "design_rank": int(rank),
            "design_condition_number": float(np.linalg.cond(model.exog)),
            "separation_detected": separated, "converged": bool(result.converged),
            "warnings": [str(w.message) for w in caught],
            "min_fitted_probability": float(result.fittedvalues.min()),
            "max_fitted_probability": float(result.fittedvalues.max())}
    return table, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RQ2 / "specificity_regression")
    args = parser.parse_args()
    out = args.output_dir
    tasks, data, paths, scaling = build_data()
    # Specifications fixed before viewing fits; sensitivities are not substitutes for the main model.
    main_formula = "resolved ~ strong + patch_z + tests_z + C(repo) + C(setting)"
    specs = [
        ("setting_adjusted", "resolved ~ strong + C(setting)", data),
        ("main", main_formula, data),
        ("separate_test_counts", "resolved ~ strong + patch_z + f2p_z + p2p_z + C(repo) + C(setting)", data),
        ("exclude_qiskit_nature", main_formula, data[data.repo != "qiskit-community/qiskit-nature"]),
    ]
    tables, diagnostics = [], []
    for name, formula, subset in specs:
        table, info = fit_model(name, formula, subset)
        tables.append(table)
        diagnostics.append(info)
    coefficients = pd.concat(tables, ignore_index=True)
    primary = coefficients[coefficients.term == "strong"].merge(
        pd.DataFrame(diagnostics)[["name", "observations", "task_clusters"]],
        left_on="model", right_on="name").drop(columns="name")
    pearson = pointbiserialr(tasks.strong, tasks.engineering_complexity_score)
    spearman = spearmanr(tasks.strong, tasks.engineering_complexity_score)
    diagnostics_dict = {
        "method": "Binomial-logit GEE, working independence, task-cluster robust sandwich SE; Wald 95% CI and two-sided p-values",
        "cohort": "106 original paper tasks; 15 configurations selected by RQ1 100-step table; one recorded result per task/configuration",
        "outcome": "Resolved, including non-submission/failure as zero; evaluator revalidations are not independent agent runs",
        "test_count_unit": "Fixed selected test selectors, not expanded parameterized pytest items; F2P + P2P",
        "scaling": scaling,
        "specificity_patch_correlation": {
            "n_tasks": len(tasks), "point_biserial_r": float(pearson.statistic),
            "point_biserial_p": float(pearson.pvalue), "spearman_rho": float(spearman.statistic),
            "spearman_p": float(spearman.pvalue)},
        "models": diagnostics,
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": scipy.__version__, "statsmodels": statsmodels.__version__},
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "limitations": ["Observational adjusted associations, not causal effects.",
                        "Only 106 independent task clusters; configurations are fixed evaluated settings.",
                        "Finance and Tangelo have no strong tasks; repository overlap must be reported.",
                        "Confidence intervals use asymptotic cluster-robust Wald inference.",
                        "No multiple-testing correction; sensitivity models are diagnostic."]}
    out.mkdir(parents=True, exist_ok=True)
    tasks.sort_values("sample_id").to_csv(out / "task_covariates.csv", index=False)
    data.sort_values(["sample_id", "setting"]).to_csv(out / "regression_data.csv", index=False)
    coefficients.to_csv(out / "all_coefficients.csv", index=False)
    primary.to_csv(out / "specificity_effects.csv", index=False)
    pd.crosstab(tasks.repo, tasks.quantum_depth).to_csv(out / "repository_overlap.csv")
    data.groupby("quantum_depth").resolved.agg(["sum", "count", "mean"]).to_csv(out / "unadjusted_resolution.csv")
    (out / "diagnostics.json").write_text(json.dumps(diagnostics_dict, indent=2) + "\n")
    print(primary.to_string(index=False))
    print(json.dumps(diagnostics_dict["specificity_patch_correlation"], indent=2))
    print("Diagnostics:", json.dumps(diagnostics, indent=2))
    print("Outputs:", out)


if __name__ == "__main__":
    main()
