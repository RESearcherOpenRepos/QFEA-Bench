# QFEA-Bench: Benchmarking LLM-Based Agents on Repo-Level Quantum Feature Implementation

**Research artifact for FSE 2027 review**

QFEA-Bench evaluates coding agents on feature requests from quantum software repositories. Each task provides a base revision, a structured specification, a reference implementation, selected feature and regression tests, and a containerized evaluation environment.

Start with the [review guide](docs/README.md) to verify the released results without model API calls or Docker. The [research results guide](rq/README.md) maps each research question to its current inputs and outputs. The guides distinguish release inputs from historical evidence.

## Current benchmark

| Item | FSE review version |
| --- | ---: |
| Active tasks | 117 |
| Repositories | 11 |
| Feature tests (F2P) | 623 |
| Regression tests (P2P) | 994 |
| Agent–LLM settings | 15 (3 agents × 5 models) |
| Task–setting outcomes | 1,755 |
| Strong / medium quantum specificity | 49 / 68 |
| Small / medium / large patch-size groups | 39 / 39 / 39 |

The [sample index](benchmark/dataset/samples/index.json) defines the active cohort. Stable IDs span 1–119 with IDs 117 and 119 excluded after evaluation for specification-quality and scope reasons. The [exclusion decisions](rq/rq1/results/cohort_revision_20261002/exclusions.json), raw evaluation records, and [119-task comparison guide](rq/rq1/results/cohort_revision_20261002/README.md) remain available; excluded sample build contexts have been removed. Historical 106-task and 119-task results must not be used as current denominators.

| Repository | Tasks |
| --- | ---: |
| Qiskit Nature | 49 |
| Qiskit Machine Learning | 24 |
| OpenFermion | 12 |
| Qiskit Optimization | 10 |
| PennyLane | 7 |
| OpenQAOA | 3 |
| sQUlearn | 3 |
| Tequila | 3 |
| Qiskit Finance | 2 |
| Tangelo | 2 |
| qiskit-addon-sqd | 2 |

## Results to inspect

The agents are Mini-SWE-Agent, OpenHands, and AutoCodeRover. The five model identities in the recorded experiments are GPT-5.5, GLM-5.2, Gemini-3-Flash, DeepSeek-v4-Pro, and DeepSeek-v4-Flash. Provider and run provenance are retained separately from model names.

- **RQ1 — Overall capability:** the strongest setting, Mini-SWE-Agent with GPT-5.5, resolves 69/117 tasks (59.0%). See the [current performance table](rq/rq1/results/current/rq1_step_cap_main_table.csv) and [merged evaluation records](rq/rq1/results/current/evaluations/).
- **RQ2 — Difficulty:** stronger quantum specificity is associated with lower resolution after controlling for patch size, test count, and configuration (odds ratio 0.338, 95% CI 0.178–0.641). The current model does not include repository fixed effects; see [coefficients](rq/rq2/results/current/regression_coefficients.csv) and [audit](rq/rq1/results/current/audit.json).
- **RQ3 — Test constraints:** tasks with quantum-semantic feature tests have 27.0% pooled resolution, compared with 52.1% for tasks without them. These are task–setting rates, not independent task counts. See [constraint summaries](rq/rq3/results/summary/) and [annotation protocol](rq/rq3/README.md).
- **RQ4 — Failure causes:** the 38 tasks unresolved by all settings contain 280 tests with observed failures, yielding 1,907 testcase–setting failure observations. See the [failure audit](rq/rq4/README.md). Unexecuted and uncollected tests do not become inferred failures.

Three evaluator repetitions check a submitted patch's stability; they do not create three independent agent generations or expand the statistical sample. The evaluator CLI defaults to one execution, so use `--stable-runs 3` for the paper's stability protocol. Original corrections, interrupted workflows, and author-confirmed repeat metadata retain their provenance. Four active OpenHands–Gemini records use explicitly marked token estimates; these are not exact measurements or billing totals.

