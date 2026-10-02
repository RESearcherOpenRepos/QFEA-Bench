"""Build the final entry point and run four offline validation commands."""
import json,subprocess,time,sys,shutil,uuid
from pathlib import Path
R=Path(__file__).resolve().parent

def formal(sid):
 j=R/'jobs'/sid;cfg=json.loads((j/'test_plan.json').read_text());platform=cfg.get('platform','linux/amd64')
 shutil.copy2(R/'evaluator.py',j/'evaluator.py')
 (j/'run.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec python /benchmark/evaluator.py "$@"\n')
 p=j/'Dockerfile';s=p.read_text();s=s.replace('COPY run.sh /benchmark/run.sh','COPY run.sh evaluator.py test_plan.json /benchmark/');p.write_text(s)
 stamp=time.time_ns();log=R/'logs'/sid/f'formal_build_{stamp}.log'
 with log.open('w') as f:rc=subprocess.run(['docker','build','--platform',platform,'-f',str(p),'-t','benchmark-'+sid+':latest',str(j)],stdout=f,stderr=subprocess.STDOUT).returncode
 if rc:raise RuntimeError(log)
 records=[]
 for side,suite in [('patched','fail_pass'),('patched','pass_pass'),('base','fail_pass'),('base','pass_pass')]:
  out=R/'logs'/sid/f'formal_{side}_{suite}_{time.time_ns()}';out.mkdir()
  name='qfea-formal-'+uuid.uuid4().hex[:10]
  cmd=['docker','run','--rm','--name',name,'--platform',platform,'--network','none','-e','GIT_NO_LAZY_FETCH=1','-e','RESULT_PATH=/results/result.json','-v',str(out)+':/results','benchmark-'+sid+':latest',side,suite.replace('_','-')]
  start=time.monotonic()
  with (out/'output.log').open('w') as f:
   try:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
   except subprocess.TimeoutExpired:subprocess.run(['docker','kill',name],stdout=subprocess.DEVNULL);rc=124
  d=dict(side=side,suite=suite,returncode=rc,duration_seconds=round(time.monotonic()-start,3),command=cmd)
  (out/'command.json').write_text(json.dumps(d,indent=2)+'\n');records.append(str(out));print(sid,side,suite,rc,d['duration_seconds'],flush=True)
 (R/'logs'/sid/'formal_runs.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':
 for sid in sys.argv[1:]:formal(sid)
