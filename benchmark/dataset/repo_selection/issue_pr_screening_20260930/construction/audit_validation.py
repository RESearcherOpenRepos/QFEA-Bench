"""Check actual per-item evidence; never equate a nonzero suite exit with all failures."""
import json,collections,datetime
from pathlib import Path
R=Path(__file__).resolve().parent

def check(out,selectors,expect_failure=False,allow_collection=False):
 out=Path(out)
 if not (out/'result.json').exists():return False,'missing result'
 d=json.loads((out/'result.json').read_text());cmd=json.loads((out/'command.json').read_text())
 if cmd['returncode']==124:return False,'timeout'
 if d['collection_errors']:
  return (expect_failure and allow_collection),'collection failure (requires feature-specific manual review)'
 if set(d['items'])!=set(selectors):return False,'selector mismatch'
 by=collections.defaultdict(list)
 for report in d['reports']:by[report['nodeid']].append(report)
 for node in selectors:
  reports=by[node]
  if not reports or any(x['outcome']=='skipped' or x.get('wasxfail') for x in reports):return False,'skipped or unexecuted item'
  failed=any(x['outcome']=='failed' for x in reports)
  passed=any(x['phase']=='call' and x['outcome']=='passed' for x in reports)
  if expect_failure and not failed:return False,'base-passing item'
  if not expect_failure and (failed or not passed):return False,'not a real pass'
 return True,'verified'

def audit(sid):
 cfg=json.loads((R/'jobs'/sid/'test_plan.json').read_text());log=R/'logs'/sid
 problems=[];stability={};formal={}
 for stage in ['stability','formal']:
  p=log/(stage+'_runs.json')
  if not p.exists():problems.append(stage+' incomplete');continue
  records=[Path(x) for x in json.loads(p.read_text())];counts=collections.Counter();individual_counts=collections.Counter();collection_seen=False
  for out in records:
   if not (out/'result.json').exists():problems.append(str(out.name)+': missing result');continue
   d=json.loads((out/'result.json').read_text());side,suite=d['side'],d['suite'];expected=side=='base' and suite=='fail_pass'
   individual='individual' in out.name
   selectors=json.loads((out/'config.json').read_text())[suite] if individual else cfg[suite]
   allow=bool(cfg.get('reviewed_base_collection_failure')) and expected
   ok,reason=check(out,selectors,expected,allow)
   if not ok:problems.append(out.name+': '+reason)
   if individual:
    for selector in selectors:individual_counts[selector]+=1
    continue
   if expected and d['collection_errors']:collection_seen=True
   counts[side+'_'+suite]+=1
   cmd=json.loads((out/'command.json').read_text())
   if stage=='formal':
    formal[side+'_'+suite]=dict(verified=ok,seconds=cmd['duration_seconds'],path=str(out),items=len(selectors))
    if cmd['duration_seconds']>=120:problems.append('formal exceeds 120 seconds: '+side+' '+suite)
  required=3 if stage=='stability' else 1
  for key in ['patched_fail_pass','patched_pass_pass','base_fail_pass','base_pass_pass']:
   if counts[key]!=required:problems.append(stage+' '+key+' trial count '+str(counts[key]))
  if stage=='stability':
   stability=dict(counts)
   if collection_seen:
    for selector in cfg['fail_pass']:
     if individual_counts[selector]!=3:problems.append('individual base trial count '+str(individual_counts[selector])+': '+selector)
 return dict(sample_id=sid,runtime_verified=not problems,problems=problems,stability=stability,formal=formal)

if __name__=='__main__':
 rows=[audit(p.name) for p in (R/'jobs').iterdir() if p.is_dir()]
 (R/'validation_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
 for d in rows:print(d['sample_id'],d['runtime_verified'],'; '.join(d['problems'][:3]))
 p=R/'status.json';d=json.loads(p.read_text());d.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='validating',runtime_verified_new_instances=sum(x['runtime_verified'] for x in rows),validation_commands_executed=len(list((R/'logs').glob('*/**/command.json'))),docker_builds_completed=sum(1 for p in (R/'logs').glob('*/build_status.json') if len(json.loads(p.read_text()))==2 and all(x['returncode']==0 for x in json.loads(p.read_text()))));p.write_text(json.dumps(d,indent=2)+'\n')