Supplementary experiment evidence is kept with each agent's results:
[AutoCodeRover](benchmark/evaluation/autocoderover/results/supplementary/README.md),
[Mini-SWE-Agent](benchmark/evaluation/minisweagent/results/supplementary/README.md), and
[OpenHands](benchmark/evaluation/openhands/results/supplementary/README.md).
These archives preserve historical predictions, partial evaluations, recovery records,
and shared audits; final outcome tables use the canonical evaluator files.

## Quick verification

From a clean checkout, Python 3.10 or newer is sufficient for the following checks; no API key, external framework checkout, or Docker service is needed:

```bash
python3 rq/rq1/scripts/verify_revision.py
python3 rq/rq3/scripts/audit_casewise_replays.py
python3 rq/rq4/scripts/summarize_rq4_dominant_testcases.py
```

Expected results include `status: passed`, 117 tasks, 15 settings, 1,755 outcomes, 623 F2P and 994 P2P selectors, and 1,907 audited failure observations. The commands refresh their verification/summary files. See the [review guide](docs/README.md) for complete result regeneration and validation boundaries.

## Repository layout

```text
benchmark/
  dataset/
    samples/              # 117 active sample specifications and build contexts
    repo_selection/       # repository and Issue–PR screening evidence
    audits/               # construction and cross-benchmark statistics
    scripts/              # build, export, and maintenance utilities
  evaluation/
    common/               # shared task, output, usage, and status contracts
    minisweagent/          # Mini-SWE-Agent adapter, configs, recorded results
    openhands/             # OpenHands adapter, configs, recorded results
    autocoderover/         # AutoCodeRover adapter, configs, recorded results
    scripts/              # shared patch evaluator and test runner
    tests/                # adapter/evaluator regression checks
rq/
  rq1/                    # current performance, merged outcomes, cohort checks
  rq2/                    # current difficulty/regression results and inputs
  rq3/                    # CURRENT constraint annotations, replays, summaries
  rq4/                    # CURRENT failure observations and diagnostic evidence
  refresh_extended_paper.py # regenerates current RQ1 and RQ2 outputs
docs/                    # combined review/setup README and verification records
```

The manuscript (`paper/`), external framework checkouts, virtual environments, full local run directories, and temporary exports are excluded from Git. Released structured outcomes and selected diagnostic logs support offline inspection; local provenance paths in archived logs are not download links.

## Run new experiments

Full experiments require Docker, framework dependencies, network access during setup, and credentials for the selected model provider. Start with one task. Historical provider availability and prices are not guarantees for a new run.

1. Prepare framework sources and environments using [setup instructions](docs/README.md).
2. Build sample/evaluation images with the [image workflow](benchmark/dataset/README.md). Respect each sample's recorded Docker platform; the two SQD additions were validated on `linux/arm64`.
3. Export the current index and follow the adapter guide: [Mini-SWE-Agent](benchmark/evaluation/minisweagent/README.md), [OpenHands](benchmark/evaluation/openhands/README.md), or [AutoCodeRover](benchmark/evaluation/autocoderover/README.md).
4. Evaluate new predictions in a separate output directory with `--stable-runs 3`; consult [testcase outcome semantics](benchmark/evaluation/README.md).

The shared prompt presents `problem_statement`, `requirements`, and `interface`. Reference patches and evaluation-only metadata are not task input. Sample construction and selector validation rules are documented in the [construction workflow](benchmark/dataset/README.md).

After installing the framework environments, run adapter/evaluator checks with:

```bash
python3 benchmark/evaluation/scripts/run_tests.py
```

This runs both the core and OpenHands suites. It does not execute the benchmark's model experiments.

## Provenance and reuse

Upstream repositories, frameworks, and comparison datasets retain their own licenses and attribution. This repository does not override those terms. Historical screening decisions and assisted annotation provenance are retained; an automated evidence review must not be interpreted as independent human annotator votes. See the relevant protocols and audit records for scope and limitations.
