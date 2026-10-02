from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[4]


def load_module(relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_openhands_enables_deepseek_reasoning_content_passthrough() -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    model_features = runner.openhands_model_features
    original_patterns = list(model_features.SEND_REASONING_CONTENT_MODELS)
    try:
        model_features.SEND_REASONING_CONTENT_MODELS[:] = [
            pattern for pattern in original_patterns if pattern != "deepseek-v4-flash"
        ]
        assert not model_features.get_features(
            "openai/deepseek-v4-flash"
        ).send_reasoning_content

        runner.patch_deepseek_reasoning_content_passthrough(
            "openai/deepseek-v4-flash"
        )

        assert "deepseek-v4-flash" in model_features.SEND_REASONING_CONTENT_MODELS
        assert model_features.get_features(
            "openai/deepseek-v4-flash"
        ).send_reasoning_content
    finally:
        model_features.SEND_REASONING_CONTENT_MODELS[:] = original_patterns


def test_run_openhands_normalizes_raw_output_cost_with_cache() -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    from openhands.sdk.llm.utils.metrics import Cost, Metrics, TokenUsage

    output = runner.EvalOutput(
        instance_id="sample_1",
        test_result={"git_patch": "diff --git a/x.py b/x.py\n"},
        metrics=Metrics(
            accumulated_cost=0.001,
            accumulated_token_usage=TokenUsage(
                model="openrouter/openai/gpt-5.5",
                prompt_tokens=1000,
                completion_tokens=100,
                cache_read_tokens=400,
                cache_write_tokens=0,
            ),
            costs=[Cost(model="openrouter/openai/gpt-5.5", cost=0.001)],
        ),
    )

    normalized = runner.normalize_eval_output_cost(
        output,
        "openrouter/openai/gpt-5.5",
    )

    assert normalized.metrics is not None
    assert round(normalized.metrics.accumulated_cost, 6) == 0.0062
    assert round(sum(cost.cost for cost in normalized.metrics.costs), 6) == 0.0062


def test_run_openhands_sanitized_writer_drops_reasoning_artifacts(tmp_path: Path) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    output_path = tmp_path / "output.jsonl"

    runner.write_sanitized_eval_output(
        str(output_path),
        {
            "instance_id": "sample_1",
            "error": None,
            "metrics": {
                "accumulated_token_usage": {
                    "prompt_tokens": 7,
                    "completion_tokens": 3,
                    "reasoning_tokens": 17,
                },
                "reasoning_content": "hidden chain",
            },
            "history": [
                {
                    "kind": "ActionEvent",
                    "tool_name": "finish",
                    "thinking_blocks": [{"thinking": "hidden chain"}],
                }
            ],
            "reasoning": {"effort": "medium"},
        },
    )

    written = output_path.read_text(encoding="utf-8")
    row = json.loads(written)
    assert row["metrics"]["accumulated_token_usage"]["prompt_tokens"] == 7
    assert row["metrics"]["accumulated_token_usage"]["completion_tokens"] == 3
    assert "reasoning_tokens" not in written
    assert "reasoning_content" not in written
    assert "thinking_blocks" not in written
    assert '"reasoning"' not in written


def test_export_openhands_instances_preserves_task_fields(tmp_path: Path) -> None:
    exporter = load_module(
        "benchmark/evaluation/openhands/scripts/export_openhands_instances.py"
    )
    sample_dir = tmp_path / "samples" / "repo" / "sample_1"
    sample_dir.mkdir(parents=True)
    (sample_dir / "sample.json").write_text(
        json.dumps(
            {
                "instance": {
                    "repo": "owner/repo",
                    "instance_id": "sample_1",
                    "base_commit": "abc",
                    "issue_url": "https://example.test/issue",
                    "pr_url": "https://example.test/pr",
                    "patch": "def",
                },
                "task": {
                    "problem_statement": "Implement a feature.",
                    "requirements": ["Expose Foo.", "Keep Bar unchanged."],
                    "interface": [
                        {
                            "Type": "Class",
                            "Name": "Foo",
                            "Path": "pkg/foo.py",
                            "Input": "constructor",
                            "Output": "",
                            "Description": "Feature entrypoint.",
                        }
                    ],
                },
                "validation": {
                    "patched": {
                        "fail_pass": {"file_list": ["tests/test_foo.py::test_new"]},
                        "pass_pass": {"file_list": ["tests/test_bar.py::test_old"]},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "instances.jsonl"
    instances = exporter.export_instances(
        tmp_path / "samples",
        output,
        "benchmark-openhands-",
        "/workspace/repo",
    )

    assert len(instances) == 1
    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["problem_statement"] == "Implement a feature."
    assert row["requirements"] == ["Expose Foo.", "Keep Bar unchanged."]
    assert row["interface"][0]["Name"] == "Foo"
    assert row["image_name"] == "benchmark-openhands-sample_1:latest"
    assert row["source_repo_path"] == "/workspace/repo"


def test_convert_openhands_preds_extracts_git_patch() -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    rows = [
        {
            "instance_id": "sample_1",
            "test_result": {"git_patch": "diff --git a/x.py b/x.py\n"},
            "history": [{"kind": "ActionEvent", "tool_name": "finish"}],
        },
        {"instance_id": "sample_2", "test_result": {}},
    ]

    converted = converter.convert_rows(rows, "openhands")

    assert [row["instance_id"] for row in converted] == ["sample_1", "sample_2"]
    assert converted[0]["model_name_or_path"] == "openhands"
    assert converted[0]["model_patch"] == "diff --git a/x.py b/x.py\n"
    assert converted[0]["step_exhausted"] is False
    assert converted[0]["repeated_command_loop"] is False
    assert converted[0]["_agent"]["steps"] == 1
    assert converted[0]["_agent"]["success"] is True
    assert converted[0]["_agent"]["run_completed"] is True
    assert converted[1]["model_patch"] == ""
    assert converted[1]["_agent"]["steps"] == 0


def test_convert_openhands_preds_prefers_success_over_later_error(tmp_path: Path) -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    rows = [
        {
            "instance_id": "sample_1",
            "test_result": {"git_patch": "diff --git a/x.py b/x.py\n"},
            "history": [
                {
                    "kind": "ActionEvent",
                    "tool_name": "finish",
                    "llm_response_id": "response-1",
                }
            ],
            "metrics": {
                "accumulated_token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 3,
                    "cache_read_tokens": 4,
                },
                "token_usages": [
                    {
                        "response_id": "response-1",
                        "prompt_tokens": 10,
                        "completion_tokens": 3,
                        "cache_read_tokens": 4,
                    }
                ],
            },
        },
        {
            "instance_id": "sample_1",
            "test_result": {},
            "history": [],
            "metrics": None,
            "error": "Docker is not available.",
        },
    ]

    converted = converter.convert_rows(rows, "openhands")
    converter.write_openhands_trajectories(rows, tmp_path)
    summary = json.loads(
        (tmp_path / "sample_1" / "sample_1.summary.json").read_text(encoding="utf-8")
    )

    assert len(converted) == 1
    assert converted[0]["model_patch"] == "diff --git a/x.py b/x.py\n"
    assert converted[0]["_agent"]["steps"] == 1
    assert converted[0]["_agent"]["input_tokens"] == 10
    assert converted[0]["_agent"]["cached_input_tokens"] == 4
    assert summary["agent"]["steps"] == 1
    assert summary["agent"]["input_tokens"] == 10
    assert summary["agent"]["cached_input_tokens"] == 4
    assert summary["agent"]["exit_status"] is None


def test_write_openhands_trajectory_exports_per_instance_json(tmp_path: Path) -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "instance_sample_1.log").write_text("agent log\n", encoding="utf-8")
    (logs_dir / "instance_sample_1.output.log").write_text(
        'output log {"reasoning_tokens": 17, "thinking_blocks": [{"thinking": "hidden"}]}\n',
        encoding="utf-8",
    )
    row = {
        "instance_id": "sample_1",
        "test_result": {"git_patch": "diff --git a/x.py b/x.py\n"},
        "history": [
            SimpleNamespace(
                kind="ActionEvent",
                tool_name="finish",
                llm_response_id="response-1",
                reasoning_content="hidden chain",
                thinking_blocks=[{"thinking": "hidden chain"}],
            )
        ],
        "metrics": {
            "accumulated_token_usage": {
                "prompt_tokens": 7,
                "completion_tokens": 3,
                "reasoning_tokens": 17,
            },
            "token_usages": [
                {
                    "prompt_tokens": 7,
                    "completion_tokens": 3,
                    "reasoning_tokens": 17,
                    "response_id": "response-1",
                }
            ],
            "reasoning_details": [{"text": "hidden chain"}],
            "responses_reasoning_item": {"summary": ["hidden chain"]},
            "thinking_blocks": [{"thinking": "hidden chain"}],
            "reasoning": "hidden chain",
            "reasoning_content": "hidden chain",
        },
        "reasoning": {"effort": "medium"},
        "metadata": {"output_dir": tmp_path},
    }

    summary_path = converter.write_openhands_trajectory(row, tmp_path)

    instance_dir = tmp_path / "sample_1"
    traj_path = instance_dir / "sample_1.traj.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    trajectory = json.loads(traj_path.read_text(encoding="utf-8"))

    assert summary["framework"] == "openhands"
    assert summary["agent"]["steps"] == 1
    assert trajectory["schema_version"] == 1
    assert trajectory["framework"] == "openhands"
    assert trajectory["instance_id"] == "sample_1"
    assert trajectory["agent"]["input_tokens"] == 7
    assert trajectory["agent"]["output_tokens"] == 3
    assert trajectory["raw_output"]["history"][0]["tool_name"] == "finish"
    assert trajectory["raw_output"]["metadata"]["output_dir"] == str(tmp_path)
    trajectory_text = traj_path.read_text(encoding="utf-8")
    assert "reasoning_tokens" not in trajectory_text
    assert "reasoning_content" not in trajectory_text
    assert "responses_reasoning_item" not in trajectory_text
    assert "thinking_blocks" not in trajectory_text
    assert (
        (instance_dir / "openhands.log").read_text(encoding="utf-8")
        == "agent log\n"
    )
    output_log = (instance_dir / "openhands.output.log").read_text(encoding="utf-8")
    assert "redacted reasoning artifact" in output_log
    assert "reasoning_tokens" not in output_log
    assert "thinking_blocks" not in output_log


def test_convert_openhands_preds_drops_openhands_state_files() -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    patch = (
        "diff --git a/pkg/source.py b/pkg/source.py\n"
        "--- a/pkg/source.py\n"
        "+++ b/pkg/source.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "diff --git a/workspace/bash_events/event.json b/workspace/bash_events/event.json\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/workspace/bash_events/event.json\n"
        "@@ -0,0 +1 @@\n"
        "+{}\n"
        "diff --git a/conversations/state.json b/conversations/state.json\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/conversations/state.json\n"
        "@@ -0,0 +1 @@\n"
        "+{}\n"
    )

    converted = converter.convert_rows(
        [
            {
                "instance_id": "sample_1",
                "test_result": {"git_patch": patch},
                "history": [{"kind": "ActionEvent", "tool_name": "finish"}],
            }
        ],
        "openhands",
    )

    assert converted[0]["model_patch"] == (
        "diff --git a/pkg/source.py b/pkg/source.py\n"
        "--- a/pkg/source.py\n"
        "+++ b/pkg/source.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )


def test_convert_openhands_preds_accepts_openhands_native_completion() -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    rows = [
        {
            "instance_id": "sample_1",
            "test_result": {"git_patch": "diff --git a/x.py b/x.py\n"},
            "history": [{"kind": "ActionEvent", "tool_name": "terminal"}],
        },
        {
            "instance_id": "sample_2",
            "test_result": {"git_patch": "diff --git a/y.py b/y.py\n"},
            "history": [
                {
                    "kind": "ConversationStateUpdateEvent",
                    "key": "execution_status",
                    "value": "finished",
                }
            ],
        },
        {
            "instance_id": "sample_3",
            "test_result": {"git_patch": "diff --git a/z.py b/z.py\n"},
            "history": [{"kind": "ActionEvent", "tool_name": "terminal"}],
        },
        {
            "instance_id": "sample_4",
            "test_result": {"git_patch": "diff --git a/w.py b/w.py\n"},
            "history": [
                {"kind": "ActionEvent", "tool_name": "terminal"},
                {
                    "kind": "MessageEvent",
                    "source": "agent",
                    "llm_message": {
                        "content": [{"text": "Implemented the requested change."}]
                    },
                },
            ],
        },
    ]

    converted = converter.convert_rows(rows, "openhands")

    assert converted[0]["model_patch"] == ""
    assert converted[1]["model_patch"] == ""
    assert converted[1]["_agent"]["success"] is False
    assert converted[1]["_agent"]["run_completed"] is False
    assert converted[2]["model_patch"] == ""
    assert converted[3]["model_patch"] == "diff --git a/w.py b/w.py\n"
    assert converted[3]["_agent"]["success"] is True
    assert converted[3]["_agent"]["run_completed"] is True


def test_convert_openhands_preds_applies_shared_step_budget_policy() -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )

    def action(step: int, tool: str = "terminal") -> dict[str, str]:
        return {
            "kind": "ActionEvent",
            "tool_name": tool,
            "llm_response_id": f"response-{step}",
        }

    rows = [
        {
            "instance_id": "finish_at_budget",
            "instance": {"max_iterations": 100},
            "test_result": {"git_patch": "diff --git a/a.py b/a.py\n"},
            "history": [action(step) for step in range(1, 100)] + [action(100, "finish")],
        },
        {
            "instance_id": "no_finish_at_budget",
            "instance": {"max_iterations": 100},
            "test_result": {"git_patch": "diff --git a/b.py b/b.py\n"},
            "history": [action(step) for step in range(1, 101)],
        },
        {
            "instance_id": "message_finished_at_budget",
            "instance": {"max_iterations": 100},
            "test_result": {"git_patch": "diff --git a/msg.py b/msg.py\n"},
            "history": [action(step) for step in range(1, 101)]
            + [
                {
                    "kind": "ConversationStateUpdateEvent",
                    "key": "execution_status",
                    "value": "finished",
                }
            ],
        },
        {
            "instance_id": "manual_fail_at_budget",
            "instance": {"max_iterations": 100},
            "test_result": {
                "git_patch": "diff --git a/manual.py b/manual.py\n",
                "manual_failed": True,
                "step_budget_exhausted": False,
            },
            "history": [action(step) for step in range(1, 101)],
        },
        {
            "instance_id": "over_budget",
            "instance": {"max_iterations": 100},
            "test_result": {"git_patch": "diff --git a/c.py b/c.py\n"},
            "history": [action(step) for step in range(1, 103)],
        },
        {
            "instance_id": "explicit_max_iterations_error",
            "test_result": {"git_patch": "diff --git a/d.py b/d.py\n"},
            "history": [
                {
                    "kind": "ConversationErrorEvent",
                    "code": "MaxIterationsReached",
                    "detail": "Agent reached maximum iterations limit (100).",
                }
            ],
        },
    ]

    converted = {row["instance_id"]: row for row in converter.convert_rows(rows, "openhands")}

    assert converted["finish_at_budget"]["model_patch"] == "diff --git a/a.py b/a.py\n"
    assert not converted["finish_at_budget"]["_agent"]["step_budget_exhausted"]
    assert converted["no_finish_at_budget"]["model_patch"] == ""
    assert converted["no_finish_at_budget"]["_agent"]["step_budget_exhausted"]
    assert converted["message_finished_at_budget"]["model_patch"] == ""
    assert converted["message_finished_at_budget"]["_agent"]["success"] is True
    assert converted["message_finished_at_budget"]["_agent"]["run_completed"] is True
    assert converted["message_finished_at_budget"]["_agent"]["step_budget_exhausted"]
    assert converted["manual_fail_at_budget"]["model_patch"] == ""
    assert converted["manual_fail_at_budget"]["_agent"]["success"] is False
    assert converted["manual_fail_at_budget"]["_agent"]["run_completed"] is False
    assert not converted["manual_fail_at_budget"]["_agent"]["step_budget_exhausted"]
    assert converted["over_budget"]["model_patch"] == ""
    assert converted["over_budget"]["_agent"]["step_budget_exhausted"]
    assert converted["explicit_max_iterations_error"]["model_patch"] == ""
    assert converted["explicit_max_iterations_error"]["_agent"]["step_budget_exhausted"]


def test_convert_openhands_preds_preserves_native_metrics() -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    rows = [
        {
            "instance_id": "sample_1",
            "test_result": {"git_patch": ""},
            "metrics": {
                "accumulated_cost": 0.25,
                "accumulated_token_usage": {
                    "prompt_tokens": 110,
                    "completion_tokens": 21,
                    "cache_read_tokens": 85,
                    "cache_write_tokens": 0,
                },
                "token_usages": [
                    {
                        "response_id": "pre",
                        "prompt_tokens": 10,
                        "completion_tokens": 1,
                        "cache_read_tokens": 5,
                    },
                    {
                        "response_id": "a",
                        "prompt_tokens": 30,
                        "completion_tokens": 5,
                        "cache_read_tokens": 30,
                    },
                    {
                        "response_id": "b",
                        "prompt_tokens": 70,
                        "completion_tokens": 15,
                        "cache_read_tokens": 50,
                    },
                    {
                        "response_id": "b",
                        "prompt_tokens": 70,
                        "completion_tokens": 15,
                        "cache_read_tokens": 50,
                    },
                ],
            },
            "history": [
                {
                    "kind": "ActionEvent",
                    "tool_name": "terminal",
                    "llm_response_id": "a",
                },
                {
                    "kind": "ActionEvent",
                    "tool_name": "file_editor",
                    "llm_response_id": "a",
                },
                {
                    "kind": "ActionEvent",
                    "tool_name": "finish",
                    "llm_response_id": "b",
                },
            ],
        }
    ]

    converted = converter.convert_rows(rows, "openhands")

    agent = converted[0]["_agent"]
    assert agent["steps"] == 2
    assert agent["input_tokens"] == 110
    assert agent["output_tokens"] == 21
    assert agent["instance_cost"] == 0.25
    assert agent["success"] is False
    assert agent["run_completed"] is False
    assert agent["step_budget_exhausted"] is False
    assert agent["repeated_command_loop"] is False
    assert agent["exit_status"] is None
    assert agent["cached_input_tokens"] == 85
    assert agent["cache_creation_input_tokens"] == 0
    assert agent["token_by_step"] == [
        {
            "step": 1,
            "input_tokens": 40,
            "cached_input_tokens": 35,
            "cache_creation_input_tokens": 0,
            "output_tokens": 6,
            "total_tokens": 46,
        },
        {
            "step": 2,
            "input_tokens": 70,
            "cached_input_tokens": 50,
            "cache_creation_input_tokens": 0,
            "output_tokens": 15,
            "total_tokens": 85,
        },
    ]
    assert agent["cumulative_token_by_step"] == [
        {
            "step": 1,
            "input_tokens": 40,
            "cached_input_tokens": 35,
            "cache_creation_input_tokens": 0,
            "output_tokens": 6,
            "total_tokens": 46,
        },
        {
            "step": 2,
            "input_tokens": 110,
            "cached_input_tokens": 85,
            "cache_creation_input_tokens": 0,
            "output_tokens": 21,
            "total_tokens": 131,
        },
    ]


def test_convert_openhands_preds_estimates_openrouter_gpt55_cost_with_cache() -> None:
    converter = load_module(
        "benchmark/evaluation/openhands/scripts/convert_openhands_preds.py"
    )
    rows = [
        {
            "instance_id": "sample_1",
            "metadata": {"llm": {"model": "openrouter/openai/gpt-5.5"}},
            "test_result": {"git_patch": "diff --git a/x.py b/x.py\n"},
            "history": [{"kind": "ActionEvent", "tool_name": "finish"}],
            "metrics": {
                "accumulated_cost": 0.001,
                "accumulated_token_usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 100,
                    "cache_read_tokens": 400,
                    "cache_write_tokens": 0,
                },
            },
        }
    ]

    converted = converter.convert_rows(rows, "openrouter/openai/gpt-5.5")

    assert converted[0]["model_name_or_path"] == "gpt-5.5"
    agent = converted[0]["_agent"]
    assert round(agent["instance_cost"], 6) == 0.0062
    assert agent["input_tokens"] == 1000
    assert agent["cached_input_tokens"] == 400
    assert agent["output_tokens"] == 100


def test_openhands_output_dir_uses_explicit_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")

    explicit_dir = tmp_path / "deepseekv4_flash_20260520"

    output_dir = Path(runner.construct_quanbench_output_dir(str(explicit_dir)))

    assert output_dir == explicit_dir
    assert output_dir.is_dir()


def test_openhands_expands_config_env_vars_from_zshrc(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export GoogleVertaxAI_API_KEY="local-gemini-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GoogleVertaxAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    expanded = runner.expand_env_vars({"api_key": "$GoogleVertaxAI_API_KEY"})

    assert expanded == {"api_key": "local-gemini-key"}
    assert os.getenv("GoogleVertaxAI_API_KEY") == "local-gemini-key"
    assert os.getenv("GOOGLE_API_KEY") is None


def test_openhands_vertex_gemini_uses_aiplatform_endpoint(tmp_path: Path, monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        "\n".join(
            [
                'export GoogleVertaxAI_API_KEY="local-gemini-key"',
                'export GoogleProjectID="local-project"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GoogleVertaxAI_API_KEY", raising=False)
    monkeypatch.delenv("GoogleProjectID", raising=False)

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "model": "gemini/gemini-3-flash-preview",
                "api_key": "$GoogleVertaxAI_API_KEY",
                "base_url": (
                    "https://aiplatform.googleapis.com/v1/projects/$GoogleProjectID/"
                    "locations/global/publishers/google"
                ),
            }
        ),
        encoding="utf-8",
    )

    llm = runner.load_llm_config(config_path)

    assert str(llm.base_url) == (
        "https://aiplatform.googleapis.com/v1/projects/local-project/"
        "locations/global/publishers/google"
    )
    assert runner.model_endpoint_hosts(llm) == ["aiplatform.googleapis.com"]


def test_openhands_dashscope_qwen_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export DASHSCOPE_API_KEY="local-dashscope-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    config_path = (
        ROOT
        / "benchmark/evaluation/openhands/config/dashscope_qwen3_6_35b_a3b.json"
    )

    llm = runner.load_llm_config(config_path)

    assert llm.model == "dashscope/qwen3.6-35b-a3b"
    assert llm.api_key.get_secret_value() == "local-dashscope-key"
    assert str(llm.base_url) == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert llm.drop_params is True
    assert llm.litellm_extra_body == {"enable_thinking": False}
    assert runner.load_prediction_model_name(config_path, llm.model) == "qwen3.6-35b-a3b"
    assert runner.model_endpoint_hosts(llm) == ["dashscope.aliyuncs.com"]


def test_openhands_n_limit_preserves_dataset_order(monkeypatch) -> None:
    import pandas as pd

    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")

    monkeypatch.setattr(
        runner,
        "get_dataset",
        lambda **_: pd.DataFrame(
            [
                {"instance_id": "sample_1"},
                {"instance_id": "sample_2"},
                {"instance_id": "sample_3"},
            ]
        ),
    )
    metadata = SimpleNamespace(
        dataset="instances.jsonl",
        dataset_split="train",
        eval_limit=2,
        selected_instances_file=None,
    )

    df = runner.prepare_quanbench_dataframe(metadata)

    assert df["instance_id"].tolist() == ["sample_1", "sample_2"]


def test_openhands_slice_preserves_dataset_order(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    pd = __import__("pandas")

    monkeypatch.setattr(
        runner,
        "get_dataset",
        lambda **_: pd.DataFrame(
            [
                {"instance_id": "sample_1"},
                {"instance_id": "sample_2"},
                {"instance_id": "sample_3"},
            ]
        ),
    )
    metadata = SimpleNamespace(
        dataset="instances.jsonl",
        dataset_split="train",
        eval_limit=0,
        selected_instances_file=None,
        quanbench_slice="1:3",
    )

    df = runner.prepare_quanbench_dataframe(metadata)

    assert df["instance_id"].tolist() == ["sample_2", "sample_3"]


def test_openhands_terminal_timeout_is_configured(monkeypatch) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")

    from openhands.tools.terminal.definition import TerminalAction
    from openhands.tools.terminal.impl import TerminalExecutor

    seen_timeouts = []

    def fake_call(self, action, conversation=None):
        del self, conversation
        seen_timeouts.append(action.timeout)
        return action.timeout

    monkeypatch.delattr(TerminalExecutor, "_quanbench_original_call", raising=False)
    monkeypatch.delattr(TerminalExecutor, "_quanbench_timeout_seconds", raising=False)
    monkeypatch.setattr(TerminalExecutor, "__call__", fake_call)

    runner.configure_tool_timeouts({"terminal": {"timeout_seconds": 120}})
    executor = object.__new__(TerminalExecutor)

    TerminalExecutor.__call__(executor, TerminalAction(command="echo hi", timeout=None))
    TerminalExecutor.__call__(executor, TerminalAction(command="sleep 10", timeout=30))
    TerminalExecutor.__call__(executor, TerminalAction(command="pytest", timeout=300))
    TerminalExecutor.__call__(
        executor,
        TerminalAction(command="C-c", is_input=True, timeout=None),
    )

    assert seen_timeouts == [120, 30, 120, None]


def test_openhands_agent_config_parses_tool_concurrency_limit(tmp_path: Path) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"agent": {"tool_concurrency_limit": "4"}}),
        encoding="utf-8",
    )

    assert runner.load_agent_config(config_path) == {"tool_concurrency_limit": 4}


def test_openhands_step_progress_counts_unique_responses(monkeypatch) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", stdout)

    class ActionEvent(SimpleNamespace):
        pass

    callback = runner.build_step_progress_callback("sample_1", 100, 6)
    callback(ActionEvent(tool_name="terminal", llm_response_id="resp-1"))
    callback(ActionEvent(tool_name="file_editor", llm_response_id="resp-1"))
    callback(ActionEvent(tool_name="terminal", llm_response_id="resp-2"))
    callback(ActionEvent(tool_name="think"))
    callback(ActionEvent(tool_name="terminal"))
    callback(SimpleNamespace(tool_name="terminal", llm_response_id="resp-3"))

    assert callback.step == 4
    assert not callback.exhausted
    assert stdout.getvalue().splitlines() == [
        "OPENHANDS_PROGRESS instance=sample_1 step=1/100 tool=terminal",
        "OPENHANDS_PROGRESS instance=sample_1 step=2/100 tool=terminal",
        "OPENHANDS_PROGRESS instance=sample_1 step=3/100 tool=think",
        "OPENHANDS_PROGRESS instance=sample_1 step=4/100 tool=terminal",
    ]


def test_openhands_step_progress_reports_exhaustion(monkeypatch) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    monkeypatch.setattr(sys, "__stdout__", io.StringIO())

    class ActionEvent(SimpleNamespace):
        pass

    callback = runner.build_step_progress_callback("sample_1", 2, 6)
    callback(ActionEvent(tool_name="terminal", llm_response_id="resp-1"))
    assert not callback.exhausted
    callback(ActionEvent(tool_name="terminal", llm_response_id="resp-2"))
    assert callback.exhausted


def test_openhands_step_progress_raises_on_repeated_command(monkeypatch) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    monkeypatch.setattr(sys, "__stdout__", io.StringIO())

    class ActionEvent(SimpleNamespace):
        pass

    callback = runner.build_step_progress_callback("sample_1", 100, 3)
    command = "python3 -c 'print(1)'"
    callback(
        ActionEvent(tool_name="terminal", llm_response_id="resp-1", command=command)
    )
    callback(
        ActionEvent(tool_name="terminal", llm_response_id="resp-2", command=command)
    )

    try:
        callback(
            ActionEvent(tool_name="terminal", llm_response_id="resp-3", command=command)
        )
    except runner.RepeatedCommandLoopError as exc:
        assert exc.command == command
        assert exc.count == 3
        assert exc.limit == 3
    else:
        raise AssertionError("Expected repeated command loop detection")


def test_openhands_prune_resume_keeps_step_budget_exhausted_rows(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")

    output = tmp_path / "output.jsonl"
    output.write_text(
        json.dumps(
            {
                "instance_id": "sample_1",
                "attempt": 1,
                "test_result": {"git_patch": "", "step_budget_exhausted": True},
                "instruction": "task",
                "error": None,
                "history": [],
                "metrics": {},
                "instance": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner.prune_resume_file(output, {"sample_1"}, object())

    assert len(output.read_text(encoding="utf-8").splitlines()) == 1


def test_openhands_progress_syncs_final_exhausted_step(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", stdout)

    callback = runner.build_step_progress_callback("sample_1", 100, 0)
    callback.step = 93
    callback.mark_exhausted()

    assert callback.step == 100
    assert (
        "OPENHANDS_PROGRESS instance=sample_1 "
        "step=100/100 tool=max_iterations status=step_exhausted"
    ) in stdout.getvalue()
    callback.mark_exhausted()
    assert stdout.getvalue().count("status=step_exhausted") == 1

    stdout.seek(0)
    stdout.truncate(0)
    callback = runner.build_step_progress_callback("sample_2", 100, 0)
    callback.step = 100
    callback.mark_exhausted()

    assert (
        "OPENHANDS_PROGRESS instance=sample_2 "
        "step=100/100 tool=max_iterations status=step_exhausted"
    ) in stdout.getvalue()


def test_openhands_prune_resume_drops_manually_failed_rows(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")

    output = tmp_path / "output.jsonl"
    output.write_text(
        json.dumps(
            {
                "instance_id": "sample_1",
                "attempt": 1,
                "test_result": {
                    "git_patch": "",
                    "manual_failed": True,
                    "step_budget_exhausted": True,
                },
                "instruction": "task",
                "error": None,
                "history": [],
                "metrics": {},
                "instance": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner.prune_resume_file(output, {"sample_1"}, object())

    assert output.read_text(encoding="utf-8") == ""


def test_openhands_prune_resume_drops_finished_status_without_finish_tool(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(ROOT / "external" / "OpenHands-benchmarks")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")

    output = tmp_path / "output.jsonl"
    output.write_text(
        json.dumps(
            {
                "instance_id": "sample_1",
                "attempt": 1,
                "test_result": {"git_patch": "diff --git a/x.py b/x.py\n"},
                "instruction": "task",
                "error": None,
                "history": [
                    {
                        "kind": "ConversationStateUpdateEvent",
                        "key": "execution_status",
                        "value": "finished",
                    }
                ],
                "metrics": {},
                "instance": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner.prune_resume_file(output, {"sample_1"}, object())

    assert output.read_text(encoding="utf-8") == ""


def test_openhands_prompt_uses_common_task_template() -> None:
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "benchmark/evaluation/openhands/config")),
        undefined=StrictUndefined,
    )
    rendered = env.get_template("new_feature.j2").render(
        instance={"repo_path": "/workspace/repo"},
        repo_path="/workspace/repo",
        feature_goal="Implement Foo.",
        acceptance_requirements="1. Foo is available.",
        public_interface_contract="1. Class Foo\n   - Path: pkg/foo.py",
    )

    assert "<feature_request>" in rendered
    assert "## Important Boundaries" in rendered
    assert "<environment>" in rendered
    assert "I have access to a python code repository in the directory /workspace/repo ." in rendered
    assert "I've already taken care of all changes to any of the test files described in the <feature_request>." in rendered
    assert "Also the development Python environment is already set up for you" in rendered
    assert "</environment>" in rendered
    assert "Phase 1. Reading" not in rendered
    assert "Implement Foo." in rendered
    assert "1. Foo is available." in rendered
    assert "## Completion" in rendered
    assert "use the finish tool" in rendered


def test_openrouter_gemini_minimal_does_not_send_conflicting_reasoning_effort() -> None:
    from openhands.sdk import LLM
    from openhands.sdk.llm.options.chat_options import select_chat_options

    config = json.loads((ROOT / 'benchmark/evaluation/openhands/config/openrouter_gemini_3_flash_preview.json').read_text())
    for key in ('run', 'tools', 'prediction_model_name'):
        config.pop(key)
    config['api_key'] = 'test-only-no-request'
    llm = LLM.model_validate(config)
    options = select_chat_options(llm, {}, has_tools=True)
    assert 'reasoning_effort' not in options
    assert llm.litellm_extra_body['reasoning'] == {'effort': 'minimal', 'exclude': True}
