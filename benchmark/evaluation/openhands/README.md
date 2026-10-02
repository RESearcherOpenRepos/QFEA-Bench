# OpenHands Evaluation Workflow

This directory contains the OpenHands adapter for the repository-level
code-generation benchmark.

Unless otherwise noted, run the following commands from the repository root.

## Layout

```text
benchmark/evaluation/openhands/
  config/          # model configs and prompt templates
  data/instances/  # exported OpenHands JSONL dataset
  runs/            # raw output.jsonl and converted preds.jsonl
  results/         # evaluator summary results
  scripts/         # export, build, run, and conversion scripts
```

Install sources and environments first: [setup guide](../../../docs/README.md).
Re-export the active 117-task index before starting a new run; keep released
result files separate from new outputs.

## 1. Export Instances

```bash
./.venv/bin/python benchmark/evaluation/openhands/scripts/export_openhands_instances.py \
  --samples-dir benchmark/dataset/samples \
  --output benchmark/evaluation/openhands/data/instances/openhands.secure.jsonl
```

Export a single sample or subset:

```bash
./.venv/bin/python benchmark/evaluation/openhands/scripts/export_openhands_instances.py \
  --samples-dir benchmark/dataset/samples \
  --output benchmark/evaluation/openhands/data/instances/openhands.secure.jsonl \
  --filter qiskit_nature_956_1027
```

## 2. Build Agent Images

OpenHands images are built on top of base-only
`benchmark-agent-base:*` images. Build or refresh those base agent images first:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_agent_base_images.py
```

Then build OpenHands images:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_openhands_images.py \
  --current-only \
  --jobs 1
```

Build a single sample:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_openhands_images.py \
  --filter qiskit_nature_956_1027 \
  --remove-existing \
  --jobs 1
```

Image hierarchy:

```text
benchmark-agent-base:<sample_id> -> benchmark-openhands-<sample_id>:latest
```

## 3. Run The Agent

First set the official DeepSeek API key:

```bash
export DEEPSEEK_API_KEY=...
```

The OpenHands runner must be launched from `external/OpenHands-benchmarks`:

```bash
cd external/OpenHands-benchmarks
```

Run one sample:

```bash
.venv/bin/python ../../benchmark/evaluation/openhands/scripts/run_openhands.py \
  --model-config ../../benchmark/evaluation/openhands/config/deepseek_v4_flash_official.json \
  --prompt-config ../../benchmark/evaluation/openhands/config/new_feature.j2 \
  --dataset ../../benchmark/evaluation/openhands/data/instances/openhands.secure.jsonl \
  --num-workers 1 \
  --n-limit 1 \
  --output-dir ../../benchmark/evaluation/openhands/runs/review_deepseek_v4_flash
```

Run a selected subset:

```bash
.venv/bin/python ../../benchmark/evaluation/openhands/scripts/run_openhands.py \
  --model-config ../../benchmark/evaluation/openhands/config/deepseek_v4_flash_official.json \
  --prompt-config ../../benchmark/evaluation/openhands/config/new_feature.j2 \
  --dataset ../../benchmark/evaluation/openhands/data/instances/openhands.secure.jsonl \
  --select ../../benchmark/evaluation/openhands/data/selected.txt \
  --num-workers 2 \
  --output-dir ../../benchmark/evaluation/openhands/runs/review_deepseek_v4_flash
```

Return to the repository root after the run finishes:

```bash
cd ../..
```

Raw output file:

```text
benchmark/evaluation/openhands/runs/<run_id>/output.jsonl
```

Each completed instance is written as one line in `output.jsonl`. Live logs
during execution are stored under:

```text
benchmark/evaluation/openhands/runs/<run_id>/logs/
```

## 4. Convert Predictions

The runner automatically exports evaluator-readable `preds.json` and
`preds.jsonl`. For an older run containing only raw `output.jsonl`, regenerate
predictions with:

```bash
./.venv/bin/python benchmark/evaluation/openhands/scripts/convert_openhands_preds.py \
  benchmark/evaluation/openhands/runs/review_deepseek_v4_flash/output.jsonl \
  --output benchmark/evaluation/openhands/runs/review_deepseek_v4_flash/preds.jsonl \
  --model-name openhands_deepseek_v4_flash
