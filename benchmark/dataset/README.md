# Dataset construction and evaluation images

## Benchmark Workflow

This document defines the construction workflow for repo-level code-generation
benchmark samples. The goal is to build reusable, executable, and comparable
samples from real feature or behavior requests in open-source repositories, so
models can be evaluated on understanding requirements, locating code,
completing interfaces, implementing functionality, and passing validation tests
inside full repositories.

Each sample lives under:

```text
benchmark/dataset/samples/<repo>/<sample_id>/
```

Each sample must contain at least:

- `sample.json`
- `Dockerfile.repo-base`
- `Dockerfile`
- `run.sh`

`run.sh` is both the sample validation entry point and the shared execution
entry point reused by agents and evaluators. When creating or migrating a
sample, `run.sh` must support the evaluator-injected `MODEL_PATCH_FILE` and
`PREP_ONLY` protocol. If a non-empty `MODEL_PATCH_FILE` is provided, the script
must attempt `git apply` after checkout and cleanup, and explicitly print
`Patch applied: true` or `Patch applied: false (...)`. If `PREP_ONLY=1`, the
script should exit immediately after checkout, patch application, and any
required base-tree test-file preparation, without running pytest. Otherwise,
the evaluator cannot reliably record whether the model patch was applied.

`<repo>` uses the hyphenated short repository name, such as
`qiskit-machine-learning`, `qiskit-nature`, or `qiskit-optimization`. Tool
scripts discover samples recursively from `benchmark/dataset/samples/`, while
commands may still receive the samples root directory.

### Core Principles

- Select samples from `benchmark/dataset/repo_selection/issue_pr_screening_20260930/review_candidates.csv` in order,
  using rows marked `keep=yes`.
- A sample must come from a clear feature or behavior request, and the PR must
  directly resolve that request.
- The current benchmark dataset keeps only Python samples. If a candidate's
  main validation path relies only on `testscpp/`, C++ executable tests, or
  another non-Python primary test entry point, skip it and record the reason in
  the CSV.
- Test scope should be centered on the target feature. Do not run full-repo
  tests or cross-directory integration tests by default.
- Each sample must receive an independent blind `quantum_depth` annotation
  before inspecting any agent or model evaluation results. `quantum_depth`
  measures the quantum specificity of the task itself and must not be inferred
  from whether models solve it.
- Sample construction must explicitly determine and record the file-level
  `golden_patch` scope. This scope should satisfy: modifying only these files
  would, in principle, be sufficient to pass all fail-pass and pass-pass tests.
  Do not treat the entire PR diff as one-shot or retrieval context.
- Prefer `linux/amd64` as the fixed platform to avoid Apple Silicon local
  environment effects on image architecture.
- Install dependencies during Docker build. During Docker run, only switch
  commits and execute tests.
- Base dependency installation on the sample commit's project metadata, CI,
  test dependency files, and optional dependency declarations.
- Maintain `sample.json` manually. Generate
  `benchmark/dataset/samples/index.json` with the update script.

### Construction Workflow

#### 1. Review The Sample

Read `sample_id`, repository, issue, PR, and candidate test paths from the CSV.
Candidate test paths are only hints; the final test scope must be confirmed
from the PR diff and patched version.

During review, confirm that:

- The issue is a clear feature or behavior request.
- The issue itself is quantum-related, such as quantum algorithms, quantum
  optimization, quantum machine learning, quantum chemistry, quantum
  information modeling, quantum operators, circuits, states, measurement, or a
  primitive/backend/sampler/estimator execution path. If it is only ordinary
  engineering, a generic parameter addition, parameter-order adjustment,
  renaming, documentation/API convenience, or non-quantum wrapper cleanup, do
  not proceed even if the PR has tests.
- The PR directly resolves the issue.
- The PR's added or modified tests actually cover the target feature.
- The PR's code and test changes can form a stable fail-to-pass sample.
- The sample's main validation entry point is Python tests. If the candidate
  only provides C++ or `testscpp` coverage and has no suitable Python fail-pass
  path, skip the sample.

#### 2. Annotate Quantum-Domain Reasoning Depth

Quantum-domain reasoning depth is a property of the sample, not a property of
model performance. When constructing or backfilling a sample, complete the
blind annotation before inspecting agent run results, resolved rates, model
patches, failure logs, or any difficulty statistics. `quantum_depth` measures
how much quantum-domain reasoning is needed to complete and judge the task; it
does not measure whether the task merely appears in a quantum-software
repository.

Use the following fixed `quantum_depth` labels. Prioritize the requirement
itself, validation behavior, and interface semantics. Examples are anchor cases,
not keyword lists. Since all admitted feature or behavior requests must already
be quantum-related, `medium` indicates non-core quantum semantics or
quantum-adjacent work, while `strong` indicates core quantum semantics.

- `strong`: Correctness depends on concrete quantum, physical, or
  quantum-chemistry semantics, typically requiring preservation of a domain
  equivalence relation, algebraic invariant, mapping rule, or physical
  convention. Typical signals include fermion-to-qubit mappers, Majorana
  conventions, and electronic-structure Hamiltonians.
