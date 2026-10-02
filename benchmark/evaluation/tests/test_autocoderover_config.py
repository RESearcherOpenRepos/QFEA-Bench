from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module(relative_path: str):
    path = ROOT / relative_path
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_autocoderover_openrouter_gpt55_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export OPENROUTER_API_KEY="local-openrouter-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    config = runner.read_config(
        ROOT / "benchmark/evaluation/autocoderover/config/openrouter_gpt55.json",
    )

    assert config["model"] == "litellm-generic-openrouter/openai/gpt-5.5"
    assert config["prediction_model_name"] == "gpt-5.5"
    assert config["env"]["OPENROUTER_API_KEY"] == "local-openrouter-key"
    assert config["env"]["ACR_LITELLM_API_KEY"] == "local-openrouter-key"
    assert config["env"]["ACR_LITELLM_API_BASE"] == "https://openrouter.ai/api/v1"
    assert json.loads(config["env"]["ACR_LITELLM_EXTRA_BODY"]) == {
        "usage": {"include": True},
        "reasoning": {"effort": "none"},
    }
    assert os.getenv("OPENROUTER_API_KEY") == "local-openrouter-key"


def test_autocoderover_openrouter_glm52_zai_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export OPENROUTER_API_KEY="local-openrouter-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    config = runner.read_config(
        ROOT / "benchmark/evaluation/autocoderover/config/openrouter_glm5_2_zai.json",
    )

    assert config["model"] == "litellm-generic-openrouter/z-ai/glm-5.2"
    assert config["prediction_model_name"] == "glm-5.2"
    assert config["env"]["OPENROUTER_API_KEY"] == "local-openrouter-key"
    assert config["env"]["ACR_LITELLM_API_KEY"] == "local-openrouter-key"
    assert config["env"]["ACR_LITELLM_API_BASE"] == "https://openrouter.ai/api/v1"
    assert json.loads(config["env"]["ACR_LITELLM_EXTRA_BODY"]) == {
        "usage": {"include": True},
        "reasoning": {"effort": "none"},
        "provider": {"only": ["Z.AI"], "allow_fallbacks": False},
    }
    assert os.getenv("OPENROUTER_API_KEY") == "local-openrouter-key"


