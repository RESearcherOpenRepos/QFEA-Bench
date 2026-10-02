# AutoCodeRover Evaluation

This adapter runs AutoCodeRover in `local-issue` mode on QFEA-Bench instances.

## Fair Task Input

AutoCodeRover's CLI argument is named `--issue-file`, but this adapter does not
write the original GitHub issue, PR metadata, tests, or golden patch into that
file. The file contains only the benchmark task fields:

- `problem_statement`
- `requirements`
- `interface`

The rendered input template is `config/task_spec.j2`.

## Runtime Shape

This adapter does not build per-instance AutoCodeRover images. It reuses the
dataset image from `benchmark/dataset/samples/index.json`, copies
`/workspace/repo` out to a per-instance worktree, and runs AutoCodeRover against
that local repo. In other words, AutoCodeRover does not need an agent-specific
Docker image, but the current runner still needs Docker access to copy the
repository from the benchmark evaluation image.

AutoCodeRover itself still needs a Python environment with its dependencies.
Pass that interpreter with `--acr-python`, or create one under
`external/auto-code-rover/.venv/bin/python`.

Install sources and environments first: [setup guide](../../../docs/README.md).
Re-export the active 117-task index before a new run.

## Export Instances

```bash
./.venv/bin/python benchmark/evaluation/autocoderover/scripts/export_autocoderover_instances.py
```

## Run

```bash
./.venv/bin/python benchmark/evaluation/autocoderover/scripts/run_autocoderover.py \
  --instances benchmark/evaluation/autocoderover/data/instances/autocoderover.secure.jsonl \
  --output-dir benchmark/evaluation/autocoderover/runs/review_deepseek_v4_flash \
  --config-file benchmark/evaluation/autocoderover/config/deepseek_v4_flash_official.json \
  --acr-python external/auto-code-rover/.venv/bin/python \
  --workers 1
```

## Evaluate

```bash
./.venv/bin/python benchmark/evaluation/scripts/evaluate_agent_preds.py \
  benchmark/evaluation/autocoderover/runs/review_deepseek_v4_flash/preds.json \
  --samples-dir benchmark/dataset/samples \
  --output benchmark/evaluation/autocoderover/results/results_review_deepseek_v4_flash.json \
  --workers 1 \
  --timeout 600 --stable-runs 3
```

## Outputs

- `runs/` stores raw AutoCodeRover outputs, per-instance trajectories and
  summaries, and `preds.json` / `preds.jsonl`.
- `results/` stores evaluator summaries named
  `results_<model>_<date>.json`.

## Supplementary experiment evidence

Released experiment details, including provider recovery records, partial evaluation
snapshots, and cost/completion audits, are archived in
[results/supplementary/](results/supplementary/README.md). Its manifest records the
original location and SHA-256 of every file. The top-level `results/results_*.json`
files remain the canonical evaluator results; archived intermediate attempts must
not be added to performance totals.
