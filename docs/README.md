# FSE review and setup

## FSE review guide

This guide covers the FSE review artifact: **117 active tasks, 11 repositories, 15 settings**. All commands below run from the repository root. The offline path uses released evidence and does not generate new agent submissions.

Release preparation checks are recorded in [validation-results.json](validation-results.json): 92 adapter/evaluator tests passed, current tables rebuilt identically from a clean publication copy, and the RQ3/RQ4 summaries reproduced.

### 1. Check the cohort and preserved evidence

With Python 3.10 or newer:

```bash
python3 rq/rq1/scripts/verify_revision.py
python3 rq/rq3/scripts/audit_casewise_replays.py
python3 rq/rq4/scripts/summarize_rq4_dominant_testcases.py
```

The cohort verifier checks the active IDs, raw-result hashes, retained evaluations and testcase records against the archived 119-task snapshot, root-cause annotation preservation, table arithmetic, and reported relationships. It writes [verification.json](../rq/rq1/results/cohort_revision_20261002/verification.json). Expected values are 117 tasks, 15 settings, 1,755 outcomes, 623 F2P and 994 P2P selectors, and 69 tasks resolved by the best setting. The RQ4 summary validates existing labels against observed statuses and must produce 280 tests and 1,907 failures across 38 tasks.

These checks validate internal consistency and recorded evidence. They do not independently rerun Docker tests, reproduce model generations, or establish human annotation agreement.

### 2. Rebuild summary tables

The following commands need only the standard library. They overwrite derived summaries while preserving underlying annotations and evaluation records:

```bash
python3 rq/rq3/scripts/summarize_casewise_by_agent.py
python3 rq/rq3/scripts/summarize_casewise_by_subcategory.py
python3 rq/rq3/scripts/summarize_sample_resolution_by_constraint.py
python3 rq/rq4/scripts/prepare_rq4_dominant_testcases.py
python3 rq/rq4/scripts/summarize_rq4_dominant_testcases.py
```

RQ3 outputs are in [summary/](../rq/rq3/results/summary/). RQ4 outputs are in [rq4_dominant_testcases/](../rq/rq4/results/rq4_dominant_testcases/). Their unit of counting is the selected selector; parameterized runtime items do not create extra selected tests.

### 3. Rebuild performance, difficulty, and figures

Use a separate Python 3.11 analysis environment (the pinned scientific packages were validated with Python 3.11.3):

```bash
python3.11 -m venv .venv-analysis
.venv-analysis/bin/python -m pip install -r docs/analysis-requirements.txt
.venv-analysis/bin/python rq/refresh_extended_paper.py
.venv-analysis/bin/python rq/rq3/scripts/plot_constraint_overview.py
```

The refresh script merges historical corrected outcomes with the extension evidence, filters to the active index, and regenerates RQ1/RQ2 CSVs, figures, a LaTeX table, and regression outputs in [RQ1 current results](../rq/rq1/results/current/README.md) and [RQ2 current results](../rq/rq2/results/current/README.md). The released `recorded_agent_metrics.json` supplies steps/token inputs and source-summary hashes, so no local run summaries are required. It uses no model API or Docker. The manuscript directory is unnecessary; `--update-paper` is an optional author-side operation requiring that directory.

The analysis environment versions in `analysis-requirements.txt` describe the environment used for release validation. A fresh install needs network access. The current regression omits repository fixed effects following the archived separation diagnostic; do not substitute the older 106-task regression. OpenHands–Gemini token averages combine measured and explicitly estimated values for four active tasks.

### 4. Inspect a task or failure

1. Find the stable ID and `sample_path` in [index.json](../benchmark/dataset/samples/index.json).
2. Read that sample's `sample.json`, `Dockerfile`, `Dockerfile.repo-base`, and `run.sh`. The specification, base/reference commits, selectors, and platform are stored with the task.
3. Match `instance_id` to [current evaluation records](../rq/rq1/results/current/evaluations/) and [casewise replays](../rq/rq3/results/casewise_replays/).
4. For constraints, inspect [sample_constraint_annotations/](../rq/rq3/results/sample_constraint_annotations/) and the [protocol](../rq/rq3/README.md). The annotation directory retains 119 historical task records; analysis selects 117 via the index.
5. For failure causes, use [manual.jsonl](../rq/rq4/results/rq4_dominant_testcases/manual.jsonl), [failure_observations.csv](../rq/rq4/results/rq4_dominant_testcases/failure_observations.csv), and linked evidence. One testcase can have different causes across configurations. Nonexecution does not establish a cause.

Archived logs may name local run paths that are not included in the release. Full framework checkouts, full raw trajectories, local images, and the manuscript are excluded. Structured outcomes, selected patches/logs, source snapshots, and cohort-comparison evidence are included. The release does not claim that every archived local path is independently downloadable.

Supplementary experiment records are stored under each agent's `results/supplementary/`:
[AutoCodeRover](../benchmark/evaluation/autocoderover/results/supplementary/README.md),
[Mini-SWE-Agent](../benchmark/evaluation/minisweagent/results/supplementary/README.md), and
[OpenHands](../benchmark/evaluation/openhands/results/supplementary/README.md).
Each archive includes source/destination hashes and a reconciliation against the final
results. Intermediate failures and partial snapshots are historical evidence; do not
include them as extra outcomes. See the [migration inventory](result-evidence-migration.json).

### 5. Run agents or container validation