- `medium`: The task satisfies the quantum-related admission criterion, but
  correctness does not depend on a new core quantum mapping, physical
  convention, or quantum-algorithm semantics. The core implementation is often
  API work, containers, data structures, symbolic-algebra compatibility,
  framework adaptation, local plumbing, ordinary engineering, or classical
  modeling. Typical signals include symbolic coefficients through transforms,
  wrapping a QNode as a neural-network layer, and classical optimization-model
  translators.

Allowed evidence during annotation:

- Issue and PR user requirements and discussion.
- PR changed files and implementation scope.
- `task.problem_statement`, `task.requirements`, and `task.interface`.
- `golden_patch.oracle_files`.
- Behavioral semantics locked by fail-pass selectors.

When a sample enters the dataset, record `metadata` in `sample.json`:

```json
"metadata": {
  "quantum_depth": "strong|medium",
  "quantum_depth_rationale": "One concise sentence explaining the label."
}
```

`metadata.quantum_depth_rationale` should be one concise sentence explaining
why the requirement itself has that depth.

#### 3. Determine Test Scope

The test scope must lock both the target capability and nearby existing
behavior. `fail_pass` proves that the PR target behavior fails on base and
passes on patched. `pass_pass` proves that nearby existing behavior around the
same change area is not broken. Both groups prioritize stability,
reproducibility, and validation value. Use exact pytest selectors by default,
and always narrow to case-level nodeids. Each selector in `file_list` must
correspond to an actual pytest item or test case. Do not use plain file-path
selectors, class nodeids, or fuzzy `-k` selection. While selecting tests, also
record the user-visible behavior and entry points locked by those selectors for
later `task.requirements` and `task.interface` writing.

Keep `fail_pass` minimally sufficient:

- Select only from tests added or modified by the PR.
- Each selected selector must directly cover the issue/PR target behavior,
  rather than broadening to whole-repository regression or remote integration
  scenarios.
- Patched must pass three consecutive runs; base must fail three consecutive
  runs; and the base failure reason must stably reflect a target-feature defect.
  Prefer cases that directly lock the target capability gap. If the first
  observed failure exposes compatibility, data-structure, or interface absence
  on the same functional path as the requirement, it may also be included.
- This is a per-selector hard constraint, not a coarse whole-command
  constraint. Every selector written to `validation.*.fail_pass.file_list` or
  `FAIL_PASS_TEST_PATHS` must individually satisfy patched 3/3 passed and base
  3/3 failed. Do not mix selectors that pass on base into fail-pass and rely on
  other selectors in the same command to make the overall exit code fail.
- If the official `base fail-pass` summary contains a mix of `passed` and
  `failed` / `error`, immediately return to selector-level review and remove
  selectors that pass on base.
- Use function nodeids, test-method nodeids, or parameterized case nodeids.
  Even if multiple cases share the same validation entry point, enumerate each
  case-level nodeid. Do not use plain file-path selectors or class nodeids. If a
  PR adds or modifies an entire test file, still enumerate the case-level
  nodeids that actually validate the target behavior.
- Do not subjectively remove target behavior because of test count, run cost, or
  implementation difficulty. Cost is handled uniformly by the 120-second
  validation threshold.

Expand `pass_pass` around existing behavior near fail-pass:

- By default, select existing cases from the fail-pass directory or nearby test
  directories that natively exist on both base and patched.
- Prioritize relevance in this order: same module, same class, same fixture,
  same public API, same data structure, same algorithm path, or same optional
  dependency/export entry point.
- When relevance, stability, and cost are acceptable, include all testcase-level
  selectors related to the target behavior instead of selecting only a few smoke
  tests. If all relevant cases in a neighboring test class cover the same old
  behavior surface and run cheaply, keep the relevant cases in that class.
- Do not add unrelated cases only to increase count. Cross-directory
  integration tests or full-repo tests should be included only when necessary
  and explainable.
- Each selected case must pass three consecutive real executions on both base
  and patched. Skipped, xfailed, xpassed, deselected, or not-run cases do not
  count as valid pass-pass.
- Exclude or narrow a candidate to smaller case-level selectors only when it is
  unrelated, unstable, irreproducible, hard to fix environmentally, dependent on
  external services, platform-sensitive, too expensive, or makes a single
  pass-pass validation command approach or exceed the cost threshold. Record the
  tradeoff in notes.
- If the same directory has no suitable case, use `[]`. Do not configure
  base-only pass-pass selectors; base and patched use the same pass-pass
  selector set.

Write selectors as case-level nodeids, for example
`test/foo/test_bar.py::test_function`,
`test/foo/test_bar.py::TestClass::test_case`, or
`test/foo/test_bar.py::TestClass::test_case[param]`. Do not write plain file
paths or class nodeids into samples. `validation.*.*.file_list` in
`sample.json` and Docker `FAIL_PASS_TEST_PATHS` / `PASS_PASS_TEST_PATHS` both
store selector lists. When a selector contains `::`, pytest runs the full
selector; when checking out patched test files, use only the file path before
`::`.

