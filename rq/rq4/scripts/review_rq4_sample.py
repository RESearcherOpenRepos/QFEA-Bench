"""Read one sample's evidence, serially. This script never assigns root causes."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'rq/rq4/results'
CONSTRAINT_RESULTS = ROOT / 'rq/rq3/results'
RUNS = {'gpt': 'gpt55_20260604', 'flash': 'deepseek_v4_flash_20260602',
        'pro': 'deepseek_v4_pro_20260602', 'gemini': 'gemini_3_flash_20260604',
        'glm': 'glm5_2_20260626'}


def read_case(dataset_id, alias):
    item = next(x for x in json.loads((ROOT / 'benchmark/dataset/samples/index.json').read_text())['samples'] if x['id'] == dataset_id)
    sid = item['sample_id']
    run = RUNS[alias]
    official = next(x for x in json.loads((ROOT / f'benchmark/evaluation/minisweagent/results/results_{run}.json').read_text())['results'] if x['instance_id'] == sid)
    replay = next(x for x in json.loads((CONSTRAINT_RESULTS / f'casewise_replays/minisweagent_{run}.json').read_text())['results'] if x['instance_id'] == sid)
    ann = json.loads(next((CONSTRAINT_RESULTS / 'sample_constraint_annotations').glob(f'{dataset_id:03d}_*.json')).read_text())
    sample = json.loads((ROOT / 'benchmark/dataset/samples' / item['sample_path'] / 'sample.json').read_text())
    trajpath = ROOT / official['agent']['trajectory_path']
    traj = json.loads(trajpath.read_text())
    return item, official, replay, ann, sample, traj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('id', type=int)
    parser.add_argument('run', choices=RUNS)
    parser.add_argument('--part', choices=['overview', 'patch', 'failures', 'task', 'trajectory'], default='overview')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=24000)
    args = parser.parse_args()
    item, official, replay, ann, sample, traj = read_case(args.id, args.run)
    print('ID', args.id, item['sample_id'], RUNS[args.run], 'official', official['resolved'], 'replay', replay['resolved'])
    if args.part == 'task':
        output = json.dumps({'task': sample['task'], 'tests': ann['tests']}, ensure_ascii=False, indent=2)
    elif args.part == 'patch':
        output = traj.get('info', {}).get('submission', '')
    elif args.part == 'trajectory':
        output = json.dumps(traj['messages'], ensure_ascii=False, indent=2)
    elif args.part == 'failures':
        stdout = replay.get('stdout', '')
        blocks = re.findall(r'^=+ (?:FAILURES|ERRORS) =+\n(.*?)(?=^=+ [^=\n].*?=+|\Z)', stdout, re.M | re.S)
        output = '\n'.join(dict.fromkeys(blocks)) or stdout
    else:
        print('TASK', sample['task'])
        print('EXIT', official['agent'].get('exit_status'), 'PATCH_APPLIED', replay.get('patch_applied'))
        print('RESULT', replay.get('fail_pass'), replay.get('pass_pass'))
        outcomes = {(split, x['selector']): x for key, split in [('fail_pass', 'F2P'), ('pass_pass', 'P2P')] for x in replay.get('test_cases', {}).get(key, [])}
        output = json.dumps([{**t, 'outcome': outcomes.get((t['split'], t['selector']))} for t in ann['tests'] if outcomes.get((t['split'], t['selector']), {}).get('status') != 'passed'], ensure_ascii=False, indent=2)
    print(output[args.offset:args.offset + args.limit])
    if len(output) > args.offset + args.limit:
        print('CONTINUES', 'total_chars', len(output), 'next_offset', args.offset + args.limit)


if __name__ == '__main__':
    main()
