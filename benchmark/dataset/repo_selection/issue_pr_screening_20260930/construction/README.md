# Construction and validation of closed-issue candidates

The historical extension retained 13 validated tasks from four repositories,
expanding the original 106-task cohort to 119. Subsequent specification/scope review
excluded IDs 117 and 119; the released benchmark contains **117 active tasks**.
See the [exclusion decisions](../../../../../rq/rq1/results/cohort_revision_20261002/exclusions.json).

- `cohort.json` records candidates, issue states, and base/patched revisions.
- `jobs/` stores build configurations and exact test plans.
- `logs/` preserves builds, selector checks, three stability repetitions, and four formal offline commands.
- `validation_summary.json` summarizes consistency checks against the selected tests.
- `status.json` preserves the historical construction state; use the active index for release counts.

## Validation protocol

F2P tests must pass on patched and fail for the requested behavior on base in all
three repetitions. P2P tests must actually pass on both revisions in all
repetitions; skip/xfail is not success. Each candidate additionally runs the four
formal patched/base F2P/P2P commands without networking, with each command below
120 seconds and its wall time retained.

When base cannot import the new feature, check each selector independently so a
module-level import failure does not conceal tests that already pass. Test
substitutions, removal of base-passing F2P tests, and environment adjustments are
recorded in each test plan and the CSV notes. The two SQD samples were validated on
native ARM because the recorded amd64 emulation lacks JAX-required AVX support;
this is not evidence of amd64 validation.

Task fields are checked against the selected assertions. Oracle files are limited
to the relevant implementation, and specificity labels are assigned without
inspecting agent outcomes. Samples are admitted only after runtime verification.
For sample contexts requiring `source.tar.gz`, run their `prepare_source.py` to
reconstruct pinned sources before building. See the [dataset workflow](../../../README.md).

The parent [screening guide](../README.md) documents the preceding static stage.
`audit_validation.py` checks saved execution evidence. `publish_status.py` is a
construction-maintenance command that rewrites manifests and this README; it is
not required to reproduce the paper tables and should not be used to reinterpret
historical construction totals as active-cohort results.
