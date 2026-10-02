# Cohort revision and cross-RQ verification

The active release contains **117 tasks**, with stable IDs 117
and 119 excluded after the 119-task evaluation. The exclusion decisions and original
raw-result hashes are preserved here. Shared cohort provenance is owned by RQ1
and used by all four RQs.

| Evidence | Location and purpose |
| --- | --- |
| Cohort decision | [exclusions.json](exclusions.json), [original index](index.before119.json), and [raw hashes](raw_result_hashes.json) |
| RQ1 historical outcomes | [before119](../before119/) — verifies unchanged outcomes for retained tasks |
| RQ2 historical covariates/regression | [before119](../../../rq2/results/before119/) — preserves the earlier difficulty analysis and dataset statistics |
| RQ3 historical testcase records | [before119](../../../rq3/results/before119/) — verifies retained testcase outcomes |
| RQ4 historical labels and failures | [before119](../../../rq4/results/before119/) — verifies retained root-cause annotations |
| Repository selection snapshot | [selected_repositories.csv](before119/repo_selection/selected_repositories.csv) |
| Cross-RQ paper audit | [recorded data checks](../paper_consistency_audit_20261002/data_checks.json) and [historical report](../paper_consistency_audit_20261002/report.txt) |
| Author-confirmed agreement provenance | [confirmation](../../../rq4/results/annotation_agreement_confirmation.json) — includes pair validity, specificity, and root-cause agreement; no new votes inferred |

Run `python3 rq/rq1/scripts/verify_revision.py` from the repository root. It reads the
per-RQ snapshots and writes [verification.json](verification.json). Snapshots retain
their original data bytes and historical source paths; these paths describe the old
layout and are not live execution instructions.

With the separately maintained manuscript present,
`python3 rq/rq1/scripts/check_paper_consistency.py` also compares paper Tables 2–3,
RQ3 outcomes, and RQ4 observations against current records. It requires
`paper/6_evaluation_results.tex`, which is not part of the public artifact. The
historical prose audit describes its original review date and is not a claim that
all issues it raised were subsequently resolved. Historical PDF compilation fields
in verification records are not evidence of a new compile after this relocation.
