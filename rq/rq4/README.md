# RQ4: observed failure causes

Across **117 tasks and 15 settings**, 38 tasks remain unresolved by every setting.
They contain 684 selected tests; 280 tests fail in at least one setting, yielding
**1,907 testcase–setting failure observations**. Of the 280 tests, 255 are F2P and
25 P2P, and 98 (35.0%) receive different cause categories across configurations.

| Cause | Observations |
| --- | ---: |
| Contract implementation | 1,046 |
| Representation | 392 |
| Computational logic | 371 |
| State propagation | 98 |

## Inputs and reproduction

The main evidence is under [rq4_dominant_testcases/](results/rq4_dominant_testcases/):
`manual.jsonl` records per-test and per-setting diagnoses; `testcase_inventory.jsonl`
lists all selected tests; `failure_observations.csv` contains observed failures;
`constraint_root_cause_observations.csv` gives the paper cross-tabulation; and
`observation_summary.json` records counts and units. Preparation writes the cohort,
inventory, and audit queue without changing the manual labels.

```bash
python3 rq/rq4/scripts/prepare_rq4_dominant_testcases.py
python3 rq/rq4/scripts/summarize_rq4_dominant_testcases.py
```

Run from the repository root. These commands use saved evidence without calling
models or rerunning experiments. `validated_resolutions.json`, ID54/ID96 logs,
`id64_corrected_replays/`, and [ID25 diagnostics](results/id25_loss_diagnosis/)
preserve resource/test corrections reflected in the shared outcomes.
[ID61 diagnostics](results/id61_shape_control/) and the saved case-study evidence
remain available for inspection.

## Review protocol

Select tasks unresolved in all settings after recorded evaluation corrections.
Inspect every test with at least one actual `failed` outcome, retaining F2P/P2P
split. A ledger record is `(sample_id, split, selector)` with per-setting status,
cause, and evidence. The paper counts each actual failed testcase–setting pair
once, with one confirmed primary cause. Passed, skipped, uncollected, unexecuted,
and unsubmitted cases do not become inferred failures. Repeated evaluator runs do
not increase the denominator; observations are not independent defects or tasks.

Review in stable sample/test order. Read the request, test assertions, submitted
patch, and actual failure location, using trajectories or targeted diagnostics
where needed. Scripts aggregate evidence and counts; exception names, test names,
keywords, and old task-level labels cannot assign causes automatically. Identical
exceptions or wrong numbers do not alone establish identical mechanisms.
Distinguish infrastructure/test problems from defects in agent code.

For a causal chain, count the confirmed upstream defect. Do not force a category
when independent defects cannot be ordered. Each setting contributes at most one
supporting vote per testcase. Review every observed failure before completing a
case; preserve unresolved evidence. The historical testcase-level dominant label
is the most frequent supported category, not necessarily a majority. Ties or
unknown observations capable of changing the leading category remain
`undetermined`; conflicting task/test requirements are `invalid_test`, without an
agent-cause label. A dominant-label tie does not imply missing per-setting causes.

Constraint labels identify what tests check; root causes identify actual defect
mechanisms. A quantum-semantic test can fail first at an interface check and
receive a contract-implementation cause without proving a quantum invariant was
violated. Retain the actual failure location and do not relabel RQ3. Evidence must
identify the relevant source/log/patch location; an old diagnosis is reusable only
if it explains this specific testcase failure.

## Provenance and limitations

The [extension archive](results/additions_20261002/) preserves patches, first-run
failure logs, source revisions/hashes, explicit decisions, and the original
250-test ledger. Before filtering, five added tasks with failures contributed
54 tests and 345 observations; another never-resolved task had no actual failed
tests. The active extension contributes four tasks, 30 tests, and 241 observations.
IDs 117 and 119 remain in [historical evidence](results/before119/), not active counts.

Added review was assisted by Codex and supplies no invented human votes. The
[agreement confirmation](results/annotation_agreement_confirmation.json) records
author-confirmed kappa for 1,907 failure observations; no new agreement statistic
is inferred here. No diagnostic repair was run for added cases, so those causes
are supported by source and observed failure paths. Some selected tests depend on
internal attributes or serialization formats; per-case records retain these limits.
Conclusions describe observed failures in the 38 never-resolved tasks, not all
agent failures. Historical dominant-cause summaries remain supplementary.
