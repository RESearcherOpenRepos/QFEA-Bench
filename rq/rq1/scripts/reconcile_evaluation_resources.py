#!/usr/bin/env python3
"""Replay resource fixes serially and publish one selected-test outcome source for all RQs.

Historical evaluations remain immutable. Agent metrics come from those original
trajectories; test outcomes come from the structured saved-patch evaluations.
"""
from __future__ import annotations
import argparse
import copy
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from rq.rq1.scripts.analyze_rq1 import HISTORICAL_RUNS
from benchmark.evaluation.common.evaluation_repeats import evaluation_repeat_metadata
OUT = ROOT / 'rq/rq1/results/resource_corrections'
PUBLISHED = ROOT / 'rq/rq1/results/corrected_evaluations'
RESOURCE_IDS = {'qiskit_nature_252_318', 'qiskit_optimization_13_163'}

def read(path):
    return json.loads(path.read_text())

def replay_path(spec):
    agent = 'minisweagent' if spec.agent == 'mini-swe' else spec.agent
    return ROOT / f'rq/rq3/results/casewise_replays/{agent}_{spec.run_id}.json'

def correction_path(spec, sid):
    return OUT / f'{spec.agent}_{spec.run_id}_{sid}.json'

def targets(spec):
    historical = {r['instance_id']: r for r in read(spec.result_path)['results']}
    replay = read(replay_path(spec))
    # Once published, retain the explicitly recorded verification scope.
    if replay.get('resource_reconciliation'):
        return set(replay['resource_reconciliation']['verified_instances'])
    return RESOURCE_IDS | {r['instance_id'] for r in replay['results']
                           if r['resolved'] != historical[r['instance_id']]['resolved']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    specs = [s for s in HISTORICAL_RUNS if s.result_path.exists()]
    assert len(specs) == 15
    OUT.mkdir(parents=True, exist_ok=True)
    if args.replay:
        for spec in specs:
            for sid in sorted(targets(spec)):
                output = correction_path(spec, sid)
                if output.exists():
                    continue
                cmd = [sys.executable, str(ROOT/'benchmark/evaluation/scripts/evaluate_agent_preds.py'),
                       str(spec.run_dir/'preds.json'), '--filter', sid, '--output', str(output),
                       '--stable-runs', '3', '--workers', '1', '--timeout', '300']
                with output.with_suffix('.log').open('w') as log:
                    subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                print(spec.agent, spec.run_id, sid, 'resolved:', read(output)['results'][0]['resolved'], flush=True)
    if not args.publish:
        return
    staged = []
    changes = []
    for spec in specs:
        old = read(spec.result_path)
        historical = {r['instance_id']: r for r in old['results']}
        replay = read(replay_path(spec))
        records = {r['instance_id']: r for r in replay['results']}
        verified = sorted(targets(spec))
        for sid in verified:
            result = read(correction_path(spec, sid))['results'][0]
            assert result['instance_id'] == sid
            assert not result.get('eval_infra_failed') and not result.get('timed_out')
            if result.get('agent_submitted') and result.get('patch_applied'):
                assert len(result['eval_runs']) == 3
            records[sid] = result
        published = []
        totals = dict(fail_pass=0, pass_pass=0)
        repos = {}
        for sid, row in records.items():
            sample_path = next((ROOT/'benchmark/dataset/samples').glob(f'*/{sid}/sample.json'))
            sample = read(sample_path)
            repo = sample_path.parent.parent.name
            rec = repos.setdefault(repo, dict(repo=sample['instance']['repo'],resolved=0,total=0))
            rec['total'] += 1
            rec['resolved'] += int(row['resolved'])
            for suite in totals:
                cases = row['test_cases'][suite]
                selected = sample['validation']['patched'][suite]['file_list']
                assert [t['selector'] for t in cases] == selected
                assert row[suite]['total'] == len(selected)
                assert row[suite]['passed'] == sum(t['status'] == 'passed' for t in cases)
                totals[suite] += len(selected)
            assert row['resolved'] == (bool(row.get('patch_applied')) and all(
                t['status'] == 'passed' for cases in row['test_cases'].values() for t in cases))
            merged = {k:v for k,v in historical[sid].items() if k not in ('stdout','stderr')}
            for key in ('resolved','returncode','patch_applied','eval_infra_failed','eval_infra_failure',
                        'timed_out','fail_pass','pass_pass','test_cases','stable_runs','resolved_runs'):
                if key in row:
                    merged[key] = copy.deepcopy(row[key])
            # Confirmed historical counts need not equal retained log counts.
            row.update(evaluation_repeat_metadata(row))
            merged.update(evaluation_repeat_metadata(row))
            merged['evaluation_source'] = str(replay_path(spec).relative_to(ROOT))
            published.append(merged)
            if historical[sid]['resolved'] != merged['resolved'] or sid in verified:
                changes.append(dict(agent=spec.agent,run=spec.run_id,sample_id=sid,
                                    historical_resolved=historical[sid]['resolved'],resolved=merged['resolved'],
                                    verified_three_times=merged['evaluation_repeats'] == 3))
        assert totals == dict(fail_pass=588, pass_pass=929)
        summary = copy.deepcopy(replay['summary'])
        summary.update(total=106, pending=0, resolved=sum(r['resolved'] for r in records.values()),
                       patch_applied=sum(r.get('patch_applied') is True for r in records.values()))
        for suite in totals:
            passed = sum(r[suite]['passed'] for r in records.values())
            summary[suite] = dict(passed=passed,total=totals[suite],summary=f'{passed}/{totals[suite]}')
        for rec in repos.values():
            rec['resolve_rate'] = rec['resolved']/rec['total']
        summary['per_repo'] = repos
        provenance = dict(historical_source=str(spec.result_path.relative_to(ROOT)),
                          verified_instances=verified, selector_totals=totals,
                          note='Saved patches; corrected resources; three evaluator repeats for evaluable verified instances, not new Agent runs.')
        if replay.get('evaluation_protocol'):
            provenance['evaluation_protocol'] = copy.deepcopy(replay['evaluation_protocol'])
            provenance['note'] = replay['evaluation_protocol']['note']
        replay.update(results=list(records.values()),summary=summary,resource_reconciliation=provenance)
        staged.append((spec,replay,dict(summary=summary,results=published,provenance=provenance)))
    # Validate every setting before publishing any of them.
    PUBLISHED.mkdir(exist_ok=True)
    for spec,replay,published in staged:
        replay_path(spec).write_text(json.dumps(replay,ensure_ascii=False,indent=2)+'\n')
        (PUBLISHED/f'{spec.agent}_{spec.run_id}.json').write_text(json.dumps(published,ensure_ascii=False,indent=2)+'\n')
    (OUT/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
    manifest_path = PUBLISHED/'manifest.json'
    manifest = read(manifest_path) if manifest_path.exists() else {}
    manifest.update({
        'settings': 15, 'samples_per_setting': 106, 'f2p_selectors': 588, 'p2p_selectors': 929,
        'sources': [str(replay_path(spec).relative_to(ROOT)) for spec,_,_ in staged],
    })
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    samples = [read(p) for p in (ROOT/'benchmark/dataset/samples').glob('*/*/sample.json')]
    solved = {r['instance_id'] for _,_,payload in staged for r in payload['results'] if r['resolved']}
    groups = {}
    for depth in ('strong','medium'):
        selected = [s for s in samples if s['metadata']['quantum_depth'] == depth]
        ids = sorted(s['instance']['id'] for s in selected if s['instance']['instance_id'] not in solved)
        groups[depth] = dict(total=len(selected),never_resolved=len(ids),percent=100*len(ids)/len(selected),ids=ids)
    target = ROOT/'rq/rq2/results/never_resolved_by_specificity.json'
    target.write_text(json.dumps(dict(source='Unified corrected selected-test evaluations, all 15 settings',settings=15,groups=groups),indent=2)+'\n')

    print('Published 15 settings with fixed 588 F2P / 929 P2P selectors.')

if __name__ == '__main__':
    main()