If candidate tests fail on patched, debug the environment first instead of
excluding them immediately. Check missing dependencies, dependency versions,
pytest configuration, platform differences, external services, and PR-era CI
floating dependencies such as `git+https://...`, `main`, or `master`. When
needed, pin upstream dependencies to the latest commit visible at the PR head
time. Exclude and record the reason only after confirming that the historical
environment still cannot pass stably, or that a dependency/service cannot be
reasonably reproduced.

Before writing fail-pass or pass-pass selectors into a sample, run three
stability trials. Only selectors whose three results fully match expectations
may be admitted. To save time, the three trials for the same side and same test
set may be launched in parallel, but the three processes must be independent
and each result must be recorded separately. If parallel execution reveals
resource-contention instability, switch to serial review before deciding. The
final validation stage still records one official summary and duration for each
of the four validation commands; the three trials are used for scope screening,
and trial results and exclusion reasons go into notes.

`summary` should record only pytest item results and duration aligned with the
number of `file_list` entries, such as `10 passed in 11.49s`,
`2 failed in 3.12s`, or the core reason for a collection/import error. Do not
copy warnings, subtests, or pytest-plugin auxiliary statistics into the summary.
If a pytest item internally contains `unittest.subTest`, subtest failure means
that selector does not satisfy a pass result. Summarize it at selector level, for
example `2 selected selectors failed via 12 subtest failures in 5.33s`, rather
than copying plugin output such as `12 failed, 2 passed`, which would be
misleading. In ordinary non-plugin cases, `base fail-pass` summaries should not
include passed items.

Test cost determines whether a sample is executable; it must not be used to
arbitrarily weaken the validation target. The official validation commands for
`patched fail-pass`, `base fail-pass`, `patched pass-pass`, and
`base pass-pass` should each stay below the validation-stage threshold. During
pass-pass selection, narrow by relevance and cost from low to high: keep stable
same-module, same-class, or same-API cases, and exclude the most expensive,
least relevant, externally dependent, or environment-sensitive cases. Exclude
the sample only when compliant narrowing cannot resolve the issue.

#### 4. Determine Golden Patch Scope

In addition to test scope, determine the sample's `golden_patch` scope
separately. Here, `golden_patch` means the set of gold patch files that may be
used as oracle implementation context in one-shot or retrieval evaluation. It
is not "all files in the PR diff"; it is the file-level scope for which
modifying only those files would, in principle, be sufficient to pass all
fail-pass and pass-pass tests.

`golden_patch.oracle_files` records repository-relative file paths. By default,
derive it from files in the `base_commit..patch` diff that satisfy the rule
above. Therefore it must be a subset of PR-modified files. Use these rules:

- Keep source files that directly implement the target capability, expose the
  target capability, maintain related data structures, provide compatibility
  plumbing, or implement internal interfaces on the same functional path. If
  omitting a file would make the sample hard to solve under reasonable
  assumptions, include it.
- Exclude test files by default, including `test/`, `tests/`, `*_test.py`, and
  `test_*.py`.
- Exclude pure documentation and tutorial files by default, including `docs/`,
  `releasenotes/`, notebooks, markdown, rst, images, and other non-source
  assets.
- Exclude CI and repository metadata by default, such as workflows, issue
  templates, or action configs under `.github/`, unless the file itself is part
  of the requested implementation. Benchmark samples generally should not rely
  on these files to complete the core task.
- Include `__init__.py`, registries, factories, configuration mappings, schema,
  templates, or other non-test helper code whenever they are necessary
  implementation pieces for exposing or enabling the target capability.
- If a PR modifies implementation files and documentation/test files,
  `golden_patch` records only implementation-scope files, not tests or docs.
- If a file's inclusion in `golden_patch` is disputed, ask whether modifying
  only the current file list would still in principle be sufficient to pass the
  sample's fail-pass and pass-pass tests. Record the judgment in notes.

`golden_patch` has a different purpose from test scope:

- It supports one-shot oracle, retrieval, context pruning, and later data
  analysis.
- It is not directly exposed to task-based agent evaluation prompts.
- It does not replace `task.requirements`, `task.interface`, or
  `validation.*.*.file_list`.

#### 5. Determine Environment And Images

Default environment:

- Docker platform: `linux/amd64`
- Base image: Prefer a Debian/glibc family consistent with existing samples,
  explicitly pinned to a stable OS tag such as `python:<version>-slim-trixie`,
  or an equivalent base image already used by the repository family. Do not
  rely only on drifting tags such as `python:<version>-slim`, unless the
  maintained sample family explicitly still uses that floating tag as its
  consistency baseline.
- Python version: Prefer the sample commit's CI and project metadata; use
  `3.10` when there is no special constraint.

