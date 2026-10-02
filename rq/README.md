# Research results for FSE review

The current analysis uses **117 tasks in 11 repositories**, 623 F2P and 994 P2P selectors, and 15 Agent–LLM settings. The active cohort is defined by [the sample index](../benchmark/dataset/samples/index.json). Begin with [the review guide](../docs/README.md).

## Current outputs

| Research question | Inputs and results |
| --- | --- |
| RQ1: overall capability | [117-task merged evaluations](rq1/results/current/evaluations/), [performance table](rq1/results/current/rq1_step_cap_main_table.csv), [step curves](rq1/results/current/rq1_step_curve.csv) |
| RQ2: difficulty | [task covariates](rq2/results/current/engineering_complexity.csv), [stratified results](rq2/results/current/difficulty_by_specificity_complexity.csv), [regression data](rq2/results/current/regression_data.csv), [coefficients](rq2/results/current/regression_coefficients.csv) |
| RQ3: test constraints | [protocol](rq3/README.md), [stored testcase replays](rq3/results/casewise_replays/), [summaries](rq3/results/summary/), [guide](rq3/README.md) |
| RQ4: failure causes | [current audit guide](rq4/README.md), [observations](rq4/results/rq4_dominant_testcases/failure_observations.csv), [summary](rq4/results/rq4_dominant_testcases/observation_summary.json) |

The best setting resolves 69/117 tasks. There are 651 resolved task–setting outcomes and 38 tasks that no setting resolves. RQ4 includes 280 actually failed tests and 1,907 testcase–setting failure observations, with no expansion for evaluator repetitions.

## Regenerate current results

Run from the repository root. The RQ3/RQ4 summary commands and cohort verifier use the Python standard library:

```bash
python3 rq/rq3/scripts/summarize_casewise_by_agent.py
python3 rq/rq3/scripts/summarize_casewise_by_subcategory.py
python3 rq/rq3/scripts/summarize_sample_resolution_by_constraint.py
python3 rq/rq3/scripts/audit_casewise_replays.py
python3 rq/rq4/scripts/prepare_rq4_dominant_testcases.py
python3 rq/rq4/scripts/summarize_rq4_dominant_testcases.py
python3 rq/rq1/scripts/verify_revision.py
```

To regenerate RQ1/RQ2 tables, plots, and regression, install `numpy`, `pandas`, `matplotlib`, `scipy`, and `statsmodels`, then run:

```bash
python3 rq/refresh_extended_paper.py
```

The [recorded agent metrics](rq1/results/current/recorded_agent_metrics.json) preserve the structured steps/token inputs previously available only in local summaries, including source hashes. The refresh reads this snapshot explicitly, so unpublished run directories cannot change its output.

This consumes stored evidence and writes to `rq/rq1/results/current/` and `rq/rq2/results/current/`. It does not call models or require `paper/`. The optional `--update-paper` switch also updates a separately maintained local manuscript. RQ3 figures can be generated with `python3 rq/rq3/scripts/plot_constraint_overview.py` in the same analysis environment.

## Historical inputs and interpretation

- `rq1/results/corrected_evaluations/` contains **106-task corrected inputs**, not the final 117-task release. The refresh script combines these inputs with the recorded extensions and applies [the exclusions](rq1/results/cohort_revision_20261002/exclusions.json).
- Original raw evaluator files under `benchmark/evaluation/*/results/` retain 119 records. Use the active index or current merged results for the review cohort.
- [The preserved 119-task comparison guide](rq1/results/cohort_revision_20261002/README.md) supports record-by-record checks that the cohort revision did not change retained outcomes or root-cause labels.
- The [106-task regression](rq2/results/current/README.md) and [119-task regression](rq2/results/current/README.md) are historical. The current 117-task model adjusts for patch size, test count, and configuration, without repository fixed effects; it estimates an association, not a causal effect.
- [Usage recovery](rq1/results/usage_recovery_20261002/README.md) documents interrupted OpenHands–Gemini runs. Four active records use estimated tokens, explicitly flagged in current outputs. Missing telemetry is not zero usage.
- [RQ3 extension evidence](rq3/README.md) and [RQ4 extension evidence](rq4/README.md) preserve assisted review provenance. Historical author-confirmed agreement is separate from the added review; no synthetic human votes are supplied.

Older RQ1/RQ2 scripts with a default of 106 tasks reproduce historical analyses. Use the current refresh entry point above for FSE review. Timestamps in directory and run names identify evidence batches, not a change in the active cohort.

## Evidence organization

Each RQ keeps its analysis and evidence under its own directory. Current RQ1/RQ2
outputs use `results/current/`; preserved 119-task snapshots use each RQ's
`results/before119/`. RQ3/RQ4 retain their established current result directories.
Shared cohort decisions and cross-RQ checks are indexed from
[RQ1 cohort verification](rq1/results/cohort_revision_20261002/README.md).
[The relocation inventory](../docs/rq-directory-migration.json) records every move.
Historical snapshots retain original provenance paths and must not be used as the
current cohort. The old PDF markup-cleanup comparison was backed up locally and
removed because it supplies no experimental results or analysis inputs.
