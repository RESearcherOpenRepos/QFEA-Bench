"""Serial diagnostic replays for ID64 after restoring patched test dependencies.

This does not edit official benchmark results. Requires the existing Docker
image and the saved Agent predictions.
"""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = 'qiskit_nature_47_77'
OUT = ROOT / 'rq/rq4/results/rq4_dominant_testcases/id64_corrected_replays'
RUNNER = ROOT / 'benchmark/dataset/samples/qiskit-nature/qiskit_nature_47_77/run.sh'
QUEUE = ROOT / 'rq/rq4/results/rq4_dominant_testcases/audit_queue.jsonl'


def main():
    selected = [json.loads(line) for line in QUEUE.read_text().splitlines()
                if line and json.loads(line)['id'] == 64]
    assert len(selected) == 3
    observations = [o for o in selected[0]['observations'] if o['status'] == 'failed']
    assert len(observations) == 12
    OUT.mkdir(parents=True, exist_ok=True)
    for index, observation in enumerate(observations, 1):
        agent, run = observation['agent'], observation['run']
        patch = json.loads((ROOT / observation['prediction_source']).read_text())['predictions'][SAMPLE]['model_patch']
        log = OUT / f'{agent}_{run}.log'
        with tempfile.TemporaryDirectory(prefix='qfea-id64-') as temp_dir:
            patch_path = Path(temp_dir) / 'model.patch'
            patch_path.write_text(patch)
            command = [
                'docker', 'run', '--rm', '--platform', 'linux/amd64', '--entrypoint', 'bash',
                '-e', 'MODEL_PATCH_FILE=/benchmark/model.patch',
                '-v', f'{RUNNER}:/benchmark/run.sh:ro',
                '-v', f'{patch_path}:/benchmark/model.patch:ro',
                'benchmark-evaluation:qiskit_nature_47_77',
                '/benchmark/run.sh', 'base', 'fail-pass',
            ]
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, check=False)
        log.write_text(result.stdout)
        failures = [line for line in result.stdout.splitlines() if line.startswith('FAILED ')]
        print(f'{index}/12 {agent} {run}: exit={result.returncode}, failed={len(failures)}', flush=True)
        for failure in failures:
            print('  ' + failure, flush=True)


if __name__ == '__main__':
    main()
