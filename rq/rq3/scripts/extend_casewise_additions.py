"""Merge active indexed additions from saved outcomes without running agents or evaluators.

Original casewise rows are loaded from immutable pre-extension snapshots. Missing
cases are represented as not_run only when no patch was applied. Model usage is
not combined here: currencies/providers and incomplete telemetry differ.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'rq/rq3/results/additions_20261002'
REFRESH = ROOT / 'rq/rq1/results/current'


def main():
    index = json.loads((ROOT / 'benchmark/dataset/samples/index.json').read_text())['samples']
    added = {s['sample_id'] for s in index if s['id'] > 106}
    assert len(index) == 117 and len(added) == 11
    overview = []
    # Preserve the original setting order used by RQ4's per-run evidence ledger.
    with (ROOT / 'rq/rq1/results/all_runs_overview.csv').open() as handle:
        settings = list(csv.DictReader(handle))
    for setting in settings:
        agent, run = setting['agent'], setting['run_id']
        source = REFRESH / 'evaluations' / f'{agent}_{run}.json'
        merged = json.loads(source.read_text())
        replay_agent = 'minisweagent' if agent == 'mini-swe' else agent
        target = ROOT / 'rq/rq3/results/casewise_replays' / f'{replay_agent}_{run}.json'
        backup = AUDIT / 'original_casewise' / target.name
        original = json.loads(backup.read_text())
        assert len(original['results']) == 106
        raw_source = ROOT / merged['provenance']['additions']
        raw = json.loads(raw_source.read_text())['results']
        raw = list(raw.values()) if isinstance(raw, dict) else raw
        rows = []
        for row in raw:
            if row['instance_id'] not in added:
                continue
            if not row.get('test_cases'):
                assert not row['patch_applied'] and not row['resolved']
                ann = json.loads(next((ROOT / 'rq/rq3/results/sample_constraint_annotations').glob('*_' + row['instance_id'] + '.json')).read_text())
                row['test_cases'] = {
                    key: [dict(selector=t['selector'], status='not_run', phase='no_evaluation')
                          for t in ann['tests'] if t['split'] == split]
                    for key, split in [('fail_pass', 'F2P'), ('pass_pass', 'P2P')]}
            rows.append(row)
        assert len(rows) == len(added) and {r['instance_id'] for r in rows} == added
        data = dict(original)
        data['results'] = original['results'] + rows
        data['original_106_summary'] = original['summary']
        summary = dict(total=len(index), pending=0,
                       resolved=sum(bool(r['resolved']) for r in data['results']),
                       patch_applied=sum(bool(r['patch_applied']) for r in data['results']))
        for split in ['fail_pass', 'pass_pass']:
            cases = [c for r in data['results'] for c in r['test_cases'][split]]
            counts = Counter(c['status'] for c in cases)
            summary[split] = dict(passed=counts['passed'], total=len(cases),
                                  summary=f"{counts['passed']}/{len(cases)}", counts=dict(counts))
        summary['usage_note'] = 'Casewise outcome counts only; original_106_summary preserves historical usage. Consult provider-specific addition accounting separately; missing usage is unknown.'
        data['summary'] = summary
        data['additions_provenance'] = dict(source=str(raw_source.relative_to(ROOT)), source_sha256=hashlib.sha256(raw_source.read_bytes()).hexdigest(), note='Saved repeated-test outcomes; no patch/no evaluation is not_run. Original 106 casewise rows retained.')
        target.write_text(json.dumps(data, indent=2) + '\n')
        overview.append(dict(agent=agent, run_id=run, result_path=str(source.relative_to(ROOT)),
                             resolved=sum(r['resolved'] for r in merged['results']),
                             patch_applied=sum(bool(r['patch_applied']) for r in merged['results'])))
    assert len(overview) == 15
    with (REFRESH / 'all_runs_overview.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(overview[0]))
        writer.writeheader()
        writer.writerows(overview)
    print(f'Extended 15 casewise files to {len(index)} active tasks; original 106 rows preserved.')


if __name__ == '__main__':
    main()
