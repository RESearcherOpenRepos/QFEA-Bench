#!/usr/bin/env python3
"""Rebuild the active-cohort paper analysis without altering original runs or human annotations.

Run with Python and numpy, pandas, matplotlib, scipy, statsmodels.
By default only repository analysis artifacts are written; --update-paper also
updates the separately maintained local manuscript.
RQ3/RQ4 extensions are maintained separately under their additions_20261002 audit directories.
"""
import argparse
import csv, json, sys, math, hashlib, shutil, statistics
from pathlib import Path
from dataclasses import replace
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'rq/rq1/results/current'
RQ2_OUT=ROOT/'rq/rq2/results/current'
from rq.rq1.scripts.analyze_rq1 import HISTORICAL_RUNS, enriched_rows, cumulative_at_cap, token_total
from rq.rq1.scripts.export_paper_tables import AGENT_LABELS, MODEL_LABELS, count_rate, write_rq2_difficulty_latex
from rq.rq2.scripts.analyze_engineering_complexity import assign_engineering_complexity, count_changed_nonempty_lines

def read(p): return json.loads(p.read_text())
def items(p):
    r=read(p)['results'];return list(r.values()) if isinstance(r,dict) else r

def csvread(p): return list(csv.DictReader(p.open()))
def csvwrite(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update-paper', action='store_true',
                        help='Also update the local paper/ manuscript (not required for review).')
    args = parser.parse_args()
    if args.update_paper and not (ROOT/'paper/6_evaluation_results.tex').is_file():
        parser.error('--update-paper requires the local paper/ manuscript')
    OUT.mkdir(parents=True, exist_ok=True)
    RQ2_OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'evaluations').mkdir(exist_ok=True)
    samples={d['instance']['instance_id']:d for p in (ROOT/'benchmark/dataset/samples').rglob('sample.json') for d in [read(p)]}
    total=len(samples)
    exclusions=read(ROOT/'rq/rq1/results/cohort_revision_20261002/exclusions.json')
    excluded_ids={r['sample_id'] for r in exclusions['exclusions']}
    assert total==exclusions['retained_sample_count']
    selected=csvread(ROOT/'rq/rq1/results/rq1_step_cap_main_table.csv')
    specs={(s.agent,s.model,s.run_id):s for s in HISTORICAL_RUNS}
    metrics_path=OUT/'recorded_agent_metrics.json'
    recorded_metrics=read(metrics_path)['settings']
    runs=[]; corrections=[]; coverage=[]; sources={str(metrics_path.relative_to(ROOT)):hashlib.sha256(metrics_path.read_bytes()).hexdigest()}
    recovery_path=ROOT/'rq/rq1/results/usage_recovery_20261002/openhands_gemini_recovery.json'
    recoveries={}
    if recovery_path.exists():
        recoveries={(r['agent'],r['run_id'],r['instance_id']):r for r in read(recovery_path)['records']}
        sources[str(recovery_path.relative_to(ROOT))]=hashlib.sha256(recovery_path.read_bytes()).hexdigest()
    estimate_path=ROOT/'rq/rq1/results/usage_recovery_20261002/openhands_gemini_token_estimates.json'
    estimates={}
    if estimate_path.exists():
        estimates={(r['agent'],r['run_id'],r['instance_id']):r for r in read(estimate_path)['records']}
        sources[str(estimate_path.relative_to(ROOT))]=hashlib.sha256(estimate_path.read_bytes()).hexdigest()
    original_ids=None
    for sel in selected:
        spec=specs[sel['agent'],sel['model'],sel['run_id']]
        corr=ROOT/f'rq/rq1/results/corrected_evaluations/{spec.agent}_{spec.run_id}.json'
        old={r['instance_id']:r for r in items(corr)}
        raw={r['instance_id']:r for r in items(spec.result_path)}
        assert len(old)==106 and set(old)<=set(samples) and set(raw)==set(samples)|excluded_ids and len(raw)==exclusions['original_sample_count']
        if original_ids is None: original_ids=set(old)
        assert original_ids==set(old)
        corrections += [dict(agent=spec.agent,model=spec.model,instance_id=k,raw_resolved=raw[k]['resolved'],corrected_resolved=v['resolved']) for k,v in old.items() if raw[k]['resolved']!=v['resolved']]
        fields={'instance_id','resolved','agent_submitted','patch_applied','agent_step_exhausted',
                'agent_repeated_command_loop','timed_out','evaluation_repeats','evaluation_repeats_source',
                'evaluation_source','fail_pass','pass_pass','test_cases','agent','telemetry_incomplete',
                'generation_error_kind','observed_agent_steps','generation_provider','agent_runs'}
        merged={k:{f:v for f,v in r.items() if f in fields} for k,r in {**raw,**old}.items() if k in samples}
        # Original outcomes retain the previous resource corrections. New outcomes retain real evaluations.
        path=OUT/'evaluations'/f'{spec.agent}_{spec.run_id}.json'
        path.write_text(json.dumps({'provenance':{'original_corrected':str(corr.relative_to(ROOT)),'additions':str(spec.result_path.relative_to(ROOT)),'cohort_exclusions':'rq/rq1/results/cohort_revision_20261002/exclusions.json'},'results':list(merged.values())},indent=2)+'\n')
        for p in [corr,spec.result_path]:sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        rows=enriched_rows(replace(spec,result_path=path),
                           summary_agents=recorded_metrics[spec.agent+'/'+spec.run_id])
        for r in rows:
            sid=r['item']['instance_id']; item=r['item']
            incomplete=item.get('telemetry_incomplete',False)
            r['metrics_complete']=r['metrics_known'] and not incomplete
            r['steps_complete']=r['metrics_complete']
            recovery=recoveries.get((spec.agent,spec.run_id,sid))
            if recovery:
                assert incomplete and not r['submitted'] and not r['resolved']
                assert recovery['steps_complete'] and not recovery['token_metrics_complete']
                r['steps']=recovery['steps']
                r['agent']={**r['agent'],'steps':recovery['steps']}
                r['steps_complete']=True
            estimate=estimates.get((spec.agent,spec.run_id,sid))
            r['token_estimate']=estimate
            if estimate:
                assert recovery and estimate['usage_measurement']=='estimated'
                assert estimate['steps']==r['steps']
                full=estimate['estimated_usage_by_cap']['100']
                r['agent']={**r['agent'],**{k:full[k] for k in ['input_tokens','output_tokens','cached_input_tokens','cache_creation_input_tokens']},'usage_measurement':'estimated','instance_cost':None}
                merged[sid]['agent']=r['agent']
                merged[sid]['usage_recovery']=estimate
                merged[sid]['telemetry_incomplete']=True
            if r['resolved']: assert r['submitted'] and 0<r['steps']<=100
            r['test_passes']={}
            for suite in ['fail_pass','pass_pass']:
                selectors=samples[sid]['validation']['patched'][suite]['file_list']
                cases=item.get('test_cases',{}).get(suite,[])
                if item.get('patch_applied'):
                    assert {c['selector'] for c in cases}==set(selectors),(spec.model,sid,suite)
                statuses={c['selector']:c['status'] for c in cases}
                r['test_passes'][suite]=sum(statuses.get(s)=='passed' for s in selectors) if item.get('patch_applied') else 0
            if not r['metrics_complete']:coverage.append(dict(agent=spec.agent,model=spec.model,instance_id=sid,reason=item.get('generation_error_kind','missing_metrics'),observed_steps=r['steps'] if r['steps_complete'] else item.get('observed_agent_steps'),steps_complete=r['steps_complete'],token_metrics_complete=False,tokens_estimated=bool(estimate)))
        if any(r['token_estimate'] for r in rows):
            path.write_text(json.dumps({'provenance':{'original_corrected':str(corr.relative_to(ROOT)),'additions':str(spec.result_path.relative_to(ROOT)),'cohort_exclusions':'rq/rq1/results/cohort_revision_20261002/exclusions.json','usage_estimates':str(estimate_path.relative_to(ROOT))},'results':list(merged.values())},indent=2)+'\n')
        runs.append((spec,rows))
    runs.sort(key=lambda x:(list(AGENT_LABELS).index(x[0].agent),list(MODEL_LABELS).index(x[0].model)))
    assert len(runs)==15
    totals={s:sum(len(d['validation']['patched'][s]['file_list']) for d in samples.values()) for s in ['fail_pass','pass_pass']}
    assert totals==dict(fail_pass=623,pass_pass=994)
    table=[]; curves=[]
    for spec,rows in runs:
        rec=dict(agent=spec.agent,model=spec.model,run_id=spec.run_id,total=total)
        for cap in [100,30]:
            within=lambda r: r['submitted'] and 0<r['steps']<=cap
            ns=sum(within(r) for r in rows); nr=sum(r['resolved'] and within(r) for r in rows)
            rec.update({f'{cap}_submitted':ns,f'{cap}_submitted_rate':ns/total,f'{cap}_resolved':nr,f'{cap}_resolved_rate':nr/total})
            for label,suite in [('f2p','fail_pass'),('p2p','pass_pass')]:
                passes=sum(r['test_passes'][suite] for r in rows if within(r))
                rec[f'{cap}_{label}_passed']=passes;rec[f'{cap}_{label}_total']=totals[suite];rec[f'{cap}_{label}']=passes/totals[suite]
            complete=all(r['metrics_complete'] or r['token_estimate'] for r in rows)
            rec[f'{cap}_avg_steps']=statistics.fmean(min(r['steps'],cap) for r in rows) if all(r['steps_complete'] for r in rows) else None
            capped=[(r['token_estimate']['estimated_usage_by_cap'][str(cap)],True) if r['token_estimate'] else cumulative_at_cap(r['agent'],cap) for r in rows]
            rec[f'{cap}_avg_tokens']=statistics.fmean(token_total(m) for m,known in capped) if complete and all(known for m,known in capped) else None
            if cap==100 and complete:rec[f'{cap}_avg_tokens']=statistics.fmean(token_total(r['agent']) for r in rows)
            rec[f'{cap}_token_estimated_instances']=sum(bool(r['token_estimate']) for r in rows)
            if complete and rec[f'{cap}_token_estimated_instances']:
                for bound in ['min','max']:
                    rec[f'{cap}_avg_tokens_reference_{bound}']=statistics.fmean(token_total(r['token_estimate']['estimated_usage_by_cap'][str(cap)]['reference_'+bound]) if r['token_estimate'] else token_total(r['agent']) if cap==100 else token_total(cumulative_at_cap(r['agent'],cap)[0]) for r in rows)
        table.append(rec)
        if spec.agent!='autocoderover':
            for cap in range(10,101,10):
                n=sum(r['resolved'] and 0<r['steps']<=cap for r in rows)
                curves.append(dict(agent=spec.agent,model=spec.model,run_id=spec.run_id,step_cap=cap,resolved=n,resolved_rate=n/total))
    csvwrite(OUT/'rq1_step_cap_main_table.csv',table);csvwrite(OUT/'rq1_step_curve.csv',curves)
    # Preserve measured original footprints; measure additions only from archived full reference diffs.
    oldfoot={r['sample_id']:r for r in csvread(ROOT/'rq/rq2/results/engineering_complexity.csv')}
    strata=[]
    for sid,d in sorted(samples.items()):
        m=d['metadata']; oracle=d['golden_patch']['oracle_files']
        if sid in oldfoot:
            lines=int(oldfoot[sid]['gold_solution_lines']);files=int(oldfoot[sid]['gold_solution_files'])
            assert m['quantum_depth']==oldfoot[sid]['quantum_depth']
        else:
            p=RQ2_OUT/'reference_diffs'/f'{sid}.patch';diff=p.read_text();selected_diff=[]
            for block in diff.split('diff --git ')[1:]:
                header=block.splitlines()[0]
                if any(header==f'a/{f} b/{f}' for f in oracle):selected_diff.append(block)
            lines=count_changed_nonempty_lines('\n'.join(selected_diff));files=len(oracle)
            assert lines>0 and files>0
        strata.append(dict(sample_id=sid,repo=d['instance']['repo'],quantum_depth=m['quantum_depth'],gold_solution_lines=lines,gold_solution_files=files,annotation_source='original_author_annotations' if sid in original_ids else 'construction_metadata_author_confirmed_three_rater_review'))
    assign_engineering_complexity(strata)
    csvwrite(RQ2_OUT/'engineering_complexity.csv',strata)
    byid={r['sample_id']:r for r in strata}
    difficulty=[]
    for spec,rows in runs:
        rec={'Agent':AGENT_LABELS[spec.agent],'LLM':MODEL_LABELS[spec.model],'Run ID':spec.run_id}
        for depth,label in [('medium','Medium'),('strong','Strong'),(None,'Overall')]:
            for size,title in [('small','Small'),('medium','Medium'),('large','Large'),(None,'Total')]:
                group=[r for r in rows if (depth is None or byid[r['item']['instance_id']]['quantum_depth']==depth) and (size is None or byid[r['item']['instance_id']]['engineering_complexity']==size)]
                key=label+' '+title if depth is not None or size is not None else 'Overall'
                rec[key]=count_rate(sum(r['resolved'] for r in group),len(group))
        difficulty.append(rec)
    csvwrite(RQ2_OUT/'difficulty_by_specificity_complexity.csv',difficulty)
    write_rq2_difficulty_latex(difficulty, RQ2_OUT/'rq2_difficulty_all_settings.tex')
    # Reuse the established visual style, with the enlarged cohort and y axis.
    from rq.rq1.scripts import plot_interactive_agents_step_limit_sweep as curve
    curve.draw(curves,OUT/'rq1_interactive_agents_step_limit_sweep')
    if args.update_paper:
        shutil.copy2(OUT/'rq1_interactive_agents_step_limit_sweep.pdf',ROOT/'paper/figures/rq1_interactive_agents_step_limit_sweep.pdf')
    from rq.rq2.scripts import plot_quantum_specificity_split_index_heatmap as heat
    plotted=[dict(agent=s.agent,model=s.model,run_id=s.run_id,label=f'{heat.MODEL_LABELS[s.model]} / {heat.AGENT_LABELS[s.agent]}',resolved={r['item']['instance_id']:r['resolved'] for r in rows}) for s,rows in runs]
    heat.load_complete_runs=lambda: sorted(plotted,key=heat.run_sort_key)
    heat.plot(RQ2_OUT/'engineering_complexity.csv',heat.DEFAULT_SAMPLE_INDEX,RQ2_OUT/'rq2_quantum_specificity_split_index_heatmap')
    if args.update_paper:
        shutil.copy2(RQ2_OUT/'rq2_quantum_specificity_split_index_heatmap.pdf',ROOT/'paper/figures/rq2_quantum_specificity_split_index_heatmap.pdf')
    resolved_any={r['item']['instance_id'] for s,rows in runs for r in rows if r['resolved']}
    excluded='qiskit-community/qiskit-nature'
    subset=[r for s,rows in runs for r in rows if samples[r['item']['instance_id']]['instance']['repo']!=excluded]
    pro={s.agent:{r['item']['instance_id'] for r in rows if r['resolved']} for s,rows in runs if s.model=='deepseek-v4-pro'}
    for p in (ROOT/'benchmark/dataset/samples').rglob('sample.json'):
        sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [ROOT/'rq/rq2/results/engineering_complexity.csv',*sorted((RQ2_OUT/'reference_diffs').glob('*.patch'))]:
        sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    audit=dict(total=total,cohort_exclusions=exclusions,repositories=dict(Counter(d['instance']['repo'] for d in samples.values())),tests=totals,group_sizes=dict(Counter(r['quantum_depth']+'_'+r['engineering_complexity'] for r in strata)),quantum_specificity=dict(Counter(r['quantum_depth'] for r in strata)),never_resolved_by_specificity=dict(Counter(byid[s]['quantum_depth'] for s in set(samples)-resolved_any)),never_resolved=sorted(set(samples)-resolved_any),new_never_resolved=sorted(set(samples)-resolved_any-original_ids),excluded_largest=dict(instances=len(subset)//15,resolved=sum(r['resolved'] for r in subset),outcomes=len(subset)),pro_overlap=dict(shared=len(pro['mini-swe']&pro['openhands']),union=len(pro['mini-swe']|pro['openhands']),mini_only=len(pro['mini-swe']-pro['openhands']),openhands_only=len(pro['openhands']-pro['mini-swe'])),original_corrections=corrections,incomplete_telemetry=coverage,input_sha256=sources)
    # Active-cohort adjusted regression. Repository effects omitted after the separation diagnostic.
    import numpy as np,pandas as pd
    from rq.rq2.scripts.analyze_specificity_regression import fit_model
    tasks=pd.DataFrame(strata).drop(columns='annotation_source')
    tasks['strong']=(tasks.quantum_depth=='strong').astype(int)
    tasks['test_count']=tasks.sample_id.map(lambda sid:sum(len(samples[sid]['validation']['patched'][k]['file_list']) for k in totals))
    for key,values in [('patch_z',tasks.engineering_complexity_score),('tests_z',np.log1p(tasks.test_count))]:tasks[key]=(values-values.mean())/values.std(ddof=0)
    data=pd.DataFrame([dict(sample_id=r['item']['instance_id'],setting=s.agent+'_'+s.model,resolved=int(r['resolved'])) for s,rows in runs for r in rows]).merge(tasks,on='sample_id',validate='many_to_one')
    data.to_csv(RQ2_OUT/'regression_data.csv',index=False)
    try:
        coefficients,diagnostics=fit_model(f'main_full{total}_no_repository_FE','resolved ~ strong + patch_z + tests_z + C(setting)',data)
    except ValueError as exc:
        audit['regression']=dict(status='not_estimable',reason=str(exc),repository_outcomes=data.groupby('repo').resolved.agg(['sum','count']).reset_index().to_dict('records'),paper_scope='Do not report an unstable full-cohort fit.')
    else:
        coefficients.to_csv(RQ2_OUT/'regression_coefficients.csv',index=False)
        audit['regression']=dict(status='estimable',diagnostics=diagnostics,strong=coefficients[coefficients.term=='strong'].to_dict('records')[0],specification_change='Repository fixed effects omitted after quasi-separation was diagnosed in the full119 specification; approved by the author on 2026-10-02. This is an adjusted association, not a repository-adjusted or causal effect.',comparison_audit='rq/rq2/results/specificity_regression_full119/diagnostics.json')
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    if not args.update_paper:
        print(json.dumps({k:v for k,v in audit.items() if k not in ['input_sha256','never_resolved']},indent=2))
        return
    # Update numeric cells of Table 2 and replace Table 3; preserve surrounding prose/comments.
    paper=ROOT/'paper/6_evaluation_results.tex';source=paper.read_text();lines=source.splitlines(keepends=True);idx=0
    for i,line in enumerate(lines):
        cells=line.split(' & ')
        if len(cells)!=14 or not any(m in cells[1] for m in MODEL_LABELS.values()):continue
        rec=table[idx]; assert MODEL_LABELS[rec['model']] in cells[1]
        bg=r'\cellcolor{tablerowgray}' if r'\cellcolor{tablerowgray}' in cells[1] else ''
        for j,(cap,metric) in enumerate(( (c,m) for c in [100,30] for m in ['submitted_rate','resolved_rate','f2p','p2p','avg_steps','avg_tokens']),2):
            field=f'{cap}_{metric}';value=rec[field]
            reused_full_tokens=(rec['agent']=='autocoderover' and cap==30 and metric=='avg_tokens' and value is None)
            if reused_full_tokens:
                field='100_avg_tokens';value=rec[field]
            if metric=='avg_steps' and rec['agent']=='autocoderover':value=None
            bests=[r[field] for r in table if r['agent']==rec['agent'] and r[field] is not None]
            best=value is not None and value==(min(bests) if metric.startswith('avg') else max(bests))
            text='--' if value is None else (f'{value:.2f}' if metric=='avg_steps' else f'{value:,.0f}' if metric=='avg_tokens' else f'{value*100:.1f}'+r'\%')
            if reused_full_tokens:text+=r'$^{\dagger}$'
            if best and metric=='resolved_rate':text=r'\textbf{'+text+'}'
            cells[j]=(r'\cellcolor{rowmaxfill}' if best else bg)+text
        lines[i]=' & '.join(cells)+' \\\\\n';idx+=1
    assert idx==15
    source=''.join(lines);start=source.index('% Generated by rq/rq1/scripts/export_paper_tables.py');end=source.index(r'\end{table}',start)+len(r'\end{table}')
    replacement=(RQ2_OUT/'rq2_difficulty_all_settings.tex').read_text().replace('specificity rows','quantum specificity rows')
    paper.write_text(source[:start]+replacement.rstrip()+source[end:])
    print(json.dumps({k:v for k,v in audit.items() if k not in ['input_sha256','never_resolved']},indent=2))

if __name__=='__main__':main()
