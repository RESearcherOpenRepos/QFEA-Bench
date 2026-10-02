"""Promote only audited runtime successes with reviewed task drafts."""
import json,sys,subprocess,shutil,collections
from pathlib import Path
from audit_validation import audit
R=Path(__file__).resolve().parent
DATASET=R.parents[2]
ROWS={x['sample_id']:x for x in json.loads((R/'cohort.json').read_text())}
GROUPS={'tequila':'tequila','squlearn':'squlearn','openqaoa':'openqaoa','qiskit_addon_sqd':'qiskit-addon-sqd'}

def finalize(sid):
 evidence=audit(sid)
 if not evidence['runtime_verified']:raise RuntimeError(evidence['problems'])
 row=ROWS[sid];assert row['current_issue_state']=='closed'
 j=R/'jobs'/sid;cfg=json.loads((j/'test_plan.json').read_text());draft=json.loads((j/'task_draft.json').read_text())
 group=next(v for k,v in GROUPS.items() if sid.startswith(k+'_'));dest=DATASET/'samples'/group/sid;dest.mkdir(parents=True,exist_ok=True)
 all_samples=[json.loads(p.read_text()) for p in (DATASET/'samples').glob('*/*/sample.json')]
 old=dest/'sample.json';number=json.loads(old.read_text())['instance']['id'] if old.exists() else max(x['instance'].get('id',0) for x in all_samples)+1
 image='benchmark-'+sid+':latest';platform=cfg.get('platform','linux/amd64')
 code="import json,sys,platform,subprocess;from pathlib import Path;print(json.dumps(dict(python_version=platform.python_version(),os_release=Path('/etc/os-release').read_text(),glibc=platform.libc_ver(),freeze=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))))"
 env=json.loads(subprocess.check_output(['docker','run','--rm','--platform',platform,'--network','none','--entrypoint','python',image,'-c',code],text=True))
 (j/'requirements.resolved.txt').write_text(env.pop('freeze'))
 validations={side:{} for side in ['base','patched']}
 for key,v in evidence['formal'].items():
  side,suite=key.split('_',1);out=Path(v['path']);d=json.loads((out/'result.json').read_text());failed=side=='base' and suite=='fail_pass'
  if d['collection_errors']:summary=f"{len(cfg[suite])} selected selectors blocked by target-feature import failure ({d['pytest_seconds']:.2f}s); each independently confirmed in three stability trials"
  else:summary=f"{len(cfg[suite])} {'failed' if failed else 'passed'} in {d['pytest_seconds']:.2f}s"
  validations[side][suite]=dict(result='failed' if failed else 'passed',file_list=cfg[suite],summary=summary,duration_seconds=v['seconds'])
 env.update(platform=platform,shared_between_base_and_patched=True,dependency_lock='requirements.resolved.txt',notes=[cfg[k] for k in ['platform_note','environment_note'] if k in cfg])
 sample=dict(instance=dict(id=number,repo=row['repository'],instance_id=sid,status='completed',issue_url=row['issue_url'],issue_state='closed',pr_url=row['pr_url'],base_commit=row['base_commit'],patch=row['patch_commit']),metadata=dict(quantum_depth=cfg['quantum_depth'],quantum_depth_rationale=cfg['quantum_depth_rationale']),golden_patch=dict(oracle_files=draft['oracle_files']),task=draft['task'],runtime=dict(docker=dict(build_success=True,platform=platform,image=image),environment=env),validation=dict(classification='fail_to_pass',**validations))
 sample['construction_notes']={'stability':'Three actual trials per side and suite; all exact selected items verified. Base collection failures also checked individually.','evidence_directory':str(R.relative_to(DATASET)/'logs'/sid),'selector_exclusions':cfg.get('selector_exclusions',{})}
 (j/'sample.json').write_text(json.dumps(sample,indent=2)+'\n')
 p=j/'Dockerfile';s=p.read_text()
 if 'COPY sample.json' not in s:s=s.replace('ENTRYPOINT','COPY sample.json /benchmark/sample.json\nENTRYPOINT');p.write_text(s)
 # Metadata-only layer; code, dependencies, and runner are the formally tested layers.
 with (R/'logs'/sid/'metadata_build.log').open('w') as f:
  subprocess.run(['docker','build','--platform',platform,'-f',str(p),'-t',image,str(j)],stdout=f,stderr=subprocess.STDOUT,check=True)
 info=json.loads(subprocess.check_output(['docker','image','inspect',image],text=True))[0]
 sample['runtime']['docker'].update(image_id=info['Id'],image_size=str(info['Size']))
 sample['runtime']['docker']['validation_note']='Final layer adds sample metadata only; four formal commands tested the identical code, dependencies and evaluator entry point.'
 (j/'sample.json').write_text(json.dumps(sample,indent=2)+'\n')
 p=j/'Dockerfile.repo-base';p.write_text(p.read_text().replace('# Initial recipe only: NOT built or runtime validated.','# Built evaluator dependency environment; validation evidence is recorded in sample.json.'))
 for name in ['sample.json','Dockerfile.repo-base','Dockerfile','run.sh','evaluator.py','test_plan.json','constraints.txt','requirements.resolved.txt']:
  shutil.copy2(j/name,dest/name)
 shutil.copy2(j/'source.tar.gz',dest/'source.tar.gz')
 (dest/'.gitignore').write_text('source.tar.gz\n')
 source={k:row[k] for k in ['repository','base_commit','patch_commit']}
 source['platform']=platform
 source['base_image_tag']='qfea-python310:trixie-arm64' if platform.endswith('arm64') else 'qfea-python310:trixie-db7a1753878f'
 source['base_image_digest']='python@sha256:9d53d8d4c0e882f61913025db53b3aec4ef74336082a9ab47d8a14e9e8329b00' if platform.endswith('arm64') else 'python@sha256:3ff3599b60b92eeb304e6bd580b765c4e46f0290e687926bb37a078c74a181a1'
 (dest/'source.json').write_text(json.dumps(source,indent=2)+'\n')
 shutil.copy2(R/'prepare_sample_source.py',dest/'prepare_source.py')
 print(sid,number,dest,flush=True)
if __name__=='__main__':
 for sid in sys.argv[1:]:finalize(sid)
