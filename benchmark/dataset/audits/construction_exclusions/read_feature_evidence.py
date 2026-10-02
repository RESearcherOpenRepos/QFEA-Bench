"""Print evidence for one explicitly selected candidate; does not classify it."""
import csv,json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
rows=[r for r in csv.DictReader((OUT/'candidate_decisions.csv').open()) if r['issue_label']=='feature' and r['keep'] in ('no','maybe')]
n=int(sys.argv[1]); r=rows[n-1]
folder=OUT/'github_evidence'/r['repository'].replace('/','__')
issue=r['issue_url'].split('/')[-1];pr=r['pr_url'].split('/')[-1]
print('CANDIDATE',n,r['sample_id'],'HISTORICAL',r['keep'])
for label,stem in [('ISSUE',f'issue_{issue}'),('PR',f'pr_{pr}')]:
    if '--pr-only' in sys.argv and label=='ISSUE': continue
    o=json.loads((folder/f'{stem}.json').read_text())
    print(label,o.get('title'),'\nBODY:',o.get('body'),'\nSTATE:',o.get('state'),'merged:',o.get('merged'),'changed_files:',o.get('changed_files'))
    for c in json.loads((folder/f'{stem}_comments.json').read_text()):
        
        if '--brief' in sys.argv and (c.get('user',{}).get('type')=='Bot' or 'codecov' in c.get('user',{}).get('login','').lower()): continue
        print(label,'COMMENT:',c['body'])
files=json.loads((folder/f'pr_{pr}_files.json').read_text())
print('FILES',len(files))
for f in files:print(f['filename'],f['status'],f['additions'],f['deletions'])
if '--patches' in sys.argv:
    for f in files:
        if '--tests-only' in sys.argv and 'test' not in f['filename']: continue
        print('\nPATCH',f['filename'],'\n',f.get('patch','[PATCH NOT INCLUDED BY API]'))
for suffix in (() if '--brief' in sys.argv else ('reviews','review_comments')):
    for c in json.loads((folder/f'pr_{pr}_{suffix}.json').read_text()):
        if c.get('body'):print('REVIEW',c.get('path',''),c['body'])
