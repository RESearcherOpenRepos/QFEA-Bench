# mini-SWE-agent Evaluation Workflow

This directory contains the mini-SWE-agent adapter for the repository-level
code-generation benchmark.

Unless otherwise noted, run the following commands from the repository root.

## Layout

```text
benchmark/evaluation/minisweagent/
  config/          # model configs and prompt templates
  data/instances/  # exported mini-SWE-agent instance files
  runs/            # agent trajectories and prediction files
  results/         # evaluation summary results
  scripts/         # export, build, run, and image-check scripts
```

Install sources and environments first: [setup guide](../../../docs/README.md).
Re-export the active 117-task index before starting a new run; keep released
result files separate from new outputs.

## 1. Export Instances

```bash
./.venv/bin/python benchmark/evaluation/minisweagent/scripts/export_sweagent_instances.py \
  --samples-dir benchmark/dataset/samples \
  --output benchmark/evaluation/minisweagent/data/instances/sweagent.secure.jsonl \
  --format expert \
  --image-prefix benchmark-minisweagent-
```

The exported `sweagent.secure.jsonl` file is consumed by the run script.

## 2. Build Agent Images

Build or refresh agent images that contain only the benchmark code:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_minisweagent_images.py \
  --current-only
```

Build only missing images:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_minisweagent_images.py \
  --missing-only
```

Build a single sample:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_minisweagent_images.py \
  --filter qiskit_nature_956_1027
```

Optional: check agent images:

```bash
./.venv/bin/python benchmark/evaluation/minisweagent/scripts/check_minnisweagent_images.py \
  --filter qiskit_nature_956_1027
```

## 3. Run The Agent

First set the official DeepSeek API key:

```bash
export DEEPSEEK_API_KEY=...
```

Run the first 20 samples with two workers:

```bash
./.venv/bin/python benchmark/evaluation/minisweagent/scripts/run_minisweagent.py \
  --instances benchmark/evaluation/minisweagent/data/instances/sweagent.secure.jsonl \
  --output-dir benchmark/evaluation/minisweagent/runs/review_deepseek_v4_flash \
  --prompt-config benchmark/evaluation/minisweagent/config/new_feature.yaml \
  --model-config benchmark/evaluation/minisweagent/config/deepseek_v4_flash_official.yaml \
  --workers 2 \
  --n-limit 20
```

Run a single sample:

```bash
./.venv/bin/python benchmark/evaluation/minisweagent/scripts/run_minisweagent.py \
  --instances benchmark/evaluation/minisweagent/data/instances/sweagent.secure.jsonl \
  --output-dir benchmark/evaluation/minisweagent/runs/review_deepseek_v4_flash \
  --prompt-config benchmark/evaluation/minisweagent/config/new_feature.yaml \
  --model-config benchmark/evaluation/minisweagent/config/deepseek_v4_flash_official.yaml \
  --workers 1 \
  --filter qiskit_nature_956_1027
```

Main output files:

```text
benchmark/evaluation/minisweagent/runs/<run_id>/preds.json
benchmark/evaluation/minisweagent/runs/<run_id>/<instance_id>/<instance_id>.traj.json
benchmark/evaluation/minisweagent/runs/<run_id>/<instance_id>/<instance_id>.summary.json
```

When resuming with the same `--output-dir`, completed
`<instance_id>/<instance_id>.traj.json` files are skipped; partially written
but incomplete trajectories are rerun. Add `--redo-existing` to force reruns.

## 4. Evaluate

```bash
./.venv/bin/python benchmark/evaluation/scripts/evaluate_agent_preds.py \
  benchmark/evaluation/minisweagent/runs/review_deepseek_v4_flash/preds.json \
  --output benchmark/evaluation/minisweagent/results/results_review_deepseek_v4_flash.json \
  --workers 4 \
  --timeout 600 --stable-runs 3
```

The evaluator applies each patch inside the corresponding evaluation image,
then runs fail-pass and pass-pass tests. Each sample is evaluated once by
default; the FSE protocol uses `--stable-runs 3`, as shown above.

## Notes

- `runs/` stores raw agent trajectories and `preds.json`.
- `results/` stores evaluation summaries.
- `config/new_feature.yaml` is composed from the shared task description,
  environment description, and mini-SWE-agent-specific submission instructions.
- `steps` means the number of model responses.
- The default `step_limit` is 100.
- After reaching `step_limit`, mini-SWE-agent records
  `exit_status=LimitsExceeded` in the trajectory. The runner treats this as a
  completed agent run and skips the sample during resume; the patch in
  `preds.json` is empty, so the evaluator still marks the sample unresolved.
- The runner writes both `preds.json` and `preds.jsonl` using the unified
  `benchmark/evaluation/common/output_schema.py` format.
- Each sample's `<instance_id>.traj.json` retains the raw mini-SWE-agent
  trajectory, while unified metrics are written to
  `<instance_id>.summary.json`.
- `preds.json` / `preds.jsonl` do not store the detailed `agent` field. They
  retain only the patch and `step_exhausted`; per-step tokens are stored in
  `agent.token_by_step` and `agent.cumulative_token_by_step` inside the
  summary, and the evaluator reads them from there.
- Old run directories can be completed by re-exporting predictions or rerunning
  the runner, as long as the trajectory files are preserved.

## Supplementary experiment evidence

Released experiment details, including provider recovery records, partial evaluation
snapshots, and cost/completion audits, are archived in
[results/supplementary/](results/supplementary/README.md). Its manifest records the
original location and SHA-256 of every file. The top-level `results/results_*.json`
files remain the canonical evaluator results; archived intermediate attempts must
not be added to performance totals.
