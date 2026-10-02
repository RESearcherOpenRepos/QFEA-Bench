"""Build the never-resolved cohort and serial testcase audit queue.

Only joins existing labels and outcomes. Never infers or assigns root causes.
Generated files are separate from the human-reviewed root-cause ledger.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / 'rq/rq3/results'
OUT = ROOT / 'rq/rq4/results/rq4_dominant_testcases'


def read_json(path):
    return json.loads(path.read_text())


def main():
    OUT.mkdir(exist_ok=True)
    samples = read_json(ROOT / 'benchmark/dataset/samples/index.json')['samples']
    ids = {s['sample_id']: s['id'] for s in samples}
    with (ROOT / 'rq/rq1/results/current/all_runs_overview.csv').open() as handle:
        settings = list(csv.DictReader(handle))
    assert len(ids) == len(samples) and len(settings) == 15
    assert sorted(Counter(s['agent'] for s in settings).values()) == [5, 5, 5]
    runs = []
    for setting in settings:
        agent = {'mini-swe': 'minisweagent'}.get(setting['agent'], setting['agent'])
        run = setting['run_id']
        official_path = ROOT / setting['result_path']
        replay_path = RESULTS / f'casewise_replays/{agent}_{run}.json'
        official = {r['instance_id']: r for r in read_json(official_path)['results']}
        replay = {r['instance_id']: r for r in read_json(replay_path)['results']}
        assert set(official) == set(replay) == set(ids)
        assert all(type(r['resolved']) is bool for r in official.values())
        runs.append(dict(agent=agent, run=run, official=official, replay=replay,
                         official_source=str(official_path.relative_to(ROOT)),
                         replay_source=str(replay_path.relative_to(ROOT))))
    assert len({(r['agent'], r['run']) for r in runs}) == 15
    official_cohort = {s for s in ids if all(not r['official'][s]['resolved'] for r in runs)}
    replay_cohort = {s for s in ids if all(not r['replay'][s]['resolved'] for r in runs)}
    # RQ1--RQ4 now share the corrected selected-test evaluations.
    corrections = read_json(OUT / 'validated_resolutions.json')
    for correction in corrections:
        sid = correction['sample_id']
        run = next(r for r in runs if (r['agent'], r['run']) ==
                   (correction['agent'], correction['run']))
        assert run['official'][sid]['resolved'] and run['replay'][sid]['resolved']
    assert official_cohort == replay_cohort
    corrected_cohort = official_cohort
    inventory = []
    cohort = []
    for sid in sorted(corrected_cohort, key=ids.get):
        paths = list((RESULTS / 'sample_constraint_annotations').glob(f'{ids[sid]:03d}_*.json'))
        assert len(paths) == 1
        ann = read_json(paths[0])
        assert ann['sample_id'] == sid
        keys = {(t['split'], t['selector']) for t in ann['tests']}
        assert len(keys) == len(ann['tests'])
        outcomes = []
        for run in runs:
            replay = run['replay'][sid]
            cases = {(split, t['selector']): t
                     for field, split in [('fail_pass', 'F2P'), ('pass_pass', 'P2P')]
                     for t in replay['test_cases'][field]}
            assert set(cases) == keys
            assert all(t['status'] in {'passed', 'failed', 'not_run', 'not_collected', 'skipped'}
                       for t in cases.values())
            assert all(t['status'] == 'passed' for t in cases.values()) == replay['resolved']
            outcomes.append((run, replay, cases))
        sample_inventory = []
        for test in ann['tests']:
            assert isinstance(test['label'], str)
            observations = []
            for run, replay, cases in outcomes:
                case = cases[test['split'], test['selector']]
                observations.append(dict(
                    agent=run['agent'], run=run['run'], status=case['status'],
                    phase=case.get('phase', ''), submitted=replay['agent_submitted'],
                    patch_applied=replay.get('patch_applied'),
                    eval_infra_failed=replay.get('eval_infra_failed'),
                    replay_source=run['replay_source'], official_source=run['official_source'],
                    prediction_source=f"benchmark/evaluation/{run['agent']}/runs/{run['run']}/preds.json"))
            counts = Counter(o['status'] for o in observations)
            record = dict(id=ids[sid], sample_id=sid, test_number=test['test_number'],
                          split=test['split'], selector=test['selector'], constraint_label=test['label'],
                          annotation_source=str(paths[0].relative_to(ROOT)),
                          status_counts=dict(counts), eligible=counts['failed'] > 0,
                          observations=observations)
            inventory.append(record)
            sample_inventory.append(record)
        cohort.append(dict(id=ids[sid], sample_id=sid, selected_tests=len(sample_inventory),
                           ever_failed_tests=sum(t['eligible'] for t in sample_inventory),
                           failed_in_all_15=sum(t['status_counts'].get('failed', 0) == 15 for t in sample_inventory),
                           passed_in_all_15=sum(t['status_counts'].get('passed', 0) == 15 for t in sample_inventory),
                           replay_also_never_resolved=sid in replay_cohort))
    queue = [t for t in inventory if t['eligible']]
    summary = dict(settings=15, benchmark_samples=len(ids),
                   corrected_never_resolved_samples=len(official_cohort),
                   validated_resource_corrections=corrections,
                   cohort_samples=len(cohort),
                   selected_tests=len(inventory), eligible_ever_failed_tests=len(queue),
                   eligible_split_counts=dict(Counter(t['split'] for t in queue)),
                   eligible_category_counts=dict(Counter(t['constraint_label'].split('/')[0] for t in queue)),
                   failed_in_all_15=sum(s['failed_in_all_15'] for s in cohort),
                   passed_in_all_15=sum(s['passed_in_all_15'] for s in cohort),
                   official_replay_cohort_agreement=official_cohort == replay_cohort,
                   official_only_ids=sorted(ids[s] for s in official_cohort - replay_cohort),
                   replay_only_ids=sorted(ids[s] for s in replay_cohort - official_cohort),
                   samples=cohort)
    (OUT / 'cohort.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    for name, rows in [('testcase_inventory.jsonl', inventory), ('audit_queue.jsonl', queue)]:
        (OUT / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    print(json.dumps({k: v for k, v in summary.items() if k != 'samples'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
