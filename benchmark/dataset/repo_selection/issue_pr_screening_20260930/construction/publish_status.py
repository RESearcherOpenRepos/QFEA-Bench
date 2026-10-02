"""Refresh the runtime report and audit manifests from saved execution evidence."""
import csv,json,datetime,collections
from pathlib import Path
from audit_validation import audit
R=Path(__file__).resolve().parent;PAIR=R.parent;SELECTION=PAIR.parent;DATASET=SELECTION.parent

def read_csv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(p,rows):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
cohort=json.loads((R/'cohort.json').read_text());evidence={p.name:audit(p.name) for p in (R/'jobs').iterdir() if p.is_dir()}
samples={}
for p in (DATASET/'samples').glob('*/*/sample.json'):
 d=json.loads(p.read_text());samples[d['instance']['instance_id']]=(p,d)
accepted=[x for x in evidence if evidence[x]['runtime_verified'] and x in samples]
decisions=json.loads((R/'runtime_decisions.json').read_text()) if (R/'runtime_decisions.json').exists() else {}
pending=[x for x in evidence if x not in accepted and x not in decisions]
reviews=read_csv(PAIR/'review_candidates.csv')
for row in reviews:
 sid=row['sample_id']
 if sid=='openqaoa_207_302':row.update(benchmark_status='excluded_open_issue',benchmark_notes='Issue is still open in live GitHub evidence; excluded by the required closed-Issue gate before Docker validation.')
 elif sid in accepted:
  d=samples[sid][1];cfg=json.loads((R/'jobs'/sid/'test_plan.json').read_text());dur=[d['validation'][a][b]['duration_seconds'] for a,b in [('patched','fail_pass'),('patched','pass_pass'),('base','fail_pass'),('base','pass_pass')]]
  row.update(benchmark_status='completed',benchmark_notes=f"Closed Issue; actual 3x per-selector stability plus four offline formal commands verified. F2P={len(cfg['fail_pass'])}, P2P={len(cfg['pass_pass'])}; wall seconds={dur}; platform={cfg.get('platform','linux/amd64')}. Exclusions: {json.dumps(cfg.get('selector_exclusions',{}),ensure_ascii=False)}. Evidence: construction/logs/{sid}/")
 elif sid in decisions:row.update(benchmark_status=decisions[sid]['status'],benchmark_notes=decisions[sid]['reason'])
 elif sid in evidence:row.update(benchmark_status='validation_in_progress',benchmark_notes='Docker built; exact-selector runtime review/stability/formal validation still in progress. Not yet retained as executable sample.')
write_csv(PAIR/'review_candidates.csv',reviews)
byrepo=collections.defaultdict(list)
for sid,(p,d) in samples.items():byrepo[d['instance']['repo']].append((sid,p,d))
manifest=read_csv(SELECTION/'selected_repositories.csv')
for row in manifest:
 ss=sorted(byrepo[row['repository']]);row['sample_count']=str(len(ss));row['sample_ids']='; '.join(x[0] for x in ss)
 if ss:
  sid,p,d=ss[0];row.update(example_sample_metadata='../samples/'+str(p.relative_to(DATASET/'samples')),example_issue=d['instance']['issue_url'],example_pr=d['instance']['pr_url'])
write_csv(SELECTION/'selected_repositories.csv',manifest)
manual=read_csv(SELECTION/'manual_audit.csv')
for row in manual:
 if row['scope_assessment']=='retain_for_pair_screening':row['instance_audit_status']='runtime_validation_in_progress' if pending else 'runtime_validation_complete'
write_csv(SELECTION/'manual_audit.csv',manual)
p=SELECTION/'audit_summary.json';d=json.loads(p.read_text());d.setdefault('baseline_dataset',dict(repositories=7,samples=106));d['current_dataset_repositories']=len(byrepo);d['current_dataset_samples']=len(samples);d['note']='Retrospective audit: 58 proposed exclusions and 11 selected repositories. Original seven not re-audited under the new scope criteria. Runtime outcomes for four newly admitted repositories are separately recorded.';d['new_repository_pair_screening'].update(status='runtime_validation_in_progress' if pending else 'runtime_validation_complete',closed_issue_candidates=13,runtime_validated_new_instances=len(accepted),runtime_pending=len(pending),runtime_report='issue_pr_screening_20260930/construction/README.md');p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
lines=['# Construction validation for closed-issue candidates','',f'Static screening retained 14 pairs; the closed-issue gate excludes one. Of the 13 runtime candidates, **{len(accepted)}** are retained in the active sample index, **{len(pending)}** remain outside the accepted/decision sets, and **{len(decisions)}** have recorded runtime exclusions.','', 'The original 106 tasks are preserved. This command does not regenerate paper statistics or agent experiments. Counts below come from saved execution evidence and the active sample index.','', '| Sample | Status | F2P / P2P | Platform | Wall seconds: patched F2P/P2P, base F2P/P2P |','| --- | --- | --- | --- | --- |']
for row in cohort:
 sid=row['sample_id']
 if sid not in evidence:
  lines.append(f'| {sid} | Excluded: issue is open | — | — | — |');continue
 cfg=json.loads((R/'jobs'/sid/'test_plan.json').read_text());status='Accepted' if sid in accepted else ('Excluded: '+decisions[sid]['reason'] if sid in decisions else 'Pending')
 timing=' / '.join(str(evidence[sid]['formal'].get(k,{}).get('seconds','—')) for k in ['patched_fail_pass','patched_pass_pass','base_fail_pass','base_pass_pass'])
 lines.append(f"| {sid} | {status} | {len(cfg['fail_pass'])} / {len(cfg['pass_pass'])} | {cfg.get('platform','linux/amd64')} | {timing} |")
lines += ['', '## Validation rules', '',
 '- Selected F2P tests pass on patched and fail for the target behavior on base in three repetitions. P2P tests actually pass on both revisions in all repetitions; skip/xfail does not count.',
 '- Four formal commands are also run without networking, each below 120 seconds, with wall time retained.',
 '- Tests that fail when importing a new feature on base are checked separately by selector; one module import failure must not hide other passing cases.',
 '- The two SQD tasks were validated on native ARM. The recorded amd64 emulation lacks JAX-required AVX support; ARM evidence must not be described as amd64 validation.',
 '- Test substitutions, base-passing F2P removals, and environment adjustments are recorded in test_plan.json and CSV notes.',
 '- The three task fields are checked against actual tests. Oracle files are limited to the relevant implementation, and quantum specificity is assessed without agent outcomes.',
 '', '## Evidence', '',
 '`cohort.json` and `evidence/*_issue.json` preserve issue states and source revisions. `jobs/` records construction and test plans; `logs/` records builds, stability checks, selector audits, and formal executions. `validation_summary.json` checks the recorded evidence against selected tests.',
 '', 'Validated sample directories contain sample.json, Dockerfiles, run.sh, selectors, and dependency snapshots. Use each applicable prepare_source.py to reconstruct ignored source.tar.gz from pinned revisions before building repo-base and sample images.']
(R/'README.md').write_text('\n'.join(lines)+'\n')
p=R/'status.json';d=json.loads(p.read_text());d.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='validating' if pending else 'completed',accepted_new_instances=len(accepted),pending_instances=pending,sample_exclusions_from_runtime=decisions,next_action='Complete pending runtime checks' if pending else 'None; see README.md');p.write_text(json.dumps(d,indent=2)+'\n')
print('accepted',len(accepted),'pending',len(pending),'total samples',len(samples))
