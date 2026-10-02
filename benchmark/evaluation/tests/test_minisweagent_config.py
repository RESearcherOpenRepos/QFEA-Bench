from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
MINISWE_SRC = ROOT / "external" / "mini-swe-agent" / "src"


def load_module(relative_path: str):
    path = ROOT / relative_path
    for entry in (ROOT, MINISWE_SRC):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_miniswe_vertex_gemini_uses_litellm_aiplatform_endpoint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")
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

    config = runner.load_config(
        [
            ROOT / "benchmark/evaluation/minisweagent/config/new_feature.yaml",
            ROOT / "benchmark/evaluation/minisweagent/config/vertex_gemini_3_flash_preview.yaml",
        ],
        None,
    )

    model = config["model"]
    assert model["model_class"] == "litellm"
    assert model["model_name"] == "gemini/gemini-3-flash-preview"
    assert model["model_kwargs"]["api_key"] == "local-gemini-key"
    assert model["model_kwargs"]["api_base"] == (
        "https://aiplatform.googleapis.com/v1/projects/local-project/"
        "locations/global/publishers/google"
    )
    assert runner.model_source_from_config(config) == "vertex"


def test_miniswe_openrouter_gpt55_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export OPENROUTER_API_KEY="local-openrouter-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    config = runner.load_config(
        [
            ROOT / "benchmark/evaluation/minisweagent/config/new_feature.yaml",
            ROOT / "benchmark/evaluation/minisweagent/config/openrouter_gpt55.yaml",
        ],
        None,
    )
    runner.configure_model_env(config)

    model = config["model"]
    assert model["model_class"] == "openrouter"
    assert model["model_name"] == "openai/gpt-5.5"
    assert model["model_kwargs"]["reasoning"] == {"effort": "none"}
    assert runner.model_source_from_config(config) == "openrouter"
    assert runner.prediction_model_name_from_config(config) == "gpt-5.5"
    assert os.getenv("OPENROUTER_API_KEY") == "local-openrouter-key"


def test_miniswe_openrouter_glm52_zai_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export OPENROUTER_API_KEY="local-openrouter-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    config = runner.load_config(
        [
            ROOT / "benchmark/evaluation/minisweagent/config/new_feature.yaml",
            ROOT / "benchmark/evaluation/minisweagent/config/openrouter_glm5_2_zai.yaml",
        ],
        None,
    )
    runner.configure_model_env(config)

    model = config["model"]
    assert model["model_class"] == "openrouter"
    assert model["model_name"] == "z-ai/glm-5.2"
    assert model["model_kwargs"]["reasoning"] == {"effort": "none"}
    assert model["model_kwargs"]["provider"] == {
        "only": ["Z.AI"],
        "allow_fallbacks": False,
    }
    assert runner.model_source_from_config(config) == "openrouter"
    assert runner.prediction_model_name_from_config(config) == "glm-5.2"
    assert os.getenv("OPENROUTER_API_KEY") == "local-openrouter-key"


@pytest.mark.parametrize("variant", ["flash", "pro"])
def test_miniswe_deepseek_config_uses_official_endpoint(variant: str) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")
    config = runner.load_config(
        [
            ROOT / "benchmark/evaluation/minisweagent/config/new_feature.yaml",
            ROOT / f"benchmark/evaluation/minisweagent/config/deepseek_v4_{variant}_official.yaml",
        ],
        None,
    )
    model = config["model"]
    assert model["model_name"] == f"openai/deepseek-v4-{variant}"
    assert model["model_kwargs"]["api_base"] == "https://api.deepseek.com"
    assert model["model_kwargs"]["temperature"] == 0.0
    assert model["model_kwargs"]["max_tokens"] == 16384
    assert model["model_kwargs"]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert runner.prediction_model_name_from_config(config) == f"deepseek-v4-{variant}"


def test_miniswe_dashscope_glm52_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export DASHSCOPE_API_KEY="local-dashscope-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    config = runner.load_config(
        [
            ROOT / "benchmark/evaluation/minisweagent/config/new_feature.yaml",
            ROOT / "benchmark/evaluation/minisweagent/config/dashscope_glm5_2.yaml",
        ],
        None,
    )
    runner.configure_model_env(config)

    model = config["model"]
    assert model["model_class"] == "litellm"
    assert model["model_name"] == "dashscope/glm-5.2"
    assert model["model_kwargs"]["api_key"] == "local-dashscope-key"
    assert model["model_kwargs"]["api_base"] == (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    assert model["model_kwargs"]["drop_params"] is True
    assert model["model_kwargs"]["extra_body"] == {"enable_thinking": False}
    assert runner.model_source_from_config(config) == "dashscope"
    assert runner.prediction_model_name_from_config(config) == "glm-5.2"
    assert os.getenv("DASHSCOPE_API_KEY") == "local-dashscope-key"


def test_miniswe_dashscope_qwen_extract_metrics_estimates_cost(tmp_path: Path) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")
    traj_path = tmp_path / "traj.json"
    traj_path.write_text(
        json.dumps(
            {
                "model_name": None,
                "messages": [
                    {
                        "role": "assistant",
                        "content": "done",
                        "extra": {
                            "response": {
                                "usage": {
                                    "input_tokens": 1_000_000,
                                    "cached_input_tokens": 1_000_000,
                                    "output_tokens": 1_000_000,
                                }
                            }
                        },
                    }
                ],
                "info": {
                    "config": {
                        "model": {"model_name": "dashscope/qwen3.6-35b-a3b"},
                    },
                    "model_stats": {"instance_cost": 99.0},
                    "exit_status": "Submitted",
                    "submission": "diff --git a/file b/file\n",
                },
            }
        ),
        encoding="utf-8",
    )

    metrics = runner.extract_trajectory_metrics(traj_path)

    assert metrics["instance_cost"] == 1.849932
    assert metrics["input_tokens"] == 1_000_000
    assert metrics["cached_input_tokens"] == 1_000_000
    assert metrics["output_tokens"] == 1_000_000
