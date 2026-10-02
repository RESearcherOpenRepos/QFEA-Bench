"""Repeat grouped trials after selector pruning; preserve valid independent item trials."""
import json,sys
from pathlib import Path
from probe import run
R=Path(__file__).resolve().parent
sid=sys.argv[1];cfg=json.loads((R/'jobs'/sid/'test_plan.json').read_text());p=R/'logs'/sid/'stability_runs.json'
old=json.loads(p.read_text());(p.parent/'stability_before_pruning.json').write_text(json.dumps(old,indent=2)+'\n')
records=[]
for value in old:
 out=Path(value)
 if 'individual' in out.name:
  selected=json.loads((out/'config.json').read_text())['fail_pass']
  if all(x in cfg['fail_pass'] for x in selected):records.append(value)
for trial in range(1,4):
 for side,suite in [('patched','fail_pass'),('base','fail_pass'),('patched','pass_pass'),('base','pass_pass')]:records.append(str(run(sid,side,suite,'run',f'pruned_stability{trial}')))
p.write_text(json.dumps(records,indent=2)+'\n')
