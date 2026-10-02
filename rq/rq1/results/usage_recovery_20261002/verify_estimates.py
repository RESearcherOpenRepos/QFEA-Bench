"""Verify retained labelled estimates and their contribution after cohort filtering."""
import csv,json,hashlib,math
from pathlib import Path
R=Path(__file__).resolve().parents[4];B=Path(__file__).parent
read=lambda p:json.loads(p.read_text())
records=read(B/'openhands_gemini_token_estimates.json')['records'];assert len(records)==6
recovery=read(B/'openhands_gemini_recovery.json')
raw=R/'benchmark/evaluation/openhands/results/results_gemini3_flash_20260606.json'
assert hashlib.sha256(raw.read_bytes()).hexdigest()==recovery['source_result_sha256']
rawrows=read(raw)['results'];rawrows=list(rawrows.values()) if isinstance(rawrows,dict) else rawrows
rr={r['instance_id']:r for r in rawrows}
derived=read(R/'rq/rq1/results/current/evaluations/openhands_gemini3_flash_20260606.json')['results'];derived={r['instance_id']:r for r in derived}
retained=[r for r in records if r['instance_id'] in derived]
for r in retained:
 sid=r['instance_id'];d=derived[sid]
 assert not d['resolved'] and d['resolved']==rr[sid]['resolved']
 assert d['usage_recovery']['usage_measurement']=='estimated' and d['agent']['usage_measurement']=='estimated'
 for k in ['test_cases','fail_pass','pass_pass','agent_submitted','patch_applied']:
  assert d.get(k)==rr[sid].get(k),(sid,k)
 for k in ['30','100']:
  u=r['estimated_usage_by_cap'][k]
  assert u['total_tokens']==u['input_tokens']+u['output_tokens']+u['cache_creation_input_tokens']
  assert len(u['reference_instances'])>=2
 assert r['estimated_usage_by_cap']['100']['total_tokens']>=r['estimated_usage_by_cap']['30']['total_tokens']
current=list(csv.DictReader((R/'rq/rq1/results/current/rq1_step_cap_main_table.csv').open()))
target=next(r for r in current if r['agent']=='openhands' and 'gemini' in r['model'])
old=list(csv.DictReader((R/'rq/rq1/results/before119/rq1_step_cap_main_table.csv').open()))
old=next(r for r in old if r['agent']=='openhands' and 'gemini' in r['model'])
for cap in ['30','100']:
 removed=sum(r['estimated_usage_by_cap'][cap]['total_tokens'] for r in records if r['instance_id'] not in derived)
 expected=(float(old[cap+'_avg_tokens'])*int(old['total'])-removed)/len(derived)
 assert math.isclose(float(target[cap+'_avg_tokens']),expected,rel_tol=1e-12)
 assert int(target[cap+'_token_estimated_instances'])==len(retained)==4
result=dict(status='passed',historical_estimates=6,retained_estimates=4,active_tasks=len(derived),original_result_sha256_preserved=recovery['source_result_sha256'],retained_outcomes_unchanged=True,avg_tokens_100=float(target['100_avg_tokens']),avg_tokens_30=float(target['30_avg_tokens']),note='Original estimates remain labelled; published means exclude the two archived tasks using the same active cohort as effectiveness.')
(B/'estimate_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
