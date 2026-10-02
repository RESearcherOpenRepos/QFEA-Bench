"""Serial diagnostic replay of hand-specified repairs, isolated from benchmark results."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from benchmark.evaluation.scripts.evaluate_agent_preds import evaluate_one_run

OUT = ROOT / 'rq/rq4/results/rq4_interventions'

def replace_once(patch, before, after):
    assert patch.count(before) == 1, (before, patch.count(before))
    assert before.count('\n') == after.count('\n'), 'Keep diff hunk lengths unchanged'
    return patch.replace(before, after)

def intervention(patch, sample_id, variant):
    if variant == 'original':
        return patch, []
    changes = []
    if sample_id == 87 and variant == 'spin_layout':
        changes = [
            ('+        rdm2_ba = np.einsum("ij,kl->kijl", rdm1_a, rdm1_b)', '+        rdm2_ba = np.einsum("ij,kl->ijkl", rdm1_a, rdm1_b)'),
            ('+                (register_length, 0, 0, register_length),', '+                (0, register_length, register_length, 0),'),
            ('+                    mo_i >= n_spatial\n+                    and mo_j < n_spatial\n+                    and mo_k < n_spatial\n+                    and mo_l >= n_spatial', '+                    mo_i < n_spatial\n+                    and mo_j >= n_spatial\n+                    and mo_k >= n_spatial\n+                    and mo_l < n_spatial'),
            ('+                    rdm2_ba[mo_i - n_spatial, mo_j, mo_k, mo_l - n_spatial] = aux_value.real', '+                    rdm2_ba[mo_i, mo_j - n_spatial, mo_k - n_spatial, mo_l] = aux_value.real'),
        ]
    elif sample_id == 70 and variant in {'qubit_order', 'lookup_protocol', 'combined'}:
        if variant in {'qubit_order', 'combined'}:
            changes.append(('+                    leaves.append("".join(child_paulis))', '+                    leaves.append("".join(reversed(child_paulis)))'))
        if variant in {'lookup_protocol', 'combined'}:
            changes.extend([
                ('+        majorana_paulis = self._majorana_pauli_table(2 * register_length, self.pauli_priority)', '+        majorana_paulis = self._majorana_pauli_table(register_length, self.pauli_priority)'),
                ('+        return [(majorana_paulis[2 * i], majorana_paulis[2 * i + 1]) for i in range(register_length)]', '+        return [(2 * SparsePauliOp(p), SparsePauliOp(["\"])) for p in majorana_paulis]'),
            ])
    elif sample_id == 101 and variant == 'observable_scale':
        changes = [
            ('+        """Return the scaled observable whose expectation is ``1 - 2*x[variable]``."""', '+        """Return the unscaled auxiliary Pauli observable."""'),
            ('+        return SparsePauliOp.from_list([(self._pauli_string([variable]), self._scale([variable]))])', '+        return SparsePauliOp.from_list([(self._pauli_string([variable]), 1.0)])'),
        ]
    else:
        raise ValueError((sample_id, variant))
    for before, after in changes:
        patch = replace_once(patch, before, after)
    return patch, [{'before': a, 'after': b} for a, b in changes]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--runs', type=int, default=1)
    args = parser.parse_args()
    index = json.loads((ROOT / 'benchmark/dataset/samples/index.json').read_text())['samples']
    item = next(x for x in index if x['id'] == args.id)
    sample_path = ROOT / 'benchmark/dataset/samples' / item['sample_path'] / 'sample.json'
    sample = json.loads(sample_path.read_text())
    original = (OUT / f'id{args.id}_original/submission.patch').read_text()
    if args.variant == 'golden':
        command = ['docker', 'run', '--rm', '--network', 'none', '--platform', 'linux/amd64',
                   '--entrypoint', 'git', '-w', '/workspace/repo', sample['runtime']['docker']['image'],
                   'diff', sample['instance']['base_commit'], sample['instance']['patch'], '--',
                   *sample['golden_patch']['oracle_files']]
        patch = subprocess.run(command, capture_output=True, text=True, check=True, timeout=60).stdout
        assert patch.strip()
        changes = [{'reference': 'golden implementation files only; not a minimal repair'}]
    else:
        patch, changes = intervention(original, args.id, args.variant)
    folder = OUT / f"id{args.id}_{args.variant}"
    folder.mkdir(parents=True, exist_ok=True)
    patch_path = folder / 'submission.patch'
    if patch_path.exists():
        assert patch_path.read_text() == patch, 'Existing experiment patch differs'
    patch_path.write_text(patch)
    image = sample['runtime']['docker']['image']
    image_id = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image], capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    manifest = {'id': args.id, 'sample_id': item['sample_id'], 'variant': args.variant,
                'changes': changes, 'image': image, 'image_id': image_id,
                'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
                'scope': 'diagnostic replay; no changes to benchmark definition or official outcome'}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for run in range(1, args.runs + 1):
        result_path = folder / f'run_{run}.json'
        if result_path.exists():
            result = json.loads(result_path.read_text())
        else:
            started = time.monotonic()
            result = evaluate_one_run(sample_path, patch, timeout=180, run_index=run)
            result['duration_seconds'] = time.monotonic() - started
            result_path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'id': args.id, 'variant': args.variant, 'run': run,
                          'resolved': result['resolved'], 'infra': result['eval_infra_failure'],
                          'duration_seconds': result.get('duration_seconds'),
                          'suites': {s: {'passed': result[s]['passed'], 'total': result[s]['total']} for s in ['fail_pass', 'pass_pass']},
                          'nonpassing': [c for cs in result['test_cases'].values() for c in cs if c['status'] != 'passed']}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
