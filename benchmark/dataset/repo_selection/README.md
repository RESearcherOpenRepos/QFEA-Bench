# Repository selection evidence

The released benchmark contains **117 tasks from 11 repositories**. This directory
preserves a retrospective repository-screening audit. The original selection did
not retain a complete search log; this later audit must not be presented as a
contemporaneous reconstruction of every original decision.

The recorded search reduces 473 initial repositories to 211 with more than 20
closed issues, then 121 with more than 200 merged PRs, and finally 69 matching the
keyword groups. Scope review proposes 58 exclusions and retains the original
seven repositories plus Tequila, sQUlearn, OpenQAOA, and qiskit-addon-sqd. The
original seven were not re-audited against all subsequently adopted conditions.
Independent human-confirmation fields remain incomplete; unknown or deferred
checks do not establish that a condition passed or failed.

## Criteria and evidence

The automatic gate combines a non-fork GitHub search for `quantum` in repository
names/descriptions and more than 100 stars with the issue/PR thresholds above.
At least one phrase must match GitHub's name/description/README search:
`quantum computing`, `quantum chemistry`, `quantum machine learning`,
`quantum optimization`, or `quantum finance`. Stable repository IDs determine
intersection and deduplication. The automatic gate does not filter language or
archive status; primary language alone does not prove a Python-native application
implementation. Applicable scope conditions are conjunctive and must use the same
unit of assessment. The proposed single-algorithm-family exclusion was withdrawn
for OpenQAOA and SQD.

| File | Purpose |
| --- | --- |
| [criteria.json](criteria.json) | Adopted gates, scope conditions, and reason codes |
| [snapshots/](snapshots/) | Recorded search metadata and complete query ID sets |
| [candidates.csv](candidates.csv) | The 69 automatic candidates |
| [screening_summary.json](screening_summary.json) | Automatic stage counts |
| [manual_audit.csv](manual_audit.csv) | Scope assessments, evidence, and unfilled human-confirmation fields |
| [selected_repositories.csv](selected_repositories.csv) | The 11 repositories and active sample counts |
| [audit_summary.json](audit_summary.json) | Historical audit state; its 119-task construction count predates cohort filtering |
| [audit_closure.json](audit_closure.json) | Evidence limits, including lack of a uniquely derived seven-repository selection |
| [deep_review.csv](deep_review.csv) | Detailed boundary-project assessments |
| [necessary_condition_check.json](necessary_condition_check.json) | Failed, unknown, and deferred conditions distinguished |
| [confirmed_scope_review.json](confirmed_scope_review.json) | Decisions after additional scope conditions |
| [primary_product_review.json](primary_product_review.json) | Primary-product scope decisions and counterevidence |
| [evidence/](evidence/) | Source revisions, file excerpts, permanent links, and review evidence |
| [Issue–PR screening](issue_pr_screening_20260930/README.md) | Four-repository candidate selection |
| [Construction](issue_pr_screening_20260930/construction/README.md) | Runtime validation evidence |

Run `python3 benchmark/dataset/repo_selection/screen_repositories.py validate`
from the repository root to validate the recorded manifest. Use `screen` with an
explicit `--output` directory to replay the stored search snapshot; `fetch` requires
GitHub access. Store new searches separately to avoid mixing evidence snapshots.
The [sample index](../samples/index.json) defines the active cohort; historical
search counts and construction totals are not release denominators.