When choosing the base image, first inspect `Dockerfile.repo-base` for nearby
repositories or the same technology stack in the current dataset. New samples
should keep OS, glibc version, CPU architecture, and system package sources as
consistent as possible with existing images. If a deviation is required, explain
it in `runtime.environment` and CSV notes. After build, verify OS/glibc with
`/etc/os-release` and `ldd --version`, and record key versions in
`sample.json` to avoid future Docker tag drift.

Dependency installation commands must be based on the sample commit's project
configuration, not the current main branch. Check these first:

- `.github/workflows/*.yml`
- `.github/actions/*/action.yml`
- `pyproject.toml`
- `setup.py`
- `setup.cfg`
- `requirements*.txt`
- `constraints.txt`
- `tox.ini`
- `noxfile.py`

If the sample commit uses floating dependencies or upstream source dependencies
such as unpinned `git+https://...`, `main`, `master`, nightly, or dev channels,
convert them to reproducible fixed points for benchmark construction. By
default, use the PR head commit time as an anchor and pin to the latest mainline
commit in the upstream dependency repository before that time. If that
historical commit cannot install because of modern build-tool drift, first try
to restore period-appropriate build constraints such as older Cython,
setuptools, pip, or disabled build isolation, rather than using a non-equivalent
release dependency. Record this judgment and pinning in
`runtime.environment.extra_test_dependencies` or CSV notes.

Compare dependency entry files between base and patched commits. If dependency
entry files are unchanged and one image can run both base and patched, set
`shared_between_base_and_patched = true`. If dependency entries changed, or
validation shows one environment cannot support both sides, split environments
or record extra constraints.

Ordinary samples use two image layers:

- `benchmark-base:<sample_id>`: installs system dependencies, clones the
  repository, and installs Python dependencies and the editable package.
- `benchmark-<sample_id>:latest`: derives from repo-base, sets sample metadata
  and test paths, and copies `sample.json` and `run.sh`.

`Dockerfile.repo-base` uses the patched commit as the dependency-installation
baseline; `run.sh` checks out the base commit when running base. To save disk
space, the repo-base layer may use partial clone, for example
`git clone --filter=blob:none`, but it should be treated only as the dependency
environment base, not as the complete offline evaluation entry point. Batch
evaluators run with `--network none` by default and disallow lazy fetches, so
the official evaluator image `benchmark-evaluation:<sample_id>` must hydrate
the Git objects needed for both base and patched checkouts during build or
hydration. The agent-base image hydrates only objects required for the base
checkout and then rebuilds a single-commit shallow repository.

If a sample's thin `Dockerfile` installs required test dependencies beyond its
repo-base image, set `runtime.docker.evaluation_source_image` to that sample
image before evaluator hydration. This preserves those dependencies in the
offline evaluator image without changing other samples' environments. Verify
required imports inside the final evaluator image; a skipped required selector
does not count as a passing test.

Historical PennyLane releases register even `default.qubit` through setuptools
entry points. Their legacy editable install keeps those entry points in
`PennyLane.egg-info` under the checkout, which `git clean -fdx` removes during
evaluator hydration or agent-base construction. For a sample where this is
verified, set `runtime.environment.repair_plugin_entry_points_after_clean` to
`true`. The two image builders then install a local wheel without dependencies
or network access **after** their final checkout cleanup, keep
`PYTHONPATH=/workspace/repo` so tests and agents import the mutable checkout,
and check that `qml.device("default.qubit", wires=1)` still works after another
cleanup. In the agent image, this step must run from the base-only checkout to
preserve the anti-leak boundary. Leave the flag absent for other samples.

The recorded audit covers seven PennyLane evaluation images:

| Sample IDs | Observation | Benchmark impact |
| --- | --- | --- |
| 13, 19 | `git clean -fdx` removes the editable install's entry-point metadata; `default.qubit` is undiscoverable. | Selected tests produced infrastructure errors. Rebuilt evaluation and agent images with the scoped repair and reevaluated all recorded agent patches. |
| 14, 15 | A standalone `default.qubit` smoke call requires the optional `pennylane-lightning` package, which is absent. | The selected patched F2P and P2P tests all pass in the existing images (8/8 and 9/9, respectively). No image change was made. |
| 16, 17, 18 | The standalone `default.qubit` smoke call succeeds. | No repair needed. |

The optional dependency observation for IDs 14 and 15 is separate from the
missing entry-point defect in IDs 13 and 19. Revisit it only if future selected
tests or agent evaluations exercise that device path.

Keep BuildKit enabled during build and use a pip cache mount:

```dockerfile
RUN --mount=type=cache,id=quanbench-pip,target=/root/.cache/pip \
    ...
```

Build commands:

```bash
docker build --platform linux/amd64 \
  -f benchmark/dataset/samples/<repo>/<sample_id>/Dockerfile.repo-base \
  -t benchmark-base:<sample_id> \
  benchmark/dataset/samples/<repo>/<sample_id>

docker build --platform linux/amd64 \
  -f benchmark/dataset/samples/<repo>/<sample_id>/Dockerfile \
  -t benchmark-<sample_id>:latest \
  benchmark/dataset/samples/<repo>/<sample_id>
```