Follow [setup](README.md), the [image workflow](../benchmark/dataset/README.md), and the corresponding [adapter guide](../README.md#run-new-experiments). New model generations need provider credentials and incur provider usage. Container validation of an existing patch does not call the model. Use a new run name and output path to preserve released results.

For a prediction file produced by a new run:

```bash
.venv/bin/python benchmark/evaluation/scripts/evaluate_agent_preds.py   /path/to/new-run/preds.json   --samples-dir benchmark/dataset/samples   --output /path/to/new-run/evaluation.json   --workers 1 --timeout 600 --stable-runs 3
```

Three validations are executions of the same submitted patch. The selected historical experiments also preserve resource corrections and interruption/retry provenance. Results may differ with provider, model revision, hardware, or dependency changes; consult each run's configuration and recorded metadata.

## Setup for new experiments

The current FSE artifact uses 117 tasks across 11 repositories. Offline result verification does not need any agent framework or Docker; see the [review guide](README.md). This page covers new agent runs and container evaluation.

### Requirements

Use Git, Docker, Python 3.11 for the root/analysis environment, and Python 3.12 or newer for OpenHands. Docker must support the platform recorded in each sample. Most tasks use `linux/amd64`; the two qiskit-addon-sqd additions were validated on native `linux/arm64`. Their JAX runtime may fail under amd64 emulation without AVX support.

Network access is needed to retrieve sources, dependencies, and images. Model runs additionally need credentials for the chosen provider. No model credential is needed to evaluate an already saved patch. Full runs require substantially more storage and time than offline analysis; start with one task and inspect its logs before scaling out.

### Framework sources

The release excludes `external/`. The following revisions match the local framework checkouts recorded during review preparation. They identify reproducible source versions; run metadata remains the authority for the original experiments.

| Framework | Source | Revision |
| --- | --- | --- |
| Mini-SWE-Agent | [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | `bc85a45654e6348dcc6e4c5a40ad146ed0bb144d` |
| OpenHands benchmarks | [OpenHands/benchmarks](https://github.com/OpenHands/benchmarks) | `39490d3ef69d02f53827c85bef614f1df51dfd86` |
| OpenHands SDK submodule | [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | `3e0a3a0915b369c7e2057c77722e98585855d30a` |
| AutoCodeRover | [AutoCodeRoverSG/auto-code-rover](https://github.com/AutoCodeRoverSG/auto-code-rover) | `585d3e639aeda58ef0b6a151dd1cc2721a94d267` |

From a fresh repository checkout:

```bash
mkdir -p external
git clone https://github.com/SWE-agent/mini-swe-agent.git external/mini-swe-agent
git -C external/mini-swe-agent checkout bc85a45654e6348dcc6e4c5a40ad146ed0bb144d
git clone https://github.com/OpenHands/benchmarks.git external/OpenHands-benchmarks
git -C external/OpenHands-benchmarks checkout 39490d3ef69d02f53827c85bef614f1df51dfd86
git -C external/OpenHands-benchmarks submodule update --init --recursive
git -C external/OpenHands-benchmarks apply ../../benchmark/evaluation/patches/openhands-benchmarks.patch
git clone https://github.com/AutoCodeRoverSG/auto-code-rover.git external/auto-code-rover
git -C external/auto-code-rover checkout 585d3e639aeda58ef0b6a151dd1cc2721a94d267
```

The [OpenHands integration patch](../benchmark/evaluation/patches/openhands-benchmarks.patch) preserves the local `iptables` runtime dependency and missing-finish classification change. Apply it once to a clean checkout. Existing checkouts should be inspected before changing revisions or applying it.

### Python environments

Create the root and OpenHands environments after retrieving the sources:

```bash
python3 benchmark/dataset/scripts/bootstrap_local_envs.py   --python python3.11 --openhands-python python3.12
```

The bootstrap installs the Mini-SWE-Agent source and OpenHands' vendored SDK packages, and creates `.venv/` plus `external/OpenHands-benchmarks/.venv/`. It installs package requirements, not a complete historical dependency lock. Do not copy virtual environments between machines. Use the separately pinned [analysis requirements](analysis-requirements.txt) for paper statistics.

AutoCodeRover uses its own interpreter. Follow the installation instructions at its pinned revision, including platform-specific native dependencies, and pass its interpreter using `--acr-python`. The adapter's default location is `external/auto-code-rover/.venv/bin/python`; the root/bootstrap environment does not create it. The upstream requirements include platform-specific packages and should not be assumed to install unchanged on every operating system.

### Images, instances, and credentials

Follow the [image workflow](../benchmark/dataset/README.md). Each sample records its build context and source commits. For added sample contexts that use `source.tar.gz`, run their `prepare_source.py` before building; the source archive is regenerated from pinned revisions. Published registry tags are an optional cache, not a guarantee that all current images are available.

Export instances from the current index using the relevant adapter guide:

- [Mini-SWE-Agent](../benchmark/evaluation/minisweagent/README.md)
- [OpenHands](../benchmark/evaluation/openhands/README.md)
- [AutoCodeRover](../benchmark/evaluation/autocoderover/README.md)

Set credentials through environment variables described in [API providers](../benchmark/evaluation/README.md). Keep new run outputs separate from the released results. The evaluator's `--stable-runs 3` validates the same prediction three times; it does not run the agent three times.

### Adapter and evaluator checks

```bash
python3 benchmark/evaluation/scripts/run_tests.py
```

The wrapper runs the core suite in `.venv/` and OpenHands tests in its separate environment. Use `--suite core` or `--suite openhands` to run one suite. These checks use fixtures/mocks and do not launch paid experiments. They do not replace the sample-level F2P/P2P validations recorded in the dataset.
