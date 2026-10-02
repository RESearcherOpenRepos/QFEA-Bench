"""Reproduce the selected full119 model and preserve repository-FE diagnostics."""
from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R))
import pandas as pd
from rq.rq2.scripts.analyze_specificity_regression import fit_model
O=Path(__file__).parent
p=R/'rq/rq2/results/before119/regression_data.csv';d=pd.read_csv(p)
assert len(d)==1785 and d.sample_id.nunique()==119 and d.setting.nunique()==15
assert not d.duplicated(['sample_id','setting']).any()
f='resolved ~ strong + patch_z + tests_z + C(repo) + C(setting)'
records=[]
for name,formula,subset in [('full119_original_specification',f,d),('sensitivity_exclude_all_failure_repository',f,d[d.repo!='sQUlearn/squlearn']),('main_full119_without_repository_FE','resolved ~ strong + patch_z + tests_z + C(setting)',d)]:
 try:
  table,diag=fit_model(name,formula,subset);row=table[table.term=='strong'].iloc[0].to_dict();rec=dict(name=name,formula=formula,status='estimable',result=row,diagnostics=diag);table.to_csv(O/(name+'.csv'),index=False)
 except ValueError as e:rec=dict(name=name,formula=formula,status='not_estimable',reason=str(e),tasks=int(subset.sample_id.nunique()),observations=len(subset))
 records.append(rec)
repo=d.groupby('repo').resolved.agg(['sum','count']).reset_index().to_dict('records')
report=dict(source=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),models=records,repository_outcomes=repo,limitations=['Same task-cluster robust GEE specification as original analysis.','Sensitivity fits have different samples or controls and must not be presented as the full119 original specification.','The author selected the full119 model without repository effects on 2026-10-02 after the separation diagnostic; the specification change was not pre-specified.'])
(O/'diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
for r in records:print(json.dumps(r,indent=2))
