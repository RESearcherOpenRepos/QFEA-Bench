#!/usr/bin/env python3
"""Recompute tool-use statistics for the current paper cohort from retained trajectories."""
import csv,json,statistics
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parents[3]
out=root/'rq/rq1/results/current'
settings=list(csv.DictReader((out/'rq1_step_cap_main_table.csv').open()))
report=[]
for s in settings:
 if not ((s['agent']=='mini-swe' and s['model'] in ('gpt-5.5','glm-5.2')) or (s['agent']=='openhands' and s['model']=='deepseek-v4-pro')):continue
 data=json.loads((out/'evaluations'/f"{s['agent']}_{s['run_id']}.json").read_text())['results']
 details=[]
 for row in data:
  a=row['agent'];sid=row['instance_id'];path=root/a.get('trajectory_path',f"benchmark/evaluation/openhands/runs/{s['run_id']}/{sid}/{sid}.traj.json");t=json.loads(path.read_text());counts=Counter()
  if s['agent']=='mini-swe':
   messages=[m for m in t['messages'] if m.get('role')=='assistant']
   for m in messages:
    counts.update(c.get('function',{}).get('name','UNKNOWN') for c in m.get('tool_calls',[]) or [])
   assistant_turns=len(messages)
  else:
   history=t['raw_output']['history']
   actions=[e for e in history if e.get('kind')=='ActionEvent']
   counts.update(e['tool_name'] for e in actions)
   assistant_turns=None
  details.append({'instance_id':row['instance_id'],'trajectory_path':str(path.relative_to(root)),'recorded_steps':a['steps'],'assistant_messages':assistant_turns,'tools':dict(counts)})
 total=Counter()
 for d in details:total.update(d['tools'])
 rec={'agent':s['agent'],'model':s['model'],'instances':len(details),'recorded_steps':sum(d['recorded_steps'] for d in details),'tool_counts':dict(total),'details':details}
 if s['agent']=='mini-swe':
  rec['assistant_messages']=sum(d['assistant_messages'] for d in details)
  rec['bash_calls_per_assistant_step']=total['bash']/rec['assistant_messages']
  rec['mean_instance_bash_calls_per_step']=statistics.fmean(d['tools'].get('bash',0)/d['assistant_messages'] for d in details if d['assistant_messages'])
  rec['step_mismatches']=[{k:v for k,v in d.items() if k not in ['tools','trajectory_path']} for d in details if d['assistant_messages']!=d['recorded_steps']]
 else:rec['mean_tools_per_instance']={k:v/len(details) for k,v in total.items()}
 report.append(rec)
 print(json.dumps({k:v for k,v in rec.items() if k!='details'},indent=2))
assert all(r['instances']==117 for r in report)
(out/'rq1_tool_usage_117.json').write_text(json.dumps({'method':'Count tool calls in retained per-instance trajectories; Mini density is total bash calls divided by total assistant messages. OpenHands means are action counts divided by 117 instances.','settings':report},indent=2)+'\n')
