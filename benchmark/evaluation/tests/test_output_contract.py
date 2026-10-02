from __future__ import annotations

import json

from benchmark.evaluation.common.run_io import write_prediction_artifacts
from benchmark.evaluation.common.run_status import RunStatus, row_status
from benchmark.evaluation.common.output_schema import prediction_payload


def test_prediction_payload_uses_shared_run_status() -> None:
    rows = [
        {
            "model_name_or_path": "model",
            "instance_id": "submitted",
            "model_patch": "diff --git a/a.py b/a.py\n",
            "_agent": {
                "steps": 2,
                "input_tokens": 10,
                "output_tokens": 2,
                "instance_cost": 1.25,
            },
        },
        {
            "model_name_or_path": "model",
            "instance_id": "limited",
            "model_patch": "",
            "_agent": {
                "steps": 3,
                "step_budget_exhausted": True,
                "input_tokens": 20,
                "cached_input_tokens": 7,
                "cache_creation_input_tokens": 3,
                "output_tokens": 4,
                "instance_cost": 0.5,
            },
        },
        {
            "model_name_or_path": "model",
            "instance_id": "failed",
            "model_patch": "",
            "_agent": {"input_tokens": 30, "output_tokens": 6},
        },
        {
            "model_name_or_path": "model",
            "instance_id": "repeated",
            "model_patch": "",
            "_agent": {
                "steps": 1,
                "exit_status": "RepeatedCommandLoop",
                "repeated_command_loop": True,
                "repeated_command": "echo hi",
                "consecutive_count": 6,
                "consecutive_command_limit": 6,
                "input_tokens": 40,
                "output_tokens": 8,
                "instance_cost": "0.25",
            },
        },
    ]

    payload = prediction_payload(rows)
    summary_keys = list(payload["summary"])

    assert payload["summary"] == {
        "total": 4,
        "success": 3,
        "submitted": 1,
        "step_exhausted": 1,
        "timed_out": 0,
        "repeated_command_loop": 1,
        "steps": 6,
        "total_cost": 2.0,
        "input_tokens": 100,
        "cached_input_tokens": 7,
        "cache_creation_input_tokens": 3,
        "output_tokens": 20,
    }
    assert summary_keys[summary_keys.index("steps") + 1] == "total_cost"
    assert row_status(rows[0]) is RunStatus.SUBMITTED
    assert row_status(rows[1]) is RunStatus.STEP_EXHAUSTED
    assert row_status(rows[2]) is RunStatus.FAILED
    assert row_status(rows[3]) is RunStatus.REPEATED_COMMAND_LOOP
    assert "_agent" not in payload["predictions"]["submitted"]
    assert payload["predictions"]["repeated"]["repeated_command_loop"] is True
    assert payload["predictions"]["repeated"]["repeated_command"] == "echo hi"


def test_write_prediction_artifacts_updates_common_files(tmp_path) -> None:
    row = write_prediction_artifacts(
        tmp_path,
        framework="example",
        instance_id="sample_1",
        model_name="model",
        patch="diff --git a/a.py b/a.py\n",
        agent={
            "steps": 3,
            "input_tokens": 11,
            "output_tokens": 5,
            "instance_cost": 0.125,
        },
    )

    preds = json.loads((tmp_path / "preds.json").read_text(encoding="utf-8"))
    summary = json.loads(
        (tmp_path / "sample_1" / "sample_1.summary.json").read_text(encoding="utf-8")
    )
    jsonl_lines = (tmp_path / "preds.jsonl").read_text(encoding="utf-8").splitlines()

    assert row["instance_id"] == "sample_1"
    assert preds["summary"]["submitted"] == 1
    assert preds["summary"]["total_cost"] == 0.125
    summary_keys = list(preds["summary"])
    assert summary_keys[summary_keys.index("steps") + 1] == "total_cost"
    assert preds["predictions"]["sample_1"]["model_patch"].startswith("diff --git")
    assert summary["framework"] == "example"
    assert summary["agent"]["steps"] == 3
    assert len(jsonl_lines) == 1


def test_write_prediction_artifacts_normalizes_provider_model_name(tmp_path) -> None:
    row = write_prediction_artifacts(
        tmp_path,
        framework="example",
        instance_id="sample_1",
        model_name="litellm-generic-dashscope/glm-5.2",
        patch="diff --git a/a.py b/a.py\n",
        agent={"steps": 1},
    )

    preds = json.loads((tmp_path / "preds.json").read_text(encoding="utf-8"))

    assert row["model_name_or_path"] == "glm-5.2"
    assert preds["predictions"]["sample_1"]["model_name_or_path"] == "glm-5.2"


def test_prediction_payload_omits_cost_currency() -> None:
    payload = prediction_payload(
        [
            {
                "model_name_or_path": "qwen3.6-35b-a3b",
                "instance_id": "sample",
                "model_patch": "diff --git a/a.py b/a.py\n",
                "_agent": {"steps": 1, "instance_cost": 0.201626},
            }
        ]
    )

    assert payload["summary"]["total_cost"] == 0.201626
    assert "cost_currency" not in payload["summary"]
