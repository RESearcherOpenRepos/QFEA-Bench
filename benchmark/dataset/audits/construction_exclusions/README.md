# Construction screening evidence

This historical audit covers the original seven repositories: **503 candidate pairs -> 184 feature candidates -> 113 retained candidates -> 106 validated tasks**. The released benchmark contains 117 active tasks. Run `python3 benchmark/dataset/audits/construction_exclusions/build_report.py` from the repository root to regenerate this report from the preserved CSV snapshots; the original Git history is unnecessary.

Candidate pairs, rather than unique issues or PRs, are counted. `source_row_id` identifies a row within its source CSV; `dataset_id` identifies an original benchmark task. Each construction-stage exclusion has one primary reason.

| Screening decision | Count | Evidence limit |
| --- | ---: | --- |
| bugfix | 166 | Existing-behavior repair |
| refactor | 107 | Restructuring |
| other | 46 | No finer per-candidate reason recorded |
| feature, keep=no | 55 | Exclusion decision without a specific reason |
| feature, keep=maybe | 16 | Unconfirmed retention; not proof of a specific defect |
| Retained feature, keep=yes | 113 | Proceeded to construction |

The seven construction exclusions comprise one runtime incompatibility, two patch-isolation failures, two invalid F2P cases, and two issue/PR metadata mismatches. In the paper these form three execution/test-validation problems and four task/patch-alignment problems.

| Candidate | Recorded construction reason |
| --- | --- |
| `pennylane_936_1070` | The historical TensorFlow/Keras runtime raises Illegal instruction during import on the recorded linux/amd64 Docker host, preventing runtime validation. |
| `pennylane_2037_2069` | The reproducible merge-base-to-head diff lacks the target Keras implementation; tracing earlier feature commits introduces substantial upstream synchronization, so a reliable single-feature patch cannot be isolated. |
| `qiskit_machine_learning_342_373` | The change mainly adds tutorials and removes old callback tests; no target test establishes base failure followed by patched success. |
| `qiskit_nature_1010_1023` | The target tests pass on both base and patched revisions, and unittest subTest cases cannot be separated into independent pytest selectors. |
| `qiskit_nature_974_1031` | The PR mixes extensive mapper/API refactoring with related changes and lacks a clear single-feature scope. |
| `qiskit_nature_803_873` | The PR changes include_dipole in Gaussian/PySCF, which does not match the candidate Psi4Driver request and tests. |
| `qiskit_nature_514_646` | The issue requests GroundStateSolver.is_variational(), but the PR replaces a VQE factory for other issues and its test paths do not match. |

## Evidence and limitations

- [candidate_decisions.csv](candidate_decisions.csv) contains all 503 decisions, source locations, original notes, and explicit missing-reason markers. English summaries are derived descriptions; original source notes are preserved.
- [summary.json](summary.json) records machine-readable stage counts.
- [source_snapshots/](source_snapshots/) preserves the original CSVs and workflow text; their old paths identify historical sources.
- [Dataset guide](../../README.md) describes the released construction workflow.

The 55 feature/no, 16 feature/maybe, and 46 other records do not support an invented breakdown into missing tests, relationship ambiguity, or insufficient quantum scope. Any further audit must be identified as subsequent review rather than pre-existing evidence.
