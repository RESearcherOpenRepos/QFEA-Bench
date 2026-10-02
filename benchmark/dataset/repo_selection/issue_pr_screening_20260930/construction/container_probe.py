"""Offline source-switching test probe with per-item evidence; not an agent runtime."""
import json,os,subprocess,sys,time
from pathlib import Path
cfg=json.loads(Path('/probe/config.json').read_text())
side,suite,action=sys.argv[1:4]
os.chdir('/workspace/repo')
def git(*args):subprocess.run(['git',*args],check=True)
git('checkout','--force',cfg['base_commit'] if side=='base' else cfg['patch_commit'])
git('clean','-fdx')
selectors=cfg[suite]
if side=='base' and suite=='fail_pass':
 files=sorted(set(s.split('::')[0] for s in selectors));git('checkout',cfg['patch_commit'],'--',*files)
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
Path('/results/result.json').write_text(json.dumps({'side':side,'suite':suite,'action':action,'exit_code':int(rc),'pytest_seconds':time.monotonic()-t,'items':e.items,'reports':e.reports,'collection_errors':e.collection_errors},indent=2))
sys.exit(rc)
