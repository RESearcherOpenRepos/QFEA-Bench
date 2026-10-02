"""Read-only, serial GitHub evidence collection for the 71 historical feature exclusions."""
import csv
import json
import subprocess
from pathlib import Path

OUT=Path(__file__).resolve().parent
CACHE=OUT/'github_evidence'
CACHE.mkdir(exist_ok=True)

def get(endpoint, path, pages=False):
    if path.exists():
        return json.loads(path.read_text())
    cmd=['gh','api',endpoint]
    if pages: cmd+=['--paginate','--slurp']
    obj=json.loads(subprocess.check_output(cmd,text=True))
    if pages: obj=[item for page in obj for item in page]
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    return obj

rows=[r for r in csv.DictReader((OUT/'candidate_decisions.csv').open()) if r['issue_label']=='feature' and r['keep'] in ('no','maybe')]
for n,r in enumerate(rows,1):
    repo=r['repository']
    folder=CACHE/repo.replace('/','__')
    issue=r['issue_url'].rstrip('/').split('/')[-1]
    pr=r['pr_url'].rstrip('/').split('/')[-1]
    data=get(f'repos/{repo}/issues/{issue}',folder/f'issue_{issue}.json')
    get(f'repos/{repo}/issues/{issue}/comments?per_page=100',folder/f'issue_{issue}_comments.json',True)
    get(f'repos/{repo}/pulls/{pr}',folder/f'pr_{pr}.json')
    get(f'repos/{repo}/issues/{pr}/comments?per_page=100',folder/f'pr_{pr}_comments.json',True)
    get(f'repos/{repo}/pulls/{pr}/files?per_page=100',folder/f'pr_{pr}_files.json',True)
    get(f'repos/{repo}/pulls/{pr}/reviews?per_page=100',folder/f'pr_{pr}_reviews.json',True)
    get(f'repos/{repo}/pulls/{pr}/comments?per_page=100',folder/f'pr_{pr}_review_comments.json',True)
    print(f'{n}/71 fetched {r["sample_id"]}',flush=True)
