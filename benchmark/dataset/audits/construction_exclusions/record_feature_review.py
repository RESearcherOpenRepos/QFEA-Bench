"""Save a manually supplied conclusion for one reviewed candidate."""
import csv,json,sys,datetime
from pathlib import Path
OUT=Path(__file__).resolve().parent
rows=[r for r in csv.DictReader((OUT/'candidate_decisions.csv').open()) if r['issue_label']=='feature' and r['keep'] in ('no','maybe')]
a=json.load(sys.stdin); r=rows[a['ordinal']-1]
a.update(sample_id=r['sample_id'],historical_keep=r['keep'],issue_url=r['issue_url'],pr_url=r['pr_url'],audit_type='retrospective_source_review',reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtime_validation=False)
p=OUT/'feature_reaudit.jsonl'
old=[json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
assert a['sample_id'] not in {x['sample_id'] for x in old},'Already recorded; edit explicitly if revising'
with p.open('a') as f:f.write(json.dumps(a,ensure_ascii=False)+'\n')
print('Recorded',a['ordinal'],a['sample_id'],a['primary_reason'])
