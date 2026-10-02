import json,csv,re,collections,statistics
from pathlib import Path
ROOT=Path.cwd(); OUT=ROOT/'rq/rq1/results/paper_consistency_audit_20261002';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text())
def csvr(p):return list(csv.DictReader(open(p)))
samples={d['instance']['instance_id']:d for p in Path('benchmark/dataset/samples').glob('*/*/sample.json') for d in [read(p)]}
ann={d['sample_id']:d for p in Path('rq/rq3/results/sample_constraint_annotations').glob('*.json') for d in [read(p)] if d['sample_id'] in samples}
evals={p.stem:read(p)['results'] for p in Path('rq/rq1/results/current/evaluations').glob('*.json')}
errors=[]; warnings=[];out={}
def check(ok,msg):
 if not ok:errors.append(msg)
check(len(samples)==117,'Active sample count !=117')
check(set(ann)==set(samples),'Constraint annotations do not match active sample IDs')
check(len(evals)==15,'Settings !=15')
counts=collections.Counter();catcounts=collections.Counter();quantum={};label={}
for sid,d in samples.items():
 tests=ann[sid]['tests']; akeys={(t['split'],t['selector']) for t in tests}
 expected={(split,s) for split,suite in [('F2P','fail_pass'),('P2P','pass_pass')] for s in d['validation']['patched'][suite]['file_list']}
 check(akeys==expected,f'{sid}: annotation-selector mismatch')
 check(len(akeys)==len(tests),f'{sid}: duplicated labels')
 quantum[sid]=any(t['split']=='F2P' and t['label'].startswith('quantum_semantics/') for t in tests)
 for t in tests:
  cat=t['label'].split('/')[0];label[sid,t['split'],t['selector']]=cat;counts[t['split']]+=1;catcounts[t['split'],cat]+=1
never=set(samples);settings={};protocol=collections.Counter();rootmap={};agg=collections.Counter();pooled=collections.Counter();rrmap={}
caprows=csvr('rq/rq1/results/current/rq1_step_cap_main_table.csv')
caplookup={r['agent']+'_'+r['run_id']:r for r in caprows}
for name,rs in evals.items():
 ids=[r['instance_id'] for r in rs];check(len(ids)==117 and set(ids)==set(samples),name+': sample coverage')
 resolved={r['instance_id'] for r in rs if r['resolved']};never-=resolved
 cap=caplookup[name];check(len(resolved)==int(cap['100_resolved']),name+': resolved mismatch')
 agent=cap['agent'];passes=collections.Counter();byq=collections.Counter();rmap={r['instance_id']:r for r in rs};rrmap[name]=rmap
 for r in rs:
  sid=r['instance_id'];q=quantum[sid];pooled[q,'total']+=1;pooled[q,'resolved']+=int(r['resolved']);byq[q,'resolved']+=int(r['resolved']);byq[q,'total']+=1
  protocol['agent_runs='+str(r.get('agent_runs','absent'))]+=1;protocol['repeat_source='+r.get('evaluation_repeats_source','absent')]+=1
  for split,suite in [('F2P','fail_pass'),('P2P','pass_pass')]:
   cases={c['selector']:c['status'] for c in r.get('test_cases',{}).get(suite,[])}
   for s in samples[sid]['validation']['patched'][suite]['file_list']:
    status=cases.get(s,'not_run') if r.get('patch_applied') else 'not_run'
    rootmap[sid,split,s,agent,name.removeprefix(agent+'_')]=status
    cat=label[sid,split,s];agg[agent,cat,'total']+=1;agg[agent,cat,'passed']+=int(status=='passed');passes[split]+=int(status=='passed')
    if r['resolved']:check(status=='passed',name+': resolved with failing selector '+sid+' '+s)
 for split,prefix in [('F2P','f2p'),('P2P','p2p')]:check(passes[split]==int(cap[f'100_{prefix}_passed']),name+': test numerator mismatch '+split)
 settings[name]={'resolved':len(resolved),'F2P_passed':passes['F2P'],'P2P_passed':passes['P2P'],'quantum_F2P':{'resolved':byq[True,'resolved'],'total':byq[True,'total']},'without_quantum_F2P':{'resolved':byq[False,'resolved'],'total':byq[False,'total']}}
# Cross-check independently maintained RQ3 casewise files.
casewise=[]
for p in Path('rq/rq3/results/casewise_replays').glob('*.json'):
 name=p.stem.replace('minisweagent_','mini-swe_');rs=read(p)['results'];rs=list(rs.values()) if isinstance(rs,dict) else rs
 for r in rs:
  sid=r['instance_id'];ref=rrmap[name][sid]
  check(r['resolved']==ref['resolved'],name+': RQ1/RQ3 resolved disagree '+sid)
  for suite in ['fail_pass','pass_pass']:
   cs={c['selector']:c['status'] for c in r.get('test_cases',{}).get(suite,[])}
   rs2={c['selector']:c['status'] for c in ref.get('test_cases',{}).get(suite,[])}
   check(cs==rs2,name+': RQ1/RQ3 testcase disagree '+sid+' '+suite)
