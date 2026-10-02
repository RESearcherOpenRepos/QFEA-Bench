# RQ2: current difficulty results

FSE review cohort: **117 tasks, 15 settings, 1,755 outcomes**.

- `engineering_complexity.csv`: task covariates for RQ2 and the RQ3 stratified checks.
- `difficulty_by_specificity_complexity.csv` and `rq2_difficulty_all_settings.tex`: paper Table 3.
- `rq2_quantum_specificity_split_index_heatmap.pdf`: paper Figure 4.
- `regression_data.csv` and `regression_coefficients.csv`: the reported adjusted association.
- `regression_check.json`: the retained independent regression check from the paper consistency audit.
- `reference_diffs/`: reference patches used to measure extension-task complexity. Two excluded-task patches remain as historical inputs; current analyses select active tasks.

Run `python3 rq/refresh_extended_paper.py` from the repository root. It reads the
[RQ1 outcome and metric inputs](../../../rq1/results/current/README.md) and records
shared diagnostics in [RQ1 audit.json](../../../rq1/results/current/audit.json).
The current model adjusts for patch size, test count, and setting, without repository
fixed effects. It is an association, not a causal estimate.

The [119-task snapshot](../before119/) and
[full119 regression diagnostic](README.md) preserve
the basis for the specification change. Files directly under `rq2/results/` that
predate this directory describe the historical 106-task analysis.
