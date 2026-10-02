"""Run one isolated offline test/collection command and preserve its outcome."""
import json,subprocess,time,sys,uuid
from pathlib import Path
R=Path(__file__).resolve().parent

def run(sid,side,suite,action='run',label='explore',selectors=None):
 job=R/'jobs'/sid;name='qfea-audit-'+uuid.uuid4().hex[:12]
 out=R/'logs'/sid/f'{label}_{side}_{suite}_{action}_{time.time_ns()}';out.mkdir(parents=True)
 cfg=json.loads((job/'test_plan.json').read_text())
 if selectors is not None:cfg[suite]=selectors
 (out/'config.json').write_text(json.dumps(cfg))
 cmd=['docker','run','--rm','--name',name,'--platform',cfg.get('platform','linux/amd64'),'--network','none','-e','GIT_NO_LAZY_FETCH=1','-e','PYTHONPATH=/workspace/repo/src:/workspace/repo','-v',str(R/'container_probe.py')+':/probe/probe.py:ro','-v',str(out/'config.json')+':/probe/config.json:ro','-v',str(out)+':/results','--entrypoint','python','benchmark-'+sid+':latest','/probe/probe.py',side,suite,action]
 t=time.monotonic()
 with (out/'output.log').open('w') as f:
  try:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
  except subprocess.TimeoutExpired:
   subprocess.run(['docker','kill',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);rc=124
 wall=round(time.monotonic()-t,3)
 d={'sample_id':sid,'returncode':rc,'duration_seconds':wall,'command':cmd}
 (out/'command.json').write_text(json.dumps(d,indent=2)+'\n')
 print(sid,side,suite,action,'rc',rc,'seconds',wall,'dir',out.name,flush=True)
 if (out/'result.json').exists():
  result=json.loads((out/'result.json').read_text());print('items',len(result['items']),'collection_errors',len(result['collection_errors']),flush=True)
 return out
if __name__=='__main__':run(*sys.argv[1:])