When multiple samples come from the same repository and have identical Python
versions, system packages, and dependency constraints, reuse the repo-base
design and Docker layers. Each sample still keeps its own sample directory and
final image. The final sample image contains the full repo-base environment and
source, but Docker storage reuses lower layers instead of duplicating the full
dependency environment for every thin sample image.

Recommended `run.sh` patch-apply snippet:

```bash
if [ -n "${MODEL_PATCH_FILE:-}" ]; then
  if [ -s "${MODEL_PATCH_FILE}" ]; then
    if git apply --whitespace=nowarn "${MODEL_PATCH_FILE}" \
      || git apply --ignore-whitespace --whitespace=nowarn "${MODEL_PATCH_FILE}"; then
      echo "Patch applied: true"
    else
      echo "Patch applied: false (git apply failed)." >&2
      exit 21
    fi
  else
    echo "Patch applied: false (empty model patch)." >&2
    exit 20
  fi
fi

if [ "${PREP_ONLY:-0}" = "1" ]; then
  exit 0
fi
```

Samples should stay compatible with this protocol whenever possible.

#### 6. Fill `sample.json`

`sample.json` is the detailed source of truth for a sample. Main fields:

- `instance`: sample identity, source links, and version anchors.
- `metadata`: benchmark-analysis metadata, such as blind `quantum_depth` and
  its rationale.
- `golden_patch`: file-level implementation scope for the gold patch.
- `task`: task description given to the model.
- `runtime.docker`: image identity and build status.
- `runtime.environment`: platform, Python version, environment sharing policy,
  and extra test dependencies.
- `validation`: base and patched fail-pass and pass-pass test results.

Fixed enums:

- `instance.status`: `pending`, `completed`
- `validation.classification`: `fail_to_pass`, `pass_to_pass`, `error`
- `validation.*.*.result`: `passed`, `failed`, `not_applicable`
- `metadata.quantum_depth`: `strong`, `medium`

Test selector lists are stored in `validation.*.*.file_list`; there is no
separate test-planning block. The historical field name remains `file_list`,
but new and migrated samples should interpret it as a list of case-level pytest
selectors. Each entry corresponds to an actual pytest item or test case, such
as `path/to/test.py::test_case`,
`path/to/test.py::TestClass::test_case`, or a parameterized nodeid.
`FAIL_PASS_TEST_PATHS` and `PASS_PASS_TEST_PATHS` in Dockerfile/run.sh likewise
store space-separated pytest selectors.

##### `metadata` Field

`metadata.quantum_depth` records the sample's quantum-specificity strength and
must be blind-annotated according to the annotation section before evaluation
results are visible. `metadata.quantum_depth_rationale` is one short sentence
explaining why the sample is `strong` or `medium`. These fields support
benchmark data analysis only; they do not enter the agent prompt, are not used
for validation logic, and should not be modified based on model resolved
results.

##### `golden_patch` Field

`golden_patch.oracle_files` records the file-level oracle implementation scope
using repository-relative paths maintained by hand. Its definition is: modifying
only this list of files would, in principle, be sufficient to make all fail-pass
and pass-pass tests pass. The list must be a subset of PR-modified files. By
default it excludes tests, tutorials, release notes, CI configuration, and other
non-source assets. Include a non-test file modified by the PR only when it is a
necessary implementation boundary for passing the sample. Later one-shot
oracle, BM25, context-length analysis, and retrieval experiments should prefer
this list instead of treating the entire PR diff as gold context again.

##### `task` Field

The core external task description given to models consists of
`task.problem_statement`, `task.requirements`, and `task.interface`. Do not
expose test source. Put behavior locked by tests into `requirements`, and put
symbols locked by tests into `interface`.

`problem_statement` should be a cleaned issue description explaining existing
capability, the current gap, user pain, and the target outcome. It may name the
target capability, but should not expand into an acceptance checklist or include
file paths, function signatures, test details, or implementation steps.

`requirements` should be a flat list of observable behavior. It covers key
behavior expected by tests and the gold patch, such as public availability,
compatibility, error behavior, and input/output semantics. It should not include
file paths, full signatures, private methods, concrete patch hints, test
framework perspective, or benchmark-internal perspective.

`interface` is a structured list. It is an acceptance-entry specification, not a
complete API document. It records stable entries that the model must expose for
the feature to be reachable by user calls or fail-pass validation. Its purpose
is to reduce false positives: a model may implement similar behavior but fail
because entry names, constructor parameters, return types, calling patterns, or
public API shape do not match validation expectations. `interface` should not
fully reproduce every Python call touched by fail-pass tests, nor provide an
implementation path. After migrating to case-level fail-pass, `interface` must
be narrowed to selected cases; if a previously broad test scope covered an
entry that the new case-level fail-pass no longer covers, do not retain it
mechanically. Each entry contains:

- `Type`
- `Name`
- `Path`
- `Input`
- `Output`
- `Description`

Field rules:

- `Type` may only be `Function`, `Class`, or `Method`.
- `Name` is the exact symbol name; `Path` is the repository-relative path.
- Use an empty string for missing `Input` or `Output`.
- `Description` contains only the interface contract, not motivation, broad
  behavior, or implementation steps.
- Python constructor parameters go in the `Input` of the `Class` entry with a
  `constructor:` prefix.
- Constructor parameters should normally include only parameter names and
  necessary types. Include default values only when they affect tests,
  compatibility, or user-visible behavior.
- Do not list `Class.__init__` separately.
- Any stable entry directly called, monkeypatched, or exception-asserted by
  fail-pass must be written into `interface`. Such entries may include public
  APIs, private methods, internal helpers, framework hooks, or Python protocol
  methods; if fail-pass locks the entry as a validation entry point, list it.
- Judge remaining entries by task relevance. For a new core class, it may be
  appropriate to list its constructor, public methods, class methods, and
  factory methods to lock the acceptance API and reduce false positives. Do not
  mechanically list methods that are not fail-pass-locked and not core task
  APIs. Protocol capabilities such as `__len__`, `__iter__`, `__eq__`,
  `__matmul__`, `__xor__`, and `__pow__` can be described in the relevant class
  or method `Description`, for example "supports iteration" or "supports tensor
  and composition operators", if they are not listed separately.
- Ordinary package export files such as `__init__.py` are not separate
  interface entries by default.

#### 7. Run Validation And Update The Index

After official evaluator image hydration completes, run four validation
commands for each sample:

```bash
docker run --platform linux/amd64 --rm --network none -e GIT_NO_LAZY_FETCH=1 benchmark-evaluation:<sample_id> patched fail-pass
docker run --platform linux/amd64 --rm --network none -e GIT_NO_LAZY_FETCH=1 benchmark-evaluation:<sample_id> patched pass-pass
docker run --platform linux/amd64 --rm --network none -e GIT_NO_LAZY_FETCH=1 benchmark-evaluation:<sample_id> base fail-pass
docker run --platform linux/amd64 --rm --network none -e GIT_NO_LAZY_FETCH=1 benchmark-evaluation:<sample_id> base pass-pass
```

Expected results:

- `patched fail-pass` passes.
- `patched pass-pass` passes, or pass-pass is empty.
- For a `fail_to_pass` sample, `base fail-pass` fails and the failure reason
  stably reflects a target-feature defect. If it is not the most direct
  capability gap, it must still be explainable as part of the same functional
  path as the target requirement.
- For a `fail_to_pass` sample, every selected selector in `base fail-pass` must
  fail. Do not allow a situation where the whole command fails but some
  fail-pass selectors pass on base. If this happens, remove selectors that pass
  on base, narrow task/interface/golden_patch scope, and rerun stability and
  official validation.
- `base pass-pass` passes, or pass-pass is empty.

`base fail-pass` may cover patched test files to prove that old code does not
satisfy the new requirement. `base pass-pass` does not cover patched test files;
it runs only the same pass-pass tests that natively exist on base.

During validation, record wall time for each command in the corresponding
`validation.*.*.duration_seconds`. Each validation command has an independent
cost limit:

`patched fail-pass`, `base fail-pass`, `patched pass-pass`, and
`base pass-pass` should each stay under 120 seconds. If any command exceeds the
threshold, mark the sample as too costly and exclude it from the current
benchmark dataset unless the user explicitly decides to keep it. If pass-pass
tests time out, are clearly too long, or the candidate set is expected to take
minutes, narrow by relevance and cost from low to high: keep stable cases from
the same module/class/API, exclude the most expensive, least relevant, external
resource-dependent, or environment-sensitive cases, and exclude the sample only
when compliant narrowing cannot resolve the issue. Do not stop expanding just
because the pass-pass count is "already small"; stop when tests are stable,
nearby, relevant, and acceptable in per-sample cost.

After validation, backfill:

- `instance.status`
- `runtime.docker.build_success`
- `runtime.docker.image`
- `runtime.docker.image_id`
- `runtime.docker.image_size`
- `runtime.environment`
- `validation.*`

`image_id` comes from the final sample image, not the repo-base image. Local
`sample.json` is the authority for `image_id`; do not rebuild only to write the
new `image_id` back into `/benchmark/sample.json` inside the image.

Update the index after adding or modifying samples:

```bash
python benchmark/dataset/scripts/update_sample_index.py
```

`index.json` keeps the stable numeric `id` (1–119, excluding retired IDs 117 and 119), `sample_id`,
`sample_path`, and Docker metadata. The same `id` is stored in each
`sample.json` under `instance.id` and is used in task-level analysis figures. The active release contains 117 tasks; do not renumber retained IDs.

### Docker Cleanup

Check local Docker state:

```bash
docker images
docker system df
```

A standardized sample set usually has three image types:
`benchmark-base:<sample_id>`, `benchmark-<sample_id>:latest`, and
`benchmark-evaluation:<sample_id>`. `benchmark-<sample_id>:latest` is the thin
sample/source image, while `benchmark-evaluation:<sample_id>` is the official
offline entry point for batch evaluation.

