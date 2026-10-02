"""Check coverage, preserved original evidence, and Table 4/5 totals (no model calls)."""
import csv, hashlib, json
from pathlib import Path
R=Path(__file__).resolve().parents[4]
A=Path(__file__).parent
load=lambda p: json.loads(p.read_text())
active={s['id'] for s in load(R/'benchmark/dataset/samples/index.json')['samples']}
anns=[load(p) for p in (R/'rq/rq3/results/sample_constraint_annotations').glob('*.json') if load(p)['id'] in active]
assert len(anns)==117 and sum(len(d['tests']) for d in anns)==1617
new=[d for d in anns if d['id']>106]
assert len(new)==11 and sum(len(d['tests']) for d in new)==100
files=list((R/'rq/rq3/results/casewise_replays').glob('*.json'));assert len(files)==15
for p in files:
 d=load(p);b=load(A/'original_casewise'/p.name)
 assert d['results'][:106]==b['results'] and len(d['results'])==117
 assert d['summary']['total']==117
 assert d['summary']['fail_pass']['total']==623 and d['summary']['pass_pass']['total']==994
 for row in d['results'][106:]:
  for split,tests in row['test_cases'].items():
   for t in tests:
    if t['status']=='failed':
     first={c['selector']:c['status'] for c in row['eval_runs'][0]['test_cases'][split]}
     assert first[t['selector']]=='failed'
Q=R/'rq/rq4/results/rq4_dominant_testcases';O=R/'rq/rq4/results/additions_20261002/original_manual.jsonl'
assert (Q/'manual.jsonl').read_bytes().startswith(O.read_bytes())
assert len((Q/'manual.jsonl').read_text().splitlines())==280
cohort=load(Q/'cohort.json');obs=load(Q/'observation_summary.json')
assert (cohort['cohort_samples'],cohort['selected_tests'],cohort['eligible_ever_failed_tests'])==(38,684,280)
assert (obs['tasks'],obs['testcases'],obs['failure_observations'])==(38,280,1907)
assert sum(obs['causes'].values())==1907 and obs['testcases_with_multiple_causes']==98
with (R/'rq/rq3/results/summary/sample_resolution_by_f2p_quantum_constraint.csv').open() as f:
 rows=[r for r in csv.DictReader(f) if r['agent']=='all_agents' and r['quantum_specificity']=='all']
assert [(int(r['samples']),int(r['resolved']),int(r['total']),int(r['never_resolved_samples'])) for r in rows]==[(70,284,1050,29),(47,367,705,9)]
summary=dict(status='passed',annotated_tasks=117,selected_tests=1617,new_tasks=11,new_tests=100,settings=15,original_casewise_rows_preserved=1590,original_rq4_records_preserved=250,original_rq4_sha256=hashlib.sha256(O.read_bytes()).hexdigest(),rq4_cohort_tasks=38,rq4_tasks_with_observed_failures=38,rq4_testcases=280,rq4_failure_observations=1907,note='This audit checks evidence coverage and aggregation, not independent human agreement or causal proof by repair.')
(A/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