# RQ4: prove each observation refers to an observed failure in retained cohort.
obs=csvr('rq/rq4/results/rq4_dominant_testcases/failure_observations.csv');seen=set();casca=collections.defaultdict(set);rc=collections.Counter();rccat=collections.Counter()
for r in obs:
 agent='mini-swe' if r['agent']=='minisweagent' else r['agent'];key=(r['sample_id'],r['split'],r['selector'],agent,r['run'])
 check(key not in seen,'Duplicate RQ4 observation '+str(key));seen.add(key)
 check(r['sample_id'] in never,'RQ4 sample not never resolved '+r['sample_id'])
 check(rootmap.get(key)=='failed','RQ4 observation not failed '+str(key)+' status='+str(rootmap.get(key)))
 casca[key[:3]].add(r['cause']);rc[r['cause']]+=1;rccat[label[key[:3]],r['cause']]+=1
hardtests=sum(len(ann[s]['tests']) for s in never)
# Recompute RQ2 cells, medians, and compare regression dataset.
foot=csvr('rq/rq2/results/current/engineering_complexity.csv');check({r['sample_id'] for r in foot}==set(samples),'RQ2 footprints coverage')
reg=csvr('rq/rq2/results/current/regression_data.csv');check(len(reg)==1755,'Regression N !=1755')
for row in reg:
 key=next(k for k,v in caplookup.items() if v['agent']+'_'+v['model']==row['setting'])
 check(int(row['resolved'])==int(rrmap[key][row['sample_id']]['resolved']),'Regression outcome mismatch')
# Actual 117 data vs Table 3 cells in LaTeX.
tex=Path('paper/6_evaluation_results.tex').read_text();table=tex.split('\\label{tab:rq2-difficulty}',1)[1].split('\\end{table}',1)[0]
actual=[(int(a),int(b),float(c)) for a,b,c in re.findall(r'\\rqtwocell\{(\d+)/(\d+)\}\{([\d.]+)\\%\}',table)]
expected=[];largezeros=0
models=['gpt-5.5','glm-5.2','gemini-3-flash-preview','deepseek-v4-pro','deepseek-v4-flash'];agents=['mini-swe','openhands','autocoderover']
for model in models:
 for spec in ['medium','strong','all']:
  for agent in agents:
   key=next(k for k,v in caplookup.items() if v['agent']==agent and v['model']==model)
   for size in ['small','medium','large','all']:
    ids=[f['sample_id'] for f in foot if (spec=='all' or f['quantum_depth']==spec) and (size=='all' or f['engineering_complexity']==size)]
    n=sum(rrmap[key][s]['resolved'] for s in ids);expected.append((n,len(ids),float(f'{n/len(ids)*100:.1f}')))
    if spec=='strong' and size=='large' and n==0:largezeros+=1
check(actual==expected,'Table 3 cells mismatch recomputed outcomes')
# Table 2 numeric cells vs CSV, accepting explicitly marked ACR 30-step fallback.
block=tex.split('\\label{tab:overall-results}',1)[1].split('\\end{table}',1)[0]
rows=[l for l in block.splitlines() if re.search(r'GPT-5\.5|GLM-5\.2|Gemini-3-Flash|DeepSeek-v4-',l)]
check(len(rows)==len(caprows)==15,'Table 2 setting coverage mismatch')
for line,rec in zip(rows,caprows):
 cells=line.split('&')[2:];vals=[];want=[]
 for cell in cells:
  cell=re.sub(r'\\cellcolor\{[^}]+\}|\\textbf\{','',cell)
  match=re.search(r'\d[\d,]*(?:\.\d+)?|--',cell);vals.append(match.group(0) if match else None)
 for cap in [100,30]:
  want.extend([f'{float(rec[f"{cap}_{k}"])*100:.1f}' for k in ['submitted_rate','resolved_rate','f2p','p2p']])
  want.append('--' if rec['agent']=='autocoderover' else f'{float(rec[f"{cap}_avg_steps"]):.2f}')
  want.append(f'{float(rec[f"{cap}_avg_tokens"] or rec["100_avg_tokens"]):,.0f}')
 check(vals==want,'Table 2 mismatch '+rec['agent']+' '+rec['model']+': '+str(vals)+' vs '+str(want))
out={'active_cohort':{'instances':len(samples),'repos':dict(collections.Counter(d['instance']['repo'] for d in samples.values())),'test_counts':dict(counts),'specificity':dict(collections.Counter(d['metadata']['quantum_depth'] for d in samples.values()))},'settings':settings,'pooled_test_rates':{agent:{cat:agg[agent,cat,'passed']/agg[agent,cat,'total'] for cat in ['general_semantics','interface','quantum_semantics']} for agent in agents},'RQ3_groups':{'with_quantum_F2P':{'instances':sum(quantum.values()),'resolved':pooled[True,'resolved'],'outcomes':pooled[True,'total'],'never_resolved':sum(quantum[s] for s in never)},'without_quantum_F2P':{'instances':len(samples)-sum(quantum.values()),'resolved':pooled[False,'resolved'],'outcomes':pooled[False,'total'],'never_resolved':sum(not quantum[s] for s in never)}},'RQ4':{'instances':len(never),'selected_tests':hardtests,'observed_failed_testcases':len(casca),'observations':len(obs),'multicause_tests':sum(len(c)>1 for c in casca.values()),'causes':dict(rc)},'RQ2':{'large_strong_zero_settings':largezeros,'median_designated_patch_lines':statistics.median(int(f['gold_solution_lines']) for f in foot),'median_designated_patch_files':statistics.median(int(f['gold_solution_files']) for f in foot)},'protocol_metadata':dict(protocol),'errors':errors,'warnings':warnings}
(OUT/'data_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='settings'},indent=2))

raise SystemExit(1 if errors else 0)
