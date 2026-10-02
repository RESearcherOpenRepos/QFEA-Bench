"""Explore built candidates without treating preliminary outcomes as admission."""
import json,time,concurrent.futures
from pathlib import Path
from probe import run
R=Path(__file__).resolve().parent

def explore(sid):
 j=R/'jobs'/sid;outcomes={}
 for suite in ['fail_pass','pass_pass']:
  out=run(sid,'patched',suite,'collect','initial')
  result=out/'result.json'
  if not result.exists():continue
  d=json.loads(result.read_text())
  if d['exit_code']==0 and d['items']:
   p=j/'test_plan.json';cfg=json.loads(p.read_text());cfg[suite]=d['items'];p.write_text(json.dumps(cfg,indent=2)+'\n')
  else:continue
  for side in ['patched','base']:
   outcomes[side+'_'+suite]=str(run(sid,side,suite,'run','initial'))
 (R/'logs'/sid/'exploration.json').write_text(json.dumps(outcomes,indent=2)+'\n')

if __name__=='__main__':
 pending={p.name for p in (R/'jobs').iterdir() if p.is_dir()};futures=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  while pending:
   for sid in list(pending):
    p=R/'logs'/sid/'build_status.json'
    if not p.exists():continue
    d=json.loads(p.read_text())
    if any(x['returncode'] for x in d):pending.remove(sid)
    elif len(d)==2:
     futures.append(pool.submit(explore,sid));pending.remove(sid)
   if pending:time.sleep(5)
  for f in futures:f.result()
