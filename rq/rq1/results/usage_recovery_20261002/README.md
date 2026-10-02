# OpenHands–Gemini usage recovery

The released 117-task analysis retains **four explicitly estimated token records**.
This archive also preserves the two estimates for excluded tasks from the
119-task predecessor. Missing telemetry is unknown usage, not zero usage.

Six extension workflows exited after network interruptions with empty final
history and null metrics. The converter wrote placeholder zero steps/tokens.
Continuous `OPENHANDS_PROGRESS` events recovered completed assistant turns:
`tequila_400_411=9`, `openqaoa_36_71=28`, `openqaoa_112_85=9`,
`squlearn_266_301=23`, `squlearn_62_99=14`, and `squlearn_275_339=53`.
Source hashes and recovery records are retained in `openhands_gemini_recovery.json`.

Three complete generation IDs for `openqaoa_36_71` yielded 100,230 measured input
tokens, 3,992 output tokens, and a recorded cost of $0.02425365. These are partial
calls, not full-workflow usage. Together with seven complete extension workflows,
they establish a historical known-cost lower bound of $1.20193115; the full bill
remains unknown. The recorded credential could not access activity/analytics,
and the interrupted trajectories did not preserve full request histories.

## Estimation and interpretation

Seven complete workflows from the same configuration provide cumulative
input/output/cache-token references at matching step prefixes. Missing usage uses
the median reference prefix; the 53-step estimate has two reference trajectories,
and the others have four to seven. For `openqaoa_36_71`, the three measured calls
are retained and the remaining 25 steps are estimated. The 30-step column uses a
30-step prefix rather than all 53 steps.

`openhands_gemini_token_estimates.json` and `token_estimates.csv` preserve the
estimates and reference ranges. Reference minima/maxima are sensitivity scenarios,
not statistical confidence intervals. Failed requests with no returned usage are
not exactly recovered. Original evaluator results and trajectories remain unchanged.
The refresh script adds labelled estimates only to analysis copies and efficiency
statistics; it does not change submission, resolution, testcase outcomes, or labels.

## Verification

Run from the repository root:

```bash
python3 rq/refresh_extended_paper.py
python3 rq/rq1/results/usage_recovery_20261002/verify_estimates.py
```

These commands use released structured evidence. `recover_steps.py` and
`estimate_tokens.py` document the original reconstruction, which requires the
corresponding local logs/trajectories; they are not necessary for offline release
verification. Historical 119-task means remain in the preserved snapshots and
must not be substituted for active-cohort means.
