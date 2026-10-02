"""Read-only, cached reproduction of historical Issue/PR mining; no semantic auto-labels."""
import concurrent.futures,csv,json,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPOS=['tequilahub/tequila','sQUlearn/squlearn','entropicalabs/openqaoa','Qiskit/qiskit-addon-sqd']
TEST_HINTS=('test/','tests/','/test_','_test.py')
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def api(args):
 for attempt in range(4):
  p=subprocess.run(['gh','api',*args],capture_output=True,text=True,timeout=120)
  if p.returncode==0:
   d=json.loads(p.stdout)
   if not isinstance(d,dict) or not d.get('errors'):return d
  if attempt==3:raise RuntimeError(p.stderr[:600] or p.stdout[:600])
  time.sleep(2*(attempt+1))
def cached_rest(repo,key,endpoint,pages=False):
 p=ROOT/'evidence'/repo.replace('/','__')/(key+'.json')
 if p.exists():return json.loads(p.read_text())
 d=api([endpoint]+(['--paginate','--slurp'] if pages else []))
 if pages:d=[x for page in d for x in page]
 write(p,d);return d
def metadata(repo):
 p=ROOT/'evidence'/repo.replace('/','__')/'metadata.json'
 if p.exists():return json.loads(p.read_text())
 owner,name=repo.split('/');all_data={}
 for typ in ['issues','pullRequests']:
  nodes=[];cursor=None
  while True:
   after=',after:'+json.dumps(cursor) if cursor else ''
   extra=',states:MERGED' if typ=='pullRequests' else ''
   fields='number title body url state createdAt updatedAt closedAt'
   if typ=='issues':fields+=' closedByPullRequestsReferences(first:100) { totalCount pageInfo { hasNextPage } nodes { number url mergedAt repository { nameWithOwner } } }'
   else:fields+=' mergedAt baseRefOid headRefOid changedFiles'
   q='query { repository(owner:'+json.dumps(owner)+',name:'+json.dumps(name)+') { '+typ+'(first:100'+extra+after+') { totalCount pageInfo { hasNextPage endCursor } nodes { '+fields+' } } } }'
   connection=api(['graphql','-f','query='+q])['data']['repository'][typ]
   nodes.extend(connection['nodes'])
   if not connection['pageInfo']['hasNextPage']:break
   cursor=connection['pageInfo']['endCursor']
  assert len(nodes)==connection['totalCount'] and len({x['number'] for x in nodes})==len(nodes)
  all_data[typ]=nodes
 all_data['repository']=repo;all_data['retrieved_utc']=datetime.now(timezone.utc).isoformat()
 write(p,all_data);return all_data

def timeline(job):
 repo,issue=job
 return repo,issue['number'],cached_rest(repo,f'issue_{issue["number"]}_timeline',f'repos/{repo}/issues/{issue["number"]}/timeline?per_page=100',True)

def files(job):
 repo,n=job
 return repo,n,cached_rest(repo,f'pr_{n}_files',f'repos/{repo}/pulls/{n}/files?per_page=100',True)

def evidence(job):
 repo,n,kind=job
 if kind=='issue':
  cached_rest(repo,f'issue_{n}_comments',f'repos/{repo}/issues/{n}/comments?per_page=100',True)
 else:
  cached_rest(repo,f'pr_{n}',f'repos/{repo}/pulls/{n}')
  for suffix,endpoint in [('comments',f'issues/{n}/comments'),('reviews',f'pulls/{n}/reviews'),('review_comments',f'pulls/{n}/comments')]:
   cached_rest(repo,f'pr_{n}_{suffix}',f'repos/{repo}/{endpoint}?per_page=100',True)
 return repo,n,kind

