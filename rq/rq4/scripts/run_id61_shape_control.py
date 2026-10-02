"""Reproducible ID61 shape and normalization controls; no official outcome edits."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from benchmark.evaluation.scripts.evaluate_agent_preds import evaluate_one_run

SAMPLE = ROOT / 'benchmark/dataset/samples/qiskit-nature/qiskit_nature_460_482/sample.json'
PREDICTIONS = ROOT / 'benchmark/evaluation/minisweagent/runs/deepseek_v4_pro_20260602/preds.json'
PROBE = Path(__file__).with_name('probe_id61_shape_control.py')
SOURCE = 'qiskit_nature/operators/second_quantization/quadratic_hamiltonian.py'
TEST = 'test/operators/second_quantization/test_quadratic_hamiltonian.py'


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, check=True, timeout=180, **kwargs)


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--probes-only', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'rq/rq4/results/id61_shape_control')
    args = parser.parse_args()
    assert args.runs > 0
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sample = json.loads(SAMPLE.read_text())
    base, ref = sample['instance']['base_commit'], sample['instance']['patch']
    image = sample['runtime']['docker']['image']
    image_id = run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).stdout.strip()
    docker = ['docker', 'run', '--rm', '--network', 'none', '--platform', 'linux/amd64']
    git = docker + ['--entrypoint', 'git', '-w', '/workspace/repo', image_id]
    source = run(git + ['show', ref+':'+SOURCE]).stdout
    reference = run(git + ['diff', base, ref, '--', *sample['golden_patch']['oracle_files']]).stdout
    original = json.loads(PREDICTIONS.read_text())['predictions'][sample['instance']['instance_id']]['model_patch']
    before = '+        transformation_matrix = eigvecs\n'
    assert original.count(before) == 1
    shape_only = original.replace(before, '+        transformation_matrix = eigvecs[:n, :]\n')
    # Change only the normalization in the final Majorana-to-fermion conversion.
    # majorana_form, the Schur calculation, returned energies and constant remain reference.
    start = source.index('    def _non_particle_num_conserving_bogoliubov_transform(')
    head, tail = source[:start], source[start:]
    line = '        majorana_basis = np.block([[eye, eye], [1j * eye, -1j * eye]]) / np.sqrt(2)\n'
    assert tail.count(line) == 1
    mutated = head + tail.replace(line, line.replace(' / np.sqrt(2)', ''))
    mutation = ''.join(difflib.unified_diff(source.splitlines(True), mutated.splitlines(True),
                                          fromfile='a/'+SOURCE, tofile='b/'+SOURCE))
    variants = {'original': original, 'shape_only': shape_only,
                'reference': reference, 'normalization_mismatch': reference + mutation}
    manifest = {'id': 61, 'sample_id': sample['instance']['instance_id'],
                'base': base, 'reference': ref, 'image': image, 'image_id': image_id,
                'runs_per_variant': args.runs, 'agent_predictions': str(PREDICTIONS.relative_to(ROOT)),
                'probe_sha256': digest(PROBE.read_text()),
                'patch_sha256': {k: digest(v) for k, v in variants.items()},
                'scope': 'Diagnostic controls, not additional agent runs or official outcomes.',
                'variants': {'original': 'Unmodified observed Mini-SWE-Agent/DeepSeek-v4-Pro patch.',
                             'shape_only': 'One-line row truncation in the observed patch; no semantic repair.',
                             'reference': 'Reference oracle production files, not a minimal agent repair.',
                             'normalization_mismatch': 'Reference implementation with 1/sqrt(2) omitted only in the final basis conversion; synthetic mutation.'}}
    if (out/'manifest.json').exists():
        assert json.loads((out/'manifest.json').read_text()) == manifest, 'Use a fresh output directory'
    save(out/'manifest.json', manifest)
    (out/'reference_source.py').write_text(source)
    (out/'reference_test.py').write_text(run(git + ['show', ref+':'+TEST]).stdout)
    (out/'normalization_mutation.patch').write_text(mutation)
    summary = {}
    for name, patch in variants.items():
        folder = out/name
        folder.mkdir(exist_ok=True)
        (folder/'submission.patch').write_text(patch)
        if not (folder/'probe.json').exists():
            result = run(docker + ['-i', '--entrypoint', 'python', image_id, '-c', PROBE.read_text()],
                         input=json.dumps({'base': base, 'patch': patch}))
            save(folder/'probe.json', json.loads(result.stdout))
            (folder/'probe.stderr.log').write_text(result.stderr)
        probe = json.loads((folder/'probe.json').read_text())
        summary[name] = {'probe': probe, 'runs': []}
        print(json.dumps({'variant': name, 'probe': probe}), flush=True)
        if not args.probes_only:
            for repeat in range(1, args.runs + 1):
                path = folder/f'run_{repeat}.json'
                if path.exists():
                    result = json.loads(path.read_text())
                else:
                    assert run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).stdout.strip() == image_id
                    result = evaluate_one_run(SAMPLE, patch, timeout=180,
                                              run_index=repeat, total_runs=args.runs)
                    save(path, result)
                assert not result.get('eval_infra_failed') and not result.get('timed_out') and result['patch_applied']
                observation = {'repeat': repeat, 'resolved': result['resolved'],
                               'f2p': result['fail_pass']['summary'], 'p2p': result['pass_pass']['summary'],
                               'nonpassing': [c['selector'] for cases in result['test_cases'].values()
                                              for c in cases if c['status'] != 'passed']}
                summary[name]['runs'].append(observation)
                print(json.dumps({'variant': name, **observation}), flush=True)
    save(out/('probes.json' if args.probes_only else 'summary.json'), summary)


if __name__ == '__main__':
    main()