If disk space is low or failed builds produced intermediate layers, first clean
unused BuildKit cache and dangling images:

```bash
docker builder prune -f
docker image prune -f
```

Delete only tagged images that are clearly obsolete or not part of the current
sample set. Keep `benchmark-base:<sample_id>` for current samples; otherwise,
the next thin sample image build loses the cache benefit.

### Agent Evaluation Isolation

During agent execution, only the base checkout and task specification are
exposed. `instances.secure.jsonl` is the sole official evaluation instance
entry. Its `problem_statement` is generated from `task.problem_statement`,
`task.requirements`, and `task.interface`, and contains no `validation`,
fail-pass paths, pass-pass paths, or patched test content.

Each sample has one evaluation image, one safe agent base, and three
framework-specific agent images:

- `benchmark-evaluation:<sample_id>`: eval image, used only by the evaluator.
- `benchmark-agent-base:<sample_id>`: shared safe agent base containing only the
  base checkout and a leakage-trimmed single-commit shallow repository.
- `benchmark-minisweagent-<sample_id>:latest`: mini-SWE-agent image, inheriting
  `benchmark-agent-base:<sample_id>` and adding the mini-SWE-agent runtime.
- `benchmark-openhands-<sample_id>:latest`: OpenHands image, inheriting
  `benchmark-agent-base:<sample_id>` and adding the OpenHands agent-server
  layer.
- `benchmark-traeagent-<sample_id>:latest`: Trae-agent image, defaulting to an
  independent tag pointing to `benchmark-agent-base:<sample_id>`.

Leakage-prevention logic lives only in `benchmark-agent-base:<sample_id>`.
Runtime components used by all agent containers and independent of a specific
sample's dependencies, such as `swe-rex`, iptables, and common system/Python
tools required by agent containers, should preferably live in framework-specific
or shared runtime layers. Framework-specific images must not reintroduce
fail-pass/pass-pass injection, `sample.json` validation metadata, or
evaluator-only logic.

Agent adapter images derive from the final benchmark image, but must be trimmed
to a base-only runtime environment during build:

- Check out the sample `base_commit`.
- Rebuild a single-commit shallow repository from the base working tree and the
  original base commit object.
- Keep only the local branch pointing to `base_commit` and `.git/shallow`.
- Verify that the `patch` commit object can no longer be read with
  `git cat-file`.
- Delete `/benchmark` to avoid exposing validation, fail-pass, or pass-pass
  information through `/benchmark/sample.json`.

Models may search and run tests that natively exist in the base working tree;
this is normal repository exploration. Models must not see patched-only
fail-pass tests through Git history, reflog, the object database, `sample.json`,
or prompt metadata. Agent generation should use Docker `--network none` and
block common networking, dependency installation, and Git-query paths. Fail-pass
tests are injected only during evaluator execution to validate the submitted
`model_patch`.

### Templates

Template locations:

- `benchmark/dataset/templates/Dockerfile.template`
- `benchmark/dataset/templates/Dockerfile.repo-base.template`
- `benchmark/dataset/templates/Dockerfile.from-repo-base.template`
- `benchmark/dataset/templates/run.sh.template`
- `benchmark/dataset/templates/sample.json.template`

Ordinary samples use `Dockerfile.repo-base.template`,
`Dockerfile.from-repo-base.template`, `run.sh.template`, and
`sample.json.template` by default. The single-file `Dockerfile.template` is only
a fallback for legacy samples or special environments.

Templates provide only a shared skeleton and do not automatically infer the
environment. After copying a template, manually replace sample ID, repository,
issue, PR, commits, test files, system packages, install commands, task fields,
and runtime/validation records.

## Evaluation Image Workflow

This document describes the current QFEA-Bench image hierarchy, build order, and
common commands. Sample-construction rules are still defined by
the construction workflow above.

### Image Hierarchy

Each sample is identified by `sample_id` across the image hierarchy:

```text
benchmark-base:<sample_id>
        |-- benchmark-evaluation:<sample_id>
        `-- benchmark-agent-base:<sample_id>
                |-- benchmark-minisweagent-<sample_id>:latest
                |-- benchmark-openhands-<sample_id>:latest
                `-- benchmark-traeagent-<sample_id>:latest
```

Layer responsibilities:

- `benchmark-base:<sample_id>`: shared sample base layer containing system
  dependencies, Python dependencies, and the source-repository environment.
- `benchmark-evaluation:<sample_id>`: evaluation-only image. It contains
  `/benchmark/sample.json` and `/benchmark/run.sh`, and hydrates the Git
  objects required for both base and patched checkouts.
- `benchmark-agent-base:<sample_id>`: shared safe agent base. It retains only
  the base checkout and removes patch-related information and evaluator
  metadata to avoid answer leakage.
- `benchmark-minisweagent-<sample_id>:latest`: mini-SWE-agent runtime image.
- `benchmark-openhands-<sample_id>:latest`: OpenHands runtime image.
- `benchmark-traeagent-<sample_id>:latest`: Trae-agent runtime image.