def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  met={d['repository']:d for d in ex.map(metadata,REPOS)}
 print('Metadata:',{r:(len(met[r]['issues']),len(met[r]['pullRequests'])) for r in REPOS},flush=True)
 links={};stats={}
 def add(repo,issue,pr,kind):
  key=(repo,issue,pr);links.setdefault(key,set()).add(kind)
 jobs=[(r,i) for r in REPOS for i in met[r]['issues'] if i['state']=='CLOSED']
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  for k,(repo,inum,events) in enumerate(ex.map(timeline,jobs),1):
   for ev in events:
    if ev.get('event') not in ['cross-referenced','connected','referenced','closed']:continue
    src=(ev.get('source') or {}).get('issue') or {}
    if not src.get('pull_request'):continue
    if src.get('repository_url','').endswith('/repos/'+repo):add(repo,inum,src['number'],'timeline:'+ev['event'])
   if k%40==0:print('Timelines:',k,'/',len(jobs),flush=True)
 for repo in REPOS:
  d=met[repo];issues={i['number']:i for i in d['issues']};prs={p['number']:p for p in d['pullRequests']}
  for i in issues.values():
   if i['state']!='CLOSED':continue
   con=i['closedByPullRequestsReferences'];assert not con['pageInfo']['hasNextPage']
   for p in con['nodes']:
    if p['repository']['nameWithOwner'].lower()==repo.lower():add(repo,i['number'],p['number'],'linked:graphql')
  for p in prs.values():
   for m in re.finditer(r'#(\d+)|\bgh-(\d+)\b',(p['title'] or '')+'\n'+(p['body'] or ''),re.I):
    n=int(m.group(1) or m.group(2))
    if n in issues:add(repo,n,p['number'],'linked:pr_text')
  stats[repo]={'all_issues':len(issues),'closed_issues':sum(i['state']=='CLOSED' for i in issues.values()),'merged_prs':len(prs)}
 links={k:v for k,v in links.items() if k[2] in {p['number'] for p in met[k[0]]['pullRequests']}}
 jobs=sorted({(r,p) for r,i,p in links})
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  filemap={(r,n):f for r,n,f in ex.map(files,jobs)}
 records=[]
 for repo,i,p in sorted(links):
  issue=next(x for x in met[repo]['issues'] if x['number']==i);pr=next(x for x in met[repo]['pullRequests'] if x['number']==p);fs=filemap[repo,p]
  assert len(fs)==pr['changedFiles'],(repo,p,len(fs),pr['changedFiles'])
  tests=[f['filename'] for f in fs if f['status'] in ['added','modified'] and any(h in f['filename'].lower() for h in TEST_HINTS)]
  records.append({'sample_id':repo.split('/')[1].lower().replace('-','_')+f'_{i}_{p}','repository':repo,'issue_number':i,'pr_number':p,'issue_url':issue['url'],'pr_url':pr['url'],'issue_state':issue['state'],'issue_title':issue['title'],'pr_title':pr['title'],'link_types':sorted(links[repo,i,p]),'changed_files':len(fs),'test_files':tests,'legacy_test_file_gate':bool(tests)})
 write(ROOT/'all_pairs.json',records)
 for repo in REPOS:
  rs=[r for r in records if r['repository']==repo]
  stats[repo].update(raw_pairs=len(rs),pairs_with_added_or_modified_test_files=sum(r['legacy_test_file_gate'] for r in rs),pr_first_open_issue_pairs=sum(r['issue_state']=='OPEN' for r in rs))
 write(ROOT/'mining_summary.json',{'retrieval_completed_utc':datetime.now(timezone.utc).isoformat(),'repositories':stats,'semantic_review_complete_at_collection':False,'current_review_status_file':'summary.json','legacy_source_commit':'b144452455dfc3bcfe288f6b3e714890b3b7b31d','test_gate':'Historical TEST_PATH_HINTS with added/modified status; not proof of actual feature coverage.','pr_first_policy':'Like historical code, title/body references may recover open issues; their states are retained explicitly.'})
 print(json.dumps(stats,indent=2),flush=True)
 candidates=[r for r in records if r['legacy_test_file_gate']]
 p=ROOT/'review_candidates.csv'
 if not p.exists():
  with p.open('w',encoding='utf-8-sig',newline='') as out:
   keys=['id','sample_id','repository','issue_url','pr_url','issue_label','keep','benchmark_status','benchmark_notes']
   w=csv.DictWriter(out,fieldnames=keys);w.writeheader()
   for num,r in enumerate(candidates,1):w.writerow({**{k:r[k] for k in ['sample_id','repository','issue_url','pr_url']},'id':num})
 jobs=sorted({(r['repository'],r['issue_number'],'issue') for r in candidates}|{(r['repository'],r['pr_number'],'pr') for r in candidates})
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  for k,_ in enumerate(ex.map(evidence,jobs),1):
   if k%30==0:print('Review evidence:',k,'/',len(jobs),flush=True)
 print('Ready for independent, one-pair-at-a-time semantic review:',len(candidates),flush=True)
if __name__=='__main__':main()
