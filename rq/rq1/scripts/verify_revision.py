"""Verify the 117-task cohort against its preserved 119-task analysis; no API calls."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'rq/rq1/results/cohort_revision_20261002'
read = lambda p: json.loads(p.read_text())
csvrows = lambda p: list(csv.DictReader(p.open()))
index = read(ROOT / 'benchmark/dataset/samples/index.json')['samples']
active = {s['sample_id'] for s in index}
excluded = {'squlearn_266_301', 'squlearn_275_339'}
assert len(active) == 117 and not active & excluded
assert {s['id'] for s in index} == set(range(1, 120)) - {117, 119}
for rel, digest in read(HERE / 'raw_result_hashes.json').items():
    assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel

settings = 0
for path in (ROOT / 'rq/rq1/results/current/evaluations').glob('*.json'):
    before = read(ROOT / 'rq/rq1/results/before119/evaluations' / path.name)
    after = read(path)
    assert after['results'] == [r for r in before['results'] if r['instance_id'] in active], path
    settings += 1
assert settings == 15
for path in (ROOT / 'rq/rq3/results/casewise_replays').glob('*.json'):
    before = read(ROOT / 'rq/rq3/results/before119/casewise_replays' / path.name)
    after = read(path)
    assert after['results'] == [r for r in before['results'] if r['instance_id'] in active], path
old_manual = (ROOT / 'rq/rq4/results/before119/rq4_dominant_testcases/manual.jsonl').read_text().splitlines(keepends=True)
new_manual = (ROOT / 'rq/rq4/results/rq4_dominant_testcases/manual.jsonl').read_text()
assert new_manual == ''.join(line for line in old_manual if json.loads(line)['sample_id'] in active)

table = csvrows(ROOT / 'rq/rq1/results/current/rq1_step_cap_main_table.csv')
assert len(table) == 15 and {r['total'] for r in table} == {'117'}
for r in table:
    assert int(r['100_f2p_total']) == 623 and int(r['100_p2p_total']) == 994
    assert math.isclose(float(r['100_resolved_rate']), int(r['100_resolved']) / 117)
best = max(table, key=lambda r: float(r['100_resolved_rate']))
assert (best['agent'], best['model'], best['100_resolved']) == ('mini-swe', 'gpt-5.5', '69')
for agent in ('mini-swe', 'openhands', 'autocoderover'):
    assert len([r for r in table if r['agent'] == agent]) == 5
gemini = next(r for r in table if r['agent'] == 'openhands' and 'gemini' in r['model'])
assert gemini['100_token_estimated_instances'] == gemini['30_token_estimated_instances'] == '4'

audit = read(ROOT / 'rq/rq1/results/current/audit.json')
assert audit['total'] == 117 and len(audit['never_resolved']) == 38
assert audit['regression']['diagnostics']['observations'] == 1755
assert audit['regression']['status'] == 'estimable'
assert not audit['regression']['diagnostics']['separation_detected']
assert audit['quantum_specificity'] == {'medium': 68, 'strong': 49}
assert all(sum(n for key, n in audit['group_sizes'].items() if key.endswith('_' + size)) == 39
           for size in ('small', 'medium', 'large'))
strata = csvrows(ROOT / 'rq/rq2/results/current/difficulty_by_specificity_complexity.csv')
ratio = lambda value: int(value.split('/')[0]) / int(value.split('/')[1].split(' ')[0])
assert all(ratio(r['Strong Total']) < ratio(r['Medium Total']) for r in strata)
assert all(ratio(r['Overall Large']) < ratio(r['Overall Small']) for r in strata)

constraint = csvrows(ROOT / 'rq/rq3/results/summary/constraint_passes_casewise_by_agent.csv')
pooled = defaultdict(Counter)
for r in constraint:
    pooled[r['agent'], r['category']].update(passed=int(r['passed']), total=int(r['total']))
rates = {agent: {category: pooled[agent, category]['passed'] / pooled[agent, category]['total']
                for category in ('general_semantics', 'quantum_semantics', 'interface')}
         for agent in ('minisweagent', 'openhands', 'autocoderover')}
assert all(v['quantum_semantics'] < min(v['general_semantics'], v['interface']) for v in rates.values())
robust = csvrows(ROOT / 'rq/rq3/results/summary/sample_resolution_robustness.csv')
for agent in ('mini-swe', 'openhands', 'autocoderover'):
    for kind in ('f2p_test_count', 'engineering_complexity'):
        grouped = defaultdict(dict)
        for r in robust:
            if r['agent'] == agent and r['stratum_type'] == kind:
                grouped[r['stratum']][r['has_quantum_semantic_f2p']] = float(r['resolved_rate'])
        assert len(grouped) == 3
        assert all(v['true'] < v['false'] for v in grouped.values()), (agent, kind)
obs = read(ROOT / 'rq/rq4/results/rq4_dominant_testcases/observation_summary.json')
assert (obs['tasks'], obs['testcases'], obs['failure_observations']) == (38, 280, 1907)

report = dict(status='passed', active_tasks=117, settings=15, outcomes=1755,
              f2p=623, p2p=994, original_raw_results_unchanged=True,
              retained_evaluation_and_casewise_records_unchanged=True,
              retained_root_cause_annotations_unchanged=True,
              strongest_resolved=69, pooled_constraint_pass_rates=rates,
              regression=audit['regression']['strong'], rq4=obs,
              scope='Checks preservation, arithmetic and qualitative claims; no new human votes or agent runs.')
(HERE / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