```

The runner writes `<instance_id>/<instance_id>.summary.json` as soon as each
sample finishes, and atomically updates `preds.json` / `preds.jsonl`. If the
run stops midway, completed sample directories and predictions are preserved.
The conversion script also backfills the same per-instance directories from
`output.jsonl` and `output_errors.jsonl`.

Converted predictions retain only lightweight fields such as the patch and
`step_exhausted`. Per-step tokens are read from `metrics.token_usages` in
`output.jsonl` and written to each sample's
`<instance_id>/<instance_id>.summary.json`, which contains the unified
`schema_version`, `framework`, `instance_id`, and `agent` fields. Rerun this
conversion command on old run directories to backfill these fields.

Native OpenHands logs remain under `logs/` in the run directory. The runner and
conversion script also copy the corresponding `instance_<id>.log` and
`instance_<id>.output.log` into each sample directory as `openhands.log` and
`openhands.output.log`.

## 5. Evaluate

```bash
./.venv/bin/python benchmark/evaluation/scripts/evaluate_agent_preds.py \
  benchmark/evaluation/openhands/runs/review_deepseek_v4_flash/preds.jsonl \
  --output benchmark/evaluation/openhands/results/results_review_deepseek_v4_flash.json \
  --workers 4 \
  --timeout 600 --stable-runs 3
```

The evaluator applies each patch inside the corresponding evaluation image,
then runs fail-pass and pass-pass tests. Each sample is evaluated once by
default; the FSE protocol uses `--stable-runs 3`, as shown above.

## Adapter Tests

From the repository root, run:

```bash
python3 benchmark/evaluation/scripts/run_tests.py --suite openhands
```

This uses `external/OpenHands-benchmarks/.venv/bin/python`, including the local
SDK, tools, workspace, and benchmark packages. After moving the repository,
reinstall the editable packages with the bootstrap workflow; copied virtual
environments may still reference the old source directory. The tests do not
call model APIs or launch benchmark Docker runs.

## Notes

- `runs/` stores raw agent outputs and converted predictions.
- `results/` stores evaluator summaries.
- `config/new_feature.j2` is composed from the shared task description,
  environment description, and OpenHands-specific completion instructions.
- `steps` means the number of assistant/model responses.
- OpenHands SDK's `max_iteration_per_run` limits a single
  `conversation.run()`. The QFEA-Bench runner calls `conversation.run()` only
  once per sample and must not enable fake-user auto-resume; otherwise the same
  sample would receive another step budget and the cumulative step count could
  exceed 100.
- The dsv4-flash config sets `run.max_iterations` to 100 and
  `run.max_retries` to 3. The runner follows native OpenHands semantics and
  accepts either the `finish` tool or a final agent text message as a completion
  signal. If a run ends without any native completion signal, it retries once by
  default, for at most two attempts total; override this with
  `--no-finish-max-attempts` or `run.no_finish_max_attempts` in the config. If
  an attempt reaches 100 steps, the runner writes an empty-patch result with
  `step_budget_exhausted=true`. The sample still fails in the evaluator, but is
  treated as processed during resume and is not given a new solving attempt.
- `token_by_step` aligns with actual tool-action steps via OpenHands
  `ActionEvent.llm_response_id`. The OpenHands SDK may occasionally record
  pre-action LLM usage without a corresponding tool action; the converter folds
  that real cost into the first action step, keeping `token_by_step` aligned
  with `steps` and avoiding undercounting after step-limit handling.

## Supplementary experiment evidence

Released experiment details, including provider recovery records, partial evaluation
snapshots, and cost/completion audits, are archived in
[results/supplementary/](results/supplementary/README.md). Its manifest records the
original location and SHA-256 of every file. The top-level `results/results_*.json`
files remain the canonical evaluator results; archived intermediate attempts must
not be added to performance totals.
