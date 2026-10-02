import concurrent.futures,json,subprocess,time,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def build(sid):
 j=R/'jobs'/sid;logs=R/'logs'/sid;logs.mkdir(parents=True,exist_ok=True)
 result=[]
 platform=json.loads((j/'test_plan.json').read_text()).get('platform','linux/amd64')
 for kind,tag in [('repo-base','benchmark-base:'+sid),('sample','benchmark-'+sid+':latest')]:
  stamp=time.strftime('%Y%m%d_%H%M%S');log=logs/f'build_{kind}_{stamp}.log'
  cmd=['docker','build','--platform',platform,'--progress=plain','-f',str(j/('Dockerfile.repo-base' if kind=='repo-base' else 'Dockerfile')),'-t',tag,str(j)]
  t=time.monotonic()
  with log.open('w') as out:
   try:rc=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=1200).returncode
   except subprocess.TimeoutExpired:rc=124
  d={'kind':kind,'image':tag,'returncode':rc,'seconds':round(time.monotonic()-t,2),'log':str(log)};result.append(d)
  print(sid,kind,rc,d['seconds'],flush=True)
  (logs/'build_status.json').write_text(json.dumps(result,indent=2)+'\n')
  if rc:return result
 return result
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(build,sys.argv[1:]))