Core principles:

- The evaluator may contain objects needed by both base and patched checkouts;
  agent images may only expose the base checkout.
- Agent outputs are decoupled from evaluator images. If only evaluator images
  are rebuilt, existing agent outputs can be reused.
- Agent-specific images can be built locally. Registry tags are an optional cache;
  complete availability for all 117 active tasks is not asserted. Trae-agent is
  a legacy adapter outside the three-agent FSE experiment.

### Build Order

#### 1. Build Base

If `benchmark-base:<sample_id>` is missing locally, build it from the sample
Dockerfile first:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_base_images.py \
  --missing-only
```

#### 2. Build Evaluator

Build `benchmark-evaluation:<sample_id>`:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_evaluation_images.py
```

This derives the evaluator from `benchmark-base:<sample_id>` and hydrates the
base and patched Git objects needed for offline evaluation.

#### 3. Build Agent Base

If the shared safe agent base is missing locally:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_agent_base_images.py
```

This derives `benchmark-agent-base:<sample_id>` from
`benchmark-base:<sample_id>` and applies base-only leakage-prevention trimming.

#### 4. Build The Three Agent Framework Images

mini-SWE-agent:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_minisweagent_images.py \
  --skip-existing
```

OpenHands:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_openhands_images.py \
  --current-only \
  --jobs 1
```

Trae-agent:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_traeagent_images.py \
  --skip-existing
```

### Prepare Agent Images From DockerHub

If the corresponding cached tags are available, pull shared agent-base images
and retag them. Build missing tags locally using the sample build contexts.
The historical registry namespace remains `arthurshy/quanbench`:

```bash
./.venv/bin/python benchmark/dataset/scripts/pull_published_images.py \
  --repo arthurshy/quanbench \
  --kind agent-base \
  --missing-only
```

```bash
./.venv/bin/python benchmark/dataset/scripts/retag_published_images.py \
  --repo arthurshy/quanbench \
  --kind agent-base \
  --missing-only
```

Then build the OpenHands and Trae-agent images locally:

```bash
./.venv/bin/python benchmark/dataset/scripts/build_openhands_images.py \
  --current-only \
  --jobs 1
```

```bash
./.venv/bin/python benchmark/dataset/scripts/build_traeagent_images.py \
  --skip-existing
```

### Check Images

Check whether all three agent images exist and can start:

```bash
./.venv/bin/python benchmark/dataset/scripts/check_agent_images.py \
  --workers 4
```

Only check whether Docker tags exist, without starting containers:

```bash
./.venv/bin/python benchmark/dataset/scripts/check_agent_images.py \
  --inspect-only
```

Check whether evaluators can check out base and patched commits offline:

```bash
./.venv/bin/python benchmark/dataset/scripts/maintenance/check_evaluator_images_offline.py
```

### Evaluation

The evaluation script uses `benchmark-evaluation:<sample_id>` and consumes
agent-generated `preds.jsonl`:

```bash
./.venv/bin/python benchmark/evaluation/scripts/evaluate_agent_preds.py \
  benchmark/evaluation/minisweagent/runs/deepseek_v4_flash_YYYYMMDD/preds.jsonl \
  --output benchmark/evaluation/minisweagent/results/results_deepseek_v4_flash_YYYYMMDD.json \
  --workers 8 \
  --timeout 600
```

If only evaluator images are rebuilt or repaired, existing agent outputs can be
reused; rerun evaluation only.

### Progress Files

Image build and check scripts write runtime state to the following files by
default:

```text
benchmark/dataset/build_logs/image_rebuild_progress.json
benchmark/dataset/build_logs/*.jsonl
```

These are runtime progress records. They do not replace `sample.json` or
`benchmark/dataset/samples/index.json`.

## OpenFermion construction notes

Inspect the requested feature, exact PR patch, tests, dependency declarations, and
recorded sample environment before selecting selectors or an interpreter. Historical
OpenFermion revisions may be incompatible with modern NumPy, SciPy, TensorFlow, or
packaging defaults; use each retained sample's dependency pins and Dockerfiles as
evidence of its validated environment. An optional dependency may be omitted only
when the selected implementation and tests do not require it.

Review tests at selector level. Accept base failures caused by the missing target
feature, including its absence at import, only when they genuinely correspond to
the selected assertion path. Empty P2P is permissible when no relevant regression
selector is available; it must not be filled with unrelated tests. Randomized
parameter IDs can change pytest nodeids, so record and verify the exact selectors.
Keep the reference patch limited to the task implementation and documented files.

Prefer preparing the repository base from the patched revision so dependencies
and test files are available, then restore the base implementation for agent input.
Preserve historical Debian source compatibility adjustments where the Dockerfile
requires them. Some old packages need `setup.py develop` rather than a modern
editable-build backend. Retain the shared `run.sh` protocol and verify every sample
in its own container. Per-sample metadata and saved validation results are the
authority for exact versions, selectors, platforms, and failure expectations.