def test_autocoderover_dashscope_glm52_config_loads_key_from_zshrc(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text(
        'export DASHSCOPE_API_KEY="local-dashscope-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    config = runner.read_config(
        ROOT / "benchmark/evaluation/autocoderover/config/dashscope_glm5_2.json",
    )

    assert config["model"] == "litellm-generic-dashscope/glm-5.2"
    assert config["prediction_model_name"] == "glm-5.2"
    assert config["env"]["DASHSCOPE_API_KEY"] == "local-dashscope-key"
    assert config["env"]["ACR_LITELLM_API_KEY"] == "local-dashscope-key"
    assert config["env"]["ACR_LITELLM_API_BASE"] == (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    assert json.loads(config["env"]["ACR_LITELLM_EXTRA_BODY"]) == {
        "enable_thinking": False,
    }
    assert os.getenv("DASHSCOPE_API_KEY") == "local-dashscope-key"


def test_autocoderover_gpt55_extract_metrics_estimates_cost(tmp_path: Path) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")
    task_output = tmp_path / "acr_output" / "sample_2026-06-25_00-00-00"
    task_output.mkdir(parents=True)
    (task_output / "info.log").write_text(
        "input_tokens=1000000, output_tokens=1000000, cost=0.0\n",
        encoding="utf-8",
    )

    metrics = runner.extract_agent_metrics(
        task_output_dir=task_output,
        patch="",
        returncode=0,
        model_name="gpt-5.5",
    )

    assert metrics["input_tokens"] == 1_000_000
    assert metrics["output_tokens"] == 1_000_000
    assert metrics["instance_cost"] == 35.0


def test_autocoderover_env_injects_runtime_patch(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")
    monkeypatch.setenv("PYTHONPATH", "existing-path")

    env = runner.acr_env({"overall_retry_limit": 5, "env": {}}, runner.DEFAULT_ACR_ROOT)
    pythonpath = env["PYTHONPATH"].split(os.pathsep)

    assert pythonpath[0] == str(runner.RUNTIME_PATCH_DIR)
    assert pythonpath[1] == str(runner.DEFAULT_ACR_ROOT)
    assert "existing-path" in pythonpath
    assert env["ACR_OVERALL_RETRY_LIMIT"] == "5"


def test_autocoderover_prune_workspace_git_removes_only_git_metadata(tmp_path: Path) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")
    repo_dir = tmp_path / "workspace" / "repo"
    git_dir = repo_dir / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (repo_dir / "module.py").write_text("value = 1\n", encoding="utf-8")

    assert runner.prune_workspace_git(repo_dir) is True
    assert not git_dir.exists()
    assert (repo_dir / "module.py").read_text(encoding="utf-8") == "value = 1\n"
    assert runner.prune_workspace_git(repo_dir) is False


def test_autocoderover_runtime_patch_extracts_new_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    acr_root = ROOT / "external" / "auto-code-rover"
    if str(acr_root) not in sys.path:
        sys.path.insert(0, str(acr_root))

    class DummyLogger:
        def opt(self, *args, **kwargs):
            return self

        def bind(self, *args, **kwargs):
            return self

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    monkeypatch.setitem(
        sys.modules,
        "loguru",
        types.SimpleNamespace(logger=DummyLogger()),
    )

    class DummyRun:
        def __init__(self, *args, **kwargs):
            pass

    class DummyTextReporter:
        def __init__(self, *args, **kwargs):
            pass

    pylint_module = types.ModuleType("pylint")
    pylint_lint_module = types.ModuleType("pylint.lint")
    pylint_reporters_module = types.ModuleType("pylint.reporters")
    pylint_text_module = types.ModuleType("pylint.reporters.text")
    pylint_lint_module.Run = DummyRun
    pylint_text_module.TextReporter = DummyTextReporter
    monkeypatch.setitem(sys.modules, "pylint", pylint_module)
    monkeypatch.setitem(sys.modules, "pylint.lint", pylint_lint_module)
    monkeypatch.setitem(sys.modules, "pylint.reporters", pylint_reporters_module)
    monkeypatch.setitem(sys.modules, "pylint.reporters.text", pylint_text_module)

    load_module("benchmark/evaluation/autocoderover/scripts/runtime_patch/sitecustomize.py")

    from app.post_process import ExtractStatus, convert_response_to_diff

    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    git("init")
    git("add", ".")
    git("-c", "user.name=QuanBench", "-c", "user.email=quanbench@example.com", "commit", "-m", "init")
    base_commit = git("rev-parse", "HEAD").stdout.strip()

    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "meta.json").write_text(
        json.dumps(
            {
                "task_info": {"base_commit": base_commit},
                "setup_info": {"repo_path": str(repo)},
            }
        ),
        encoding="utf-8",
    )
    response = """# modification 1
```
<file>pkg/new_module.py</file>
<original></original>
<patched>def answer():
    return 42
</patched>
```
"""

    status, message, diff = convert_response_to_diff(response, str(task_dir))

    assert status == ExtractStatus.APPLICABLE_PATCH, message
    assert "diff --git a/pkg/new_module.py b/pkg/new_module.py" in diff
    assert "--- /dev/null" in diff
    assert "+def answer():" in diff
    assert "+    return 42" in diff

    absolute_response = f"""# modification 1
```
<file>{repo / "pkg" / "absolute_module.py"}</file>
<original></original>
<patched>VALUE = 7</patched>
```
"""

    status, message, diff = convert_response_to_diff(absolute_response, str(task_dir))

    assert status == ExtractStatus.APPLICABLE_PATCH, message
    assert "diff --git a/pkg/absolute_module.py b/pkg/absolute_module.py" in diff
    assert str(repo) not in diff
    assert "+VALUE = 7" in diff


def test_autocoderover_indexes_literal_workspace_paths(tmp_path: Path) -> None:
    runner = load_module('benchmark/evaluation/autocoderover/scripts/run_autocoderover.py')
    acr_root = ROOT / 'external/auto-code-rover'
    for name in ('ordinary', 'project [copy]?'):
        repo = tmp_path / name
        (repo / 'pkg').mkdir(parents=True)
        (repo / 'tests').mkdir()
        (repo / 'pkg/module.py').write_text('def actual_feature():\n    return 1\n')
        (repo / 'tests/test_module.py').write_text('def test_feature():\n    pass\n')
        env = os.environ.copy()
        env['PYTHONPATH'] = runner.acr_pythonpath(acr_root)
        completed = subprocess.run(
            [sys.executable, '-c',
             'import json,sys; from pathlib import Path; '
             'from app.search.search_backend import SearchBackend; '
             'index=SearchBackend(sys.argv[1]); '
             'print(json.dumps({"files":[str(Path(p).relative_to(sys.argv[1])) for p in index.parsed_files],"functions":sorted(index.function_index)}))', str(repo)],
            env=env, cwd=acr_root, check=True, capture_output=True, text=True,
        )
        assert json.loads(completed.stdout.strip()) == {
            'files': ['pkg/module.py'], 'functions': ['actual_feature'],
        }
