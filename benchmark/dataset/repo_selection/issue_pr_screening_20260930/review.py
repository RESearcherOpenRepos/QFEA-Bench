"""Inspect and record one candidate at a time; never auto-classify by keywords."""
import argparse,csv,json,datetime
from pathlib import Path
R=Path(__file__).resolve().parent

def rows():return list(csv.DictReader((R/'review_candidates.csv').open(encoding='utf-8-sig')))
def read(repo,name):return json.loads((R/'evidence'/repo.replace('/','__')/(name+'.json')).read_text())
def show(n,patches=False):
 rs=rows()
 if n>len(rs):print('END OF REVIEW');return
 r=rs[n-1];repo=r['repository'];i=int(r['issue_url'].split('/')[-1]);p=int(r['pr_url'].split('/')[-1]);m=read(repo,'metadata')
 issue=next(v for v in m['issues'] if v['number']==i);pr=next(v for v in m['pullRequests'] if v['number']==p)
 print('CANDIDATE',n,'/',len(rs),r['sample_id'],repo)
 for label,o,stem in [('ISSUE',issue,f'issue_{i}'),('PR',pr,f'pr_{p}')]:
  print(label,o['title'],'STATE',o['state'],'\nBODY:',o['body'])
  for c in read(repo,stem+'_comments'):
   if c.get('user',{}).get('type')=='Bot' or 'codecov' in c.get('user',{}).get('login','').lower():continue
   print(label,'COMMENT:',c['body'])
 fs=read(repo,f'pr_{p}_files');print('CHANGED FILES',len(fs))
 for f in fs:print(f['status'],f['filename'],f['additions'],f['deletions'])
 for c in read(repo,f'pr_{p}_reviews')+read(repo,f'pr_{p}_review_comments'):
  if c.get('body') and c.get('user',{}).get('type')!='Bot':print('REVIEW',c.get('path',''),c['body'])
 if patches:
  for f in fs:
   if f['filename'].endswith('.py'):print('\nPATCH',f['filename'],'\n'+f.get('patch','[NO PATCH IN REST RESPONSE]'))
def record(d):
 rs=rows();r=rs[d['ordinal']-1];assert not r['issue_label'],'Already reviewed'
 assert d['issue_label'] in ['feature','bugfix','refactor','other']
 assert d['keep'] in ['yes','no','']
 if d['issue_label']!='feature':assert d['keep']==''
 else:assert d['keep'] in ['yes','no']
 r['issue_label']=d['issue_label'];r['keep']=d['keep']
 d.update(sample_id=r['sample_id'],repository=r['repository'],issue_url=r['issue_url'],pr_url=r['pr_url'],reviewer='Codex',reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_validated=False,human_independent_annotation=False)
 with (R/'pair_decisions.jsonl').open('a') as f:f.write(json.dumps(d,ensure_ascii=False)+'\n')
 with (R/'review_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 print('RECORDED',d['ordinal'],d['issue_label'],d['keep'],d['reason'])
if __name__=='__main__':
 import sys
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['show','record']);p.add_argument('ordinal',type=int,nargs='?');p.add_argument('--patches',action='store_true');p.add_argument('--next',action='store_true');a=p.parse_args()
 if a.mode=='show':show(a.ordinal,a.patches)
 else:
  d=json.load(sys.stdin);record(d)
  if a.next:show(d['ordinal']+1,a.patches)
