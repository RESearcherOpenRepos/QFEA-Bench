# Evaluation providers and testcase evidence

## Model API providers

Provider credentials are supplied through environment variables, never committed in configuration files. Export only the credentials required by the selected configuration before launching a run. Provider checks below describe the recorded experiment dates; they do not guarantee future catalog availability.

| Platform | Environment variable | OpenAI-compatible base URL |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | `https://api.deepseek.com` |
| Alibaba Cloud DashScope | `DASHSCOPE_API_KEY` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| OpenRouter | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |
| BigModel | `BIGMODEL_API_KEY` | `https://open.bigmodel.cn/api/paas/v4` |
| SiliconFlow | `SILICONFLOW_API_KEY` | `https://api.siliconflow.cn/v1` |

### SiliconFlow

The recorded model-catalog check returned `deepseek-ai/DeepSeek-V4-Flash` and `deepseek-ai/DeepSeek-V4-Pro`. Each agent has `siliconflow_deepseek_v4_flash_once` and `siliconflow_deepseek_v4_pro_once` configurations in its `config/` directory (JSON for OpenHands/AutoCodeRover, YAML for Mini-SWE-Agent). They preserve the corresponding DashScope generation settings: temperature 0, thinking disabled, and 16,384 maximum output tokens. OpenHands retains 100 steps and one workflow attempt; evaluation repeats are controlled separately by the evaluator.

The prediction model identities remain `deepseek-v4-flash` / `deepseek-v4-pro`; provider and endpoint provenance must be recorded separately. Existing completed samples are retained when changing provider for unfinished samples. SDK dollar estimates are not verified SiliconFlow billing; retain prompt, completion, and cached-token usage for separate accounting.

[Official API documentation](https://docs.siliconflow.cn/docs/api/chat-completions-post)

OpenHands also provides `config/siliconflow_glm5_2_once.json` for `zai-org/GLM-5.2`. The recorded preflight verified `enable_thinking: false` with zero reported reasoning tokens. This overlay retains the prior GLM-5.2 settings (temperature 0, 16,384 output tokens, 100 steps, one workflow attempt).

## Exact testcase outcomes in benchmark evaluations

New evaluations load `scripts/pytest_case_report.py` as a pytest plugin for each F2P and P2P suite. The plugin records the exact pytest node IDs, setup/call/teardown outcomes, collection errors, and pytest exit code as JSON. The evaluator transports that JSON out of the disposable Docker container and stores it under `pytest_case_reports` in the result JSON. It also writes one `test_cases` entry for every selected F2P/P2P selector.

`test_cases["fail_pass"]` and `test_cases["pass_pass"]` use these statuses:

- `passed`: a call-phase pass was reported for every runtime item matched by the selected selector, with no failed or skipped phase.
- `failed`: pytest reported a failing setup, call, or teardown phase. `phase` identifies the first failing phase.
- `skipped`: pytest reported a skip. This is not counted as a pass.
- `not_collected`: pytest did not execute the selector. `phase="collection"` means its file had a collection error; `phase="startup"` means pytest stopped before producing a case report. Other selectors absent after an abort have no inferred pass/fail outcome.
- `not_run`: no pytest execution reached that selector, including when no agent patch was submitted or a collected item emitted no result.

Each suite's `passed`, `total`, and `status` are calculated from those testcase records. `total` is the number of selected selectors, not the number of pytest subtests or collection-error files. A suite is `passed` only if every selected selector passed and pytest exited successfully. A collection error can make the suite `failed` while its affected testcase entries remain `not_collected`; that accurately describes what was observed. If no P2P selectors are configured, P2P is `not_applicable`. Repeated evaluator runs count a selector as passed only when it passes in every run.

The older `results*.json` files were generated before this reporter existed. Their per-test outcomes cannot be recovered exactly from suite totals or prose logs. Replaying the saved patches in the original sample images is required to produce final per-test paper statistics; this does not call the LLM again. For example:

```bash
python3 benchmark/evaluation/scripts/evaluate_agent_preds.py \
  benchmark/evaluation/minisweagent/runs/gpt55_20260604/preds.json \
  --output rq/rq3/results/casewise_replays/minisweagent_gpt55_20260604.json \
  --workers 1 --timeout 600 --stable-runs 3

python3 rq/rq3/scripts/summarize_structured_constraint_passes.py \
  rq/rq3/results/casewise_replays/minisweagent_gpt55_20260604.json \
  --agent minisweagent --run gpt55_20260604
```

The second command joins the exact testcase statuses to the final constraint labels and verifies every selector and suite count. All 15 settings have stored testcase records for the active 117-task cohort. The example above requires a local saved prediction file, which is not included in this Git release; offline inspection uses the already released replay JSONs. Final three-category results are in `rq/rq3/results/summary/constraint_passes_casewise_by_agent.csv` and `constraint_passes_casewise_by_agent_llm.csv` in the same directory. Final subcategory, instance-resolution, and robustness summaries are also under `rq/rq3/results/summary/`.

Replay quality checks are recorded in `rq/rq3/results/summary/casewise_replay_quality.csv`. Evaluation-resource corrections are retained in `rq/rq1/results/resource_corrections/`, and the historical 106-task corrections are indexed by `rq/rq1/results/corrected_evaluations/manifest.json`. Current 117-task merged results are in `rq/rq1/results/current/evaluations/`. A pytest exit code of zero with only skipped selected tests does not count as F2P/P2P success. Replaying saved patches does not generate new Agent trajectories.
