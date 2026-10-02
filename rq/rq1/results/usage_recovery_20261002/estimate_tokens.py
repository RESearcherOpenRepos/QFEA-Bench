"""Explicitly labelled imputation from same-cohort Gemini/OpenHands trajectories.

No API calls. Original evaluation and trajectory files are never overwritten.
For n completed steps, use the component-wise median cumulative usage at step n
from same-cohort complete traces that reach n. The three independently recovered
calls are included exactly, with the other 25/28 of that run imputed. Comparison
min/max values describe reference variability, not a confidence interval.
"""
import csv, hashlib, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).parent
B=ROOT/'benchmark/evaluation/openhands/runs/gemini3_flash_20260606/additions_20260930'
KEYS=['input_tokens','output_tokens','cached_input_tokens','cache_creation_input_tokens']
refs=[]
for p in sorted((B/'remaining').glob('*/*.traj.json')):
 d=json.loads(p.read_text());a=d['agent']
 if a['steps'] and a.get('cumulative_token_by_step'):
  assert len(a['cumulative_token_by_step'])==a['steps']
  assert all(a['cumulative_token_by_step'][-1][k]==a[k] for k in KEYS)
  refs.append(dict(instance_id=p.parent.name,steps=a['steps'],records=a['cumulative_token_by_step'],source=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len(refs)==7
known=json.loads((OUT/'openqaoa_36_71_known_generations.json').read_text())['records']
anchor=dict(input_tokens=sum(r['native_tokens_prompt'] for r in known),output_tokens=sum(r['native_tokens_completion'] for r in known),cached_input_tokens=sum(r['native_tokens_cached'] for r in known),cache_creation_input_tokens=0)
recovery=json.loads((OUT/'openhands_gemini_recovery.json').read_text())
rows=[]
for r in recovery['records']:
 estimates={}
 for cap in [30,100]:
  n=min(cap,r['steps'])
  eligible=[ref for ref in refs if ref['steps']>=n]
  assert len(eligible)>=2
  values=[ref['records'][n-1] for ref in eligible]
  usage={k:round(statistics.median(v[k] for v in values)) for k in KEYS}
  lo={k:min(v[k] for v in values) for k in KEYS};hi={k:max(v[k] for v in values) for k in KEYS}
  if r['instance_id']=='openqaoa_36_71':
   assert n==28 and len(known)==3
   # The recovered response positions are not fully available; retain exact sums
   # and use mean per-step reference usage for the remaining completed steps.
   for target in [usage,lo,hi]:
    for k in KEYS:target[k]=round(anchor[k]+(n-len(known))/n*target[k])
  for target in [usage,lo,hi]:target['total_tokens']=target['input_tokens']+target['output_tokens']+target['cache_creation_input_tokens']
  assert 0<=usage['cached_input_tokens']<=usage['input_tokens']
  estimates[str(cap)]=dict(step=n,**usage,usage_measurement='estimated',reference_instances=[ref['instance_id'] for ref in eligible],reference_min=lo,reference_max=hi)
 assert all(estimates['100'][k]>=estimates['30'][k] for k in KEYS)
 rows.append(dict(agent=r['agent'],run_id=r['run_id'],instance_id=r['instance_id'],steps=r['steps'],usage_measurement='estimated',actual_token_totals_complete=False,estimated_usage_by_cap=estimates,known_request_count=len(known) if r['instance_id']=='openqaoa_36_71' else 0))
result=dict(method='Same-cohort complete-trajectory prefix median; known request totals retained with remaining steps imputed.',limitations=['Six original histories/metrics were not preserved on transport errors.','Seven comparison workflows, with only two reaching step 53; reference min/max are sensitivity scenarios, not confidence intervals.','Failed network requests without delivered assistant actions are outside this completed-step estimate; actual billing remains unknown.','Do not interpret imputed token totals as API-reported measurements.'],references=[{k:v for k,v in r.items() if k!='records'} for r in refs],records=rows)
(OUT/'openhands_gemini_token_estimates.json').write_text(json.dumps(result,indent=2)+'\n')
flat=[]
for r in rows:
 e=r['estimated_usage_by_cap']['100'];flat.append(dict(instance_id=r['instance_id'],completed_steps=r['steps'],input_tokens_estimate=e['input_tokens'],output_tokens_estimate=e['output_tokens'],total_tokens_estimate=e['total_tokens'],tokens_at_30_steps_estimate=r['estimated_usage_by_cap']['30']['total_tokens'],usage_measurement='estimated'))
with (OUT/'token_estimates.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
for r in flat:print(r)
