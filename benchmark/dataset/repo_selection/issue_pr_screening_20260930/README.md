# Issue–PR screening for four added repositories

Historical static screening: **168 linked pairs -> 68 passing the test-path gate -> 24 feature pairs -> 14 construction candidates**. Closed-issue filtering retains 13 candidates. The released benchmark has 117 active tasks after construction and scope review.

The pairwise review was performed with Codex assistance. Independent human review is not recorded as complete. This static stage did not run Docker or F2P/P2P tests; runtime evidence is maintained separately in [construction/](construction/README.md).

| Repository | Closed issues | Merged PRs | Linked pairs | Test-path gate | Features | Retained |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tequilahub/tequila | 40 | 364 | 18 | 8 | 4 | 3 |
| sQUlearn/squlearn | 83 | 275 | 65 | 27 | 9 | 5 |
| entropicalabs/openqaoa | 38 | 217 | 29 | 26 | 8 | 4 |
| Qiskit/qiskit-addon-sqd | 59 | 252 | 56 | 7 | 3 | 2 |

## Method and boundaries

1. Combine and deduplicate closed-issue closing/timeline relations and references in merged PR titles/bodies; preserve the relationship source.
2. Apply the historical added/modified test-path heuristic (`test/`, `tests/`, `/test_`, `_test.py`). The 100 rejected pairs were not semantically classified. CI paths can match this gate; a match does not establish a valid feature test.
3. Read each remaining issue, PR, discussion, and changed file. Verify the relationship before assigning feature, bugfix, refactor, or other. Only feature pairs receive a keep decision.
4. For features, check alignment with the issue, core quantum-domain scope, and actual test coverage. Multiple related issues are not automatically disqualifying; retain each implementation only once.
5. Treat retained pairs as construction candidates. `target_tests` provides source locations, not runtime-validated pytest selectors.

The PR-first path permits an open issue. OpenQAOA issue 207 / PR 302 is excluded by the subsequent closed-issue gate. Among the 68 reviewed pairs, 20 are bugfix, 6 refactor, and 18 other; 10 of the 24 features were excluded. Detailed original decisions remain in the structured evidence.

OpenQAOA ZNE requires a specific caution: `test_expectation_zne` returns before its assertion and is not a valid oracle. A notebook execution test and wrapper-count assertions supported candidate retention, but did not establish a validated numerical mitigation-accuracy oracle.

## Evidence and reproduction

- [all_pairs.json](all_pairs.json): source relations, issue states, and test-path gate results.
- [review_candidates.csv](review_candidates.csv): static labels and keep decisions, with subsequent construction status recorded separately.
- [pair_decisions.jsonl](pair_decisions.jsonl): ordered original decisions, reasons, and evidence locations.
- [retained_pairs.csv](retained_pairs.csv): candidate test locations and construction risks.
- [evidence/](evidence/): cached public metadata, patches, discussions, and reviews.
- [source_snapshots/](source_snapshots/): historical workflow text and code, retained independently of Git history.
- `collect.py` reads GitHub and reuses the cache; collect a new snapshot in a separate directory.
- `review.py show N` displays a candidate; `record` stores explicit review decisions rather than inferring labels from keywords.
- `python3 benchmark/dataset/repo_selection/issue_pr_screening_20260930/summarize.py` validates saved decisions and regenerates this English README offline.
