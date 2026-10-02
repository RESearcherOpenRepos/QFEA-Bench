"""Three fresh independent trials on each side, preserving all selector reports."""
import json,sys,concurrent.futures
from pathlib import Path
from probe import run
R=Path(__file__).resolve().parent
for sid in sys.argv[1:]:
 records=[]
 for trial in range(1,4):
  for side,suite in [('patched','fail_pass'),('base','fail_pass'),('patched','pass_pass'),('base','pass_pass')]:
   out=run(sid,side,suite,'run',f'stability{trial}')
   records.append(str(out))
   if side=='base' and suite=='fail_pass' and (out/'result.json').exists():
    result=json.loads((out/'result.json').read_text())
    if result['collection_errors']:
     cfg=json.loads((R/'jobs'/sid/'test_plan.json').read_text())
     with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
      items=pool.map(lambda selector:run(sid,side,suite,'run',f'stability{trial}_individual',[selector]),cfg[suite])
      records.extend(str(item) for item in items)
 (R/'logs'/sid/'stability_runs.json').write_text(json.dumps(records,indent=2)+'\n')
