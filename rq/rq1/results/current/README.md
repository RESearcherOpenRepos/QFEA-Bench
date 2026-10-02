# RQ1: current performance results

FSE review cohort: **117 tasks, 15 settings, 1,755 outcomes**.

- `evaluations/`: active outcomes and testcase statuses, used by RQ1 and downstream RQ2–RQ4 analyses.
- `rq1_step_cap_main_table.csv`: paper Table 2 (100-step and 30-step trajectory truncation).
- `rq1_step_curve.csv` and `rq1_interactive_agents_step_limit_sweep.pdf`: paper Figure 3.
- `recorded_agent_metrics.json`: released steps/token input snapshot; required for offline regeneration.
- `rq1_tool_usage_117.json`: recorded tool counts supporting the RQ1 behavioral discussion. Recomputing tool counts requires unpublished full trajectories; the saved report remains inspectable.
- `all_runs_overview.csv`: setting-to-outcome mapping used by RQ3/RQ4.
- `audit.json`: shared input hashes, cohort checks, overlap statistics, and RQ2 regression diagnostics.

Run `python3 rq/refresh_extended_paper.py` from the repository root to regenerate
performance results here and [RQ2 outputs](../../../rq2/results/current/README.md).
The [cohort guide](../cohort_revision_20261002/README.md) indexes the preserved
119-task evidence. Historical inputs directly under `rq1/results/` describe the
106-task predecessor; they are not current denominators.
