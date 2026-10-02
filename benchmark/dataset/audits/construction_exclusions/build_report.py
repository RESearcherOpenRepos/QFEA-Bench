"""Summarize recorded construction decisions; never infer missing historical reasons."""
from pathlib import Path
import collections
import csv
import io
import json

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REV = 'b144452455dfc3bcfe288f6b3e714890b3b7b31d'

snapshots = OUT / 'source_snapshots'
snapshots.mkdir(exist_ok=True)
# The review release has one commit; use preserved sources, not unreachable history.
paths = ['preprocessing/result/' + p.name for p in sorted(snapshots.glob('*_review_candidates.csv'))]
if len(paths) != 7:
    raise RuntimeError('Expected seven archived candidate CSVs in source_snapshots/')
index = json.loads((ROOT / 'benchmark/dataset/samples/index.json').read_text())
ids = {r['sample_id']: r['id'] for r in index['samples'] if r['id'] <= 106}
late_reasons = {
    'pennylane_936_1070': ('runtime_incompatibility', 'The historical TensorFlow/Keras runtime raises Illegal instruction during import on the recorded linux/amd64 Docker host, preventing runtime validation.'),
    'pennylane_2037_2069': ('feature_patch_not_isolatable', 'The reproducible merge-base-to-head diff lacks the target Keras implementation; tracing earlier feature commits introduces substantial upstream synchronization, so a reliable single-feature patch cannot be isolated.'),
    'qiskit_machine_learning_342_373': ('no_valid_f2p', 'The change mainly adds tutorials and removes old callback tests; no target test establishes base failure followed by patched success.'),
    'qiskit_nature_1010_1023': ('no_valid_f2p', 'The target tests pass on both base and patched revisions, and unittest subTest cases cannot be separated into independent pytest selectors.'),
    'qiskit_nature_974_1031': ('feature_patch_not_isolatable', 'The PR mixes extensive mapper/API refactoring with related changes and lacks a clear single-feature scope.'),
    'qiskit_nature_803_873': ('issue_pr_metadata_mismatch', 'The PR changes include_dipole in Gaussian/PySCF, which does not match the candidate Psi4Driver request and tests.'),
    'qiskit_nature_514_646': ('issue_pr_metadata_mismatch', 'The issue requests GroundStateSolver.is_variational(), but the PR replaces a VQE factory for other issues and its test paths do not match.'),
}
records = []
for path in paths:
    content = (snapshots / Path(path).name).read_text()
    for row in csv.DictReader(io.StringIO(content)):
        sid = row['sample_id']
        if row['keep'] == 'yes':
            stage = 'retained' if row['benchmark_status'] == 'completed' else '113_to_106'
            code, detail = ('retained', '') if stage == 'retained' else late_reasons[sid]
            reason_evidence = 'dataset_index_and_completed_status' if stage == 'retained' else 'recorded_benchmark_notes'
        else:
            stage = '503_to_113'
            if row['issue_label'] != 'feature':
                code, detail = row['issue_label'], 'Recorded issue_label classification; no finer reason was saved for other.' if row['issue_label'] == 'other' else 'Recorded issue_label classification.'
                reason_evidence = 'recorded_issue_label'
            else:
                code = 'feature_not_retained_reason_missing' if row['keep'] == 'no' else 'feature_maybe_not_retained_reason_missing'
                detail = 'The keep decision was recorded without a specific exclusion reason; missing tests, relationship ambiguity, or insufficient quantum scope must not be inferred.'
                reason_evidence = 'decision_only_reason_missing'
        records.append({
            'sample_id': sid, 'dataset_id': ids.get(sid, ''), 'repository': row['repository'],
            'issue_url': row['issue_url'], 'pr_url': row['pr_url'],
            'source_file': path, 'source_row_id': row['id'], 'source_revision': REV,
            'issue_label': row['issue_label'], 'keep': row['keep'],
            'benchmark_status': row['benchmark_status'], 'stage': stage,
            'reason_code': code, 'reason_evidence': reason_evidence,
            'reason_summary_en': detail, 'original_benchmark_notes': row['benchmark_notes'],
        })
assert len(records) == len({r['sample_id'] for r in records}) == 503
assert {r['sample_id'] for r in records if r['stage'] == 'retained'} == set(ids)
assert sum(r['keep'] == 'yes' for r in records) == 113
assert sum(r['stage'] == '113_to_106' for r in records) == 7
assert all(r['original_benchmark_notes'] for r in records if r['stage'] == '113_to_106')
with (OUT / 'candidate_decisions.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
# Preserve the original workflow snapshot byte-for-byte.
summary = {
    'source_revision': REV, 'candidate_count': 503, 'retained_after_screening': 113,
    'final_count': len(ids), 'final_ids_match_current_index': True,
    '503_to_113': dict(collections.Counter(r['reason_code'] for r in records if r['stage'] == '503_to_113')),
    '113_to_106': dict(collections.Counter(r['reason_code'] for r in records if r['stage'] == '113_to_106')),
    'limitation': '55 feature/no and 16 feature/maybe records lack specific exclusion reasons; 46 other records also lack a finer breakdown.',
}
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
report = """# Construction screening evidence

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
"""
for r in records:
    if r['stage'] == '113_to_106':
        report += f"| `{r['sample_id']}` | {r['reason_summary_en']} |\n"
report += """
## Evidence and limitations

- [candidate_decisions.csv](candidate_decisions.csv) contains all 503 decisions, source locations, original notes, and explicit missing-reason markers. English summaries are derived descriptions; original source notes are preserved.
- [summary.json](summary.json) records machine-readable stage counts.
- [source_snapshots/](source_snapshots/) preserves the original CSVs and workflow text; their old paths identify historical sources.
- [Dataset guide](../../README.md) describes the released construction workflow.

The 55 feature/no, 16 feature/maybe, and 46 other records do not support an invented breakdown into missing tests, relationship ambiguity, or insufficient quantum scope. Any further audit must be identified as subsequent review rather than pre-existing evidence.
"""
(OUT / 'README.md').write_text(report)
print(json.dumps(summary, indent=2))
