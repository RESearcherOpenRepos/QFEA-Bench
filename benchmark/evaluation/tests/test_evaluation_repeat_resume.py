"""Preserve recorded or explicitly confirmed repeat counts when resuming."""

import json

import pytest

from benchmark.evaluation.scripts import evaluate_agent_preds as evaluator
from benchmark.evaluation.common.evaluation_repeats import evaluation_repeat_metadata
from rq.rq3.scripts import replay_saved_agent_results as replay


@pytest.mark.parametrize(
    "overrides,complete",
    [
        ({}, False),
        ({"evaluation_repeats": 3}, False),
        ({"evaluation_repeats": 3, "evaluation_repeats_source": "author_confirmation"}, True),
        ({"eval_runs": [{}, {}, {}]}, True),
        ({"eval_runs": [{}, {}, {}], "timed_out": True}, False),
        ({"eval_runs": [{}, {}, {}], "eval_infra_failed": True}, False),
        ({"skipped_evaluation": True}, True),
    ],
)
def test_replay_cache_requires_execution_records(tmp_path, overrides, complete):
    path = tmp_path / "results.json"
    path.write_text(json.dumps({
        "summary": {"pending": 0},
        "results": [{"test_cases": {}, **overrides} for _ in range(106)],
    }))
    assert replay.complete_casewise(path) is complete


@pytest.mark.parametrize("previous_repeats,confirmed", [(1, False), (3, False), (3, True)])
def test_resume_rechecks_patch_when_repeat_budget_increases(
    tmp_path, monkeypatch, previous_repeats, confirmed
):
    sample_path = tmp_path / "samples" / "repo" / "task" / "sample.json"
    sample_path.parent.mkdir(parents=True)
    sample_path.write_text(json.dumps({
        "instance": {"instance_id": "task", "repo": "example/repo"},
    }))
    predictions = tmp_path / "preds.json"
    predictions.write_text(json.dumps({"task": "a nonempty saved patch"}))
    output = tmp_path / "results.json"
    saved = {
        "instance_id": "task", "resolved": True, "patch_applied": True,
        "returncode": 0, "test_cases": {"fail_pass": [], "pass_pass": []},
        "fail_pass": {"passed": 0, "total": 0, "status": "passed"},
        "pass_pass": {"passed": 0, "total": 0, "status": "passed"},
    }
    if confirmed:
        saved.update(evaluation_repeats=3, evaluation_repeats_source="author_confirmation")
    elif previous_repeats == 3:
        saved["eval_runs"] = [{}, {}, {}]
    output.with_suffix(".json.partial").write_text(json.dumps({"results": [saved]}))
    calls = []

    def fake_evaluation(sample_path, model_patch, **kwargs):
        calls.append((kwargs["run_index"], kwargs["total_runs"]))
        success = kwargs["run_index"] != 2
        return {**saved, "resolved": success, "returncode": 0 if success else 1}

    monkeypatch.setattr(evaluator, "evaluate_one_run", fake_evaluation)
    payload = evaluator.evaluate_predictions(
        predictions, tmp_path / "samples", output,
        timeout=1, stable_runs=3, resume=True,
    )
    if previous_repeats == 1:
        assert calls == [(1, 3), (2, 3), (3, 3)]
        assert payload["results"][0]["resolved"] is False
        assert payload["results"][0]["resolved_runs"] == 2
        assert len(payload["results"][0]["eval_runs"]) == 3
    else:
        assert calls == []
        assert payload["results"][0]["resolved"] is True


def test_confirmed_counts_preserve_log_records_and_skipped_status():
    result = {"evaluation_repeats": 3, "evaluation_repeats_source": "author_confirmation"}
    assert evaluation_repeat_metadata(result)["evaluation_repeats"] == 3
    assert "eval_runs" not in result
    assert evaluation_repeat_metadata({**result, "skipped_evaluation": True}) == {
        "evaluation_repeats": 0, "evaluation_repeats_source": "skipped_evaluation",
    }
    with pytest.raises(ValueError, match="positive integer"):
        evaluation_repeat_metadata({**result, "evaluation_repeats": 0})


@pytest.mark.parametrize('returncode', [125, 126, 127])
def test_docker_startup_failure_is_infrastructure(returncode):
    error = 'docker: Error response from daemon: meta.db: input/output error'
    assert evaluator.parse_eval_infra_failure(error, None, returncode) == (
        f'Docker failed before evaluation started (exit {returncode})'
    )


def test_test_failure_after_patch_application_is_not_docker_setup_failure():
    assert evaluator.parse_eval_infra_failure('a test exited with status 125', True, 125) is None
    assert evaluator.parse_eval_infra_failure('1 failed', True, 1) is None
