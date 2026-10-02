"""Fetch pinned public sources for the closed-Issue construction cohort."""
import csv,json,subprocess,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parent
AUDIT=ROOT.parent

def cmd(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True,stderr=subprocess.STDOUT)
def prepare(row):
 sid=row['sample_id'];repo=row['repository'];n=row['pr_url'].split('/')[-1]
 pr=json.loads((AUDIT/'evidence'/repo.replace('/','__')/f'pr_{n}.json').read_text())
 issue=json.loads(cmd(['gh','api',f"repos/{repo}/issues/{row['issue_url'].split('/')[-1]}"]))
 (ROOT/'evidence').mkdir(exist_ok=True)
 (ROOT/'evidence'/f'{sid}_issue.json').write_text(json.dumps(issue,indent=2)+'\n')
 row=dict(row);row['current_issue_state']=issue['state'];row['status']='pending'
 if issue['state']!='closed':row['status']='excluded_open_issue';return row
 p=ROOT/'sources'/sid;p.mkdir(parents=True,exist_ok=True)
 if not (p/'.git').exists():
  cmd(['git','init','-q'],p);cmd(['git','remote','add','origin',f'https://github.com/{repo}.git'],p)
 merge=pr['merge_commit_sha']
 cmd(['git','fetch','--depth=2','origin',merge],p)
 parent=cmd(['git','rev-parse',merge+'^1'],p).strip()
 cmd(['git','checkout','--detach','--force',merge],p)
 row.update(base_commit=parent,patch_commit=merge,pr_head_commit=pr['head']['sha'],source_dir=str(p),merged_at=pr['merged_at'])
 (ROOT/'evidence'/f'{sid}_diff.txt').write_text(cmd(['git','diff','--stat',parent,merge],p))
 print('READY',sid,parent,merge,flush=True);return row

def main():
 rows=list(csv.DictReader((AUDIT/'retained_pairs.csv').open(encoding='utf-8-sig')))
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(prepare,rows))
 (ROOT/'cohort.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print('Closed cohort',sum(r['current_issue_state']=='closed' for r in out),'/',len(out),flush=True)
if __name__=='__main__':main()
