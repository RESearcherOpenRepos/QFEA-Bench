"""Offline source-switching test probe with per-item evidence; not an agent runtime."""
import json,os,subprocess,sys,time
from pathlib import Path
cfg=json.loads(Path('/benchmark/test_plan.json').read_text())
side=sys.argv[1] if len(sys.argv)>1 else os.environ.get('TARGET','patched')
suite=(sys.argv[2] if len(sys.argv)>2 else os.environ.get('TEST_SUITE','fail-pass')).replace('-','_')
action='run'
if side not in ('base','patched') or suite not in ('fail_pass','pass_pass'):raise SystemExit('Invalid target or suite')
os.chdir('/workspace/repo')
def git(*args):subprocess.run(['git',*args],check=True)
git('checkout','--force',cfg['base_commit'] if side=='base' else cfg['patch_commit'])
git('clean','-fdx')
patch=os.environ.get('MODEL_PATCH_FILE')
if patch:
 if not Path(patch).is_file() or not Path(patch).stat().st_size:raise SystemExit(20)
 rc=subprocess.run(['git','apply','--whitespace=nowarn',patch]).returncode
 if rc and subprocess.run(['git','apply','--ignore-whitespace','--whitespace=nowarn',patch]).returncode:raise SystemExit(21)
selectors=cfg[suite]
if side=='base' and suite=='fail_pass':
 files=sorted(set(s.split('::')[0] for s in selectors));git('checkout',cfg['patch_commit'],'--',*files)
if os.environ.get('PREP_ONLY')=='1':raise SystemExit(0)
if not selectors:raise SystemExit(0 if suite=='pass_pass' else 2)
# Import the mutable tree, including historical editable layouts.
sys.path.insert(0,'/workspace/repo');sys.path.insert(0,'/workspace/repo/src')
import pytest
class Evidence:
 def __init__(self):self.items=[];self.reports=[];self.collection_errors=[]
 def pytest_collection_finish(self,session):self.items=[x.nodeid for x in session.items]
 def pytest_runtest_logreport(self,report):
  self.reports.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome,'duration':report.duration,'wasxfail':getattr(report,'wasxfail',None),'longrepr':str(report.longrepr) if report.failed or report.skipped else ''})
 def pytest_collectreport(self,report):
  if report.failed:self.collection_errors.append({'nodeid':report.nodeid,'longrepr':str(report.longrepr)})
if cfg.get('test_workdir'):os.chdir('/workspace/repo/'+cfg['test_workdir'])
e=Evidence();t=time.monotonic();args=['-q','--disable-warnings','--rootdir=/workspace/repo']+['/workspace/repo/'+x for x in selectors]
if action=='collect':args+=['--collect-only']
rc=pytest.main(args,plugins=[e])
Path(os.environ.get('RESULT_PATH','/tmp/validation-result.json')).write_text(json.dumps({'side':side,'suite':suite,'action':action,'exit_code':int(rc),'pytest_seconds':time.monotonic()-t,'items':e.items,'reports':e.reports,'collection_errors':e.collection_errors},indent=2))
sys.exit(rc)
