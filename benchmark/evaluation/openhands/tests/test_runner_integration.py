from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]


def load_module(relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openhands_caps_no_finish_retries(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENHANDS_SUPPRESS_BANNER", "1")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    original_execute_single_attempt = runner.Evaluation._execute_single_attempt

    try:
        runner.patch_evaluation_retry_limit_hook()
        assert getattr(
            runner.Evaluation._execute_single_attempt,
            "_quanbench_retry_limit_hook",
            False,
        )
    finally:
        runner.Evaluation._execute_single_attempt = original_execute_single_attempt

    dummy = SimpleNamespace(metadata=SimpleNamespace(details={}))
    assert (
        runner.QuanBenchOpenHandsEvaluation._max_retries_for_exception(
            dummy,
            runner.NoFinishToolError("OpenHands finished without finish tool"),
            3,
        )
        == 1
    )
    assert (
        runner.QuanBenchOpenHandsEvaluation._max_retries_for_exception(
            dummy,
            RuntimeError("Remote conversation ended with error"),
            3,
        )
        == 3
    )

    dummy.metadata.details = {"run": {"no_finish_max_attempts": 3}}
    assert (
        runner.QuanBenchOpenHandsEvaluation._max_retries_for_exception(
            dummy,
            runner.NoFinishToolError("OpenHands finished without finish tool"),
            3,
        )
        == 2
    )

    config_path = tmp_path / "openhands.json"
    config_path.write_text(
        '{"run": {"max_retries": 3, "no_finish_max_attempts": 4}}',
        encoding="utf-8",
    )
    defaults = runner.load_run_defaults(config_path)
    assert defaults["max_retries"] == 3
    assert defaults["no_finish_max_attempts"] == 4


def test_openhands_cached_repo_update_skip_patch(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENHANDS_SUPPRESS_BANNER", "1")
    runner = load_module("benchmark/evaluation/openhands/scripts/run_openhands.py")
    calls = []

    def fake_do_clone_or_update(url, repo_path, ref, update, git):
        calls.append(
            {
                "url": url,
                "repo_path": repo_path,
                "ref": ref,
                "update": update,
                "git": git,
            }
        )
        return repo_path

    monkeypatch.setattr(
        runner.openhands_cached_repo,
        "_do_clone_or_update",
        fake_do_clone_or_update,
    )
    monkeypatch.setenv(runner.SKIP_CACHE_REPO_UPDATE_ENV, "1")
    runner.patch_cached_repo_update_skip()

    repo_path = tmp_path / "repo"
    (repo_path / ".git").mkdir(parents=True)
    git = object()

    assert (
        runner.openhands_cached_repo._do_clone_or_update(
            "https://example.test/repo.git",
            repo_path,
            "main",
            True,
            git,
        )
        == repo_path
    )
    assert calls == [
        {
            "url": "https://example.test/repo.git",
            "repo_path": repo_path,
            "ref": "main",
            "update": False,
            "git": git,
        }
    ]
