"""Recover completed assistant turns from original progress logs; never impute tokens."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).parent
B=ROOT/'benchmark/evaluation/openhands/runs/gemini3_flash_20260606/additions_20260930'
source=ROOT/'benchmark/evaluation/openhands/results/results_gemini3_flash_20260606.json'
data=json.loads(source.read_text())['results']; data=list(data.values()) if isinstance(data,dict) else data
rows=[]
for r in data:
 if not r.get('telemetry_incomplete'):continue
 sid=r['instance_id'];matches=[]
 for p in [B/'first_agent.log', B/'first.log', B/'remaining_agents.log']:
  if p.exists():
   steps=[int(n) for n in re.findall(r'OPENHANDS_PROGRESS instance='+re.escape(sid)+r' step=(\d+)/100',p.read_text())]
   if steps:matches.append((p,steps))
 # Locate the first sample's launcher log by content without including duplicate instance logs.
 if not matches:
  for p in B.glob('*.log'):
   steps=[int(n) for n in re.findall(r'OPENHANDS_PROGRESS instance='+re.escape(sid)+r' step=(\d+)/100',p.read_text())]
   if steps:matches.append((p,steps))
 assert len(matches)==1,(sid,[(str(p),len(s)) for p,s in matches])
 p,steps=matches[0];assert steps==list(range(1,max(steps)+1)),(sid,steps)
 assert max(steps)==r['observed_agent_steps']
 rows.append(dict(agent='openhands',run_id='gemini3_flash_20260606',instance_id=sid,steps=max(steps),steps_complete=True,token_metrics_complete=False,input_tokens=None,output_tokens=None,cost_usd=None,source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),method='Count contiguous StepProgressTracker progress records; one unique model response with actions per completed step. Terminal failed request did not deliver another action.',limitation='Final metrics and history were not saved on exception; displayed zero-token counters are placeholders. Do not count unknown tokens or cost as zero.'))
assert len(rows)==6
result=dict(records=rows,source_result_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),recovery_scope='Steps only; token totals still unknown.',billing_access={'activity_http_status':403,'analytics_http_status':403,'reason':'Existing API key is not a management key.'})
(OUT/'openhands_gemini_recovery.json').write_text(json.dumps(result,indent=2)+'\n')
print([(r['instance_id'],r['steps']) for r in rows])
