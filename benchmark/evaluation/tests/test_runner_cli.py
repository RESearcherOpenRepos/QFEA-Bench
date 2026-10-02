from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MINISWE_SRC = ROOT / "external" / "mini-swe-agent" / "src"


def load_module(relative_path: str):
    path = ROOT / relative_path
    for entry in (ROOT, MINISWE_SRC):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    module_name = relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_minisweagent_accepts_num_workers(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/minisweagent/scripts/run_minisweagent.py")

    monkeypatch.setattr(sys, "argv", ["run_minisweagent.py", "--num-workers", "3"])
    assert runner.parse_args().workers == 3

    monkeypatch.setattr(sys, "argv", ["run_minisweagent.py", "--workers", "2"])
    assert runner.parse_args().workers == 2

    monkeypatch.setattr(sys, "argv", ["run_minisweagent.py", "--num-worksers", "4"])
    assert runner.parse_args().workers == 4


def test_autocoderover_accepts_num_workers(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")

    monkeypatch.setattr(sys, "argv", ["run_autocoderover.py", "--num-workers", "3"])
    assert runner.parse_args().workers == 3

    monkeypatch.setattr(sys, "argv", ["run_autocoderover.py", "--workers", "2"])
    assert runner.parse_args().workers == 2

    monkeypatch.setattr(sys, "argv", ["run_autocoderover.py", "--num-worksers", "4"])
    assert runner.parse_args().workers == 4


def test_autocoderover_accepts_n_limit(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")

    monkeypatch.setattr(sys, "argv", ["run_autocoderover.py", "--n-limit", "5"])
    args = runner.parse_args()
    assert args.n_limit == 5
    assert args.slice is None

    runner.apply_n_limit_selection(args)
    assert args.slice == "0:5"


def test_autocoderover_removes_workspace_git_by_default(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")

    monkeypatch.setattr(sys, "argv", ["run_autocoderover.py"])
    assert runner.parse_args().keep_workspace_git is False

    monkeypatch.setattr(sys, "argv", ["run_autocoderover.py", "--keep-workspace-git"])
    assert runner.parse_args().keep_workspace_git is True


def test_autocoderover_rejects_slice_with_n_limit(monkeypatch) -> None:
    runner = load_module("benchmark/evaluation/autocoderover/scripts/run_autocoderover.py")

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_autocoderover.py", "--slice", "1:3", "--n-limit", "5"],
    )
    args = runner.parse_args()
    try:
        runner.apply_n_limit_selection(args)
    except ValueError as exc:
        assert str(exc) == "Use either --slice or --n-limit, not both"
    else:
        raise AssertionError("Expected --slice and --n-limit to be rejected together")


def test_openhands_native_completion_policy() -> None:
    policy = load_module("benchmark/evaluation/openhands/scripts/run_policy.py")

    agent_message = {
        "kind": "MessageEvent",
        "source": "agent",
        "llm_message": {
            "content": [{"text": "Implemented the requested change."}],
        },
    }

    assert policy.completion_signal([agent_message]) == "agent_message"
    assert policy.has_completion_signal([agent_message])
    assert not policy.has_completion_signal(
        [
            {
                "kind": "ConversationStateUpdateEvent",
                "key": "execution_status",
                "value": "finished",
            }
        ]
    )
    assert not policy.has_completion_signal(
        [agent_message, {"kind": "ActionEvent", "tool_name": "terminal"}]
    )
