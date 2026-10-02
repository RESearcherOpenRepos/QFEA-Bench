"""Shared run-status semantics for benchmark agent outputs."""

from __future__ import annotations

from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    """Normalized runner outcome used by all framework adapters."""

    SUBMITTED = "submitted"
    STEP_EXHAUSTED = "step_exhausted"
    REPEATED_COMMAND_LOOP = "repeated_command_loop"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


def has_nonempty_patch(patch: Any) -> bool:
    return bool(str(patch or "").strip())


def agent_step_exhausted(agent: dict[str, Any] | None) -> bool:
    if not isinstance(agent, dict):
        return False
    return bool(agent.get("step_budget_exhausted")) or agent.get("exit_status") == "LimitsExceeded"


def agent_repeated_command_loop(agent: dict[str, Any] | None) -> bool:
    if not isinstance(agent, dict):
        return False
    return bool(agent.get("repeated_command_loop")) or agent.get("exit_status") == "RepeatedCommandLoop"


def agent_timed_out(agent: dict[str, Any] | None) -> bool:
    if not isinstance(agent, dict):
        return False
    return bool(agent.get("timed_out")) or agent.get("exit_status") == "TimedOut"


def row_agent(row: dict[str, Any]) -> dict[str, Any] | None:
    return row.get("_agent") or row.get("agent") or row.get("_summary_agent")


def row_step_exhausted(row: dict[str, Any]) -> bool:
    return bool(row.get("step_exhausted")) or agent_step_exhausted(row_agent(row))


def row_repeated_command_loop(row: dict[str, Any]) -> bool:
    return bool(row.get("repeated_command_loop")) or agent_repeated_command_loop(row_agent(row))


def row_timed_out(row: dict[str, Any]) -> bool:
    return bool(row.get("timed_out")) or agent_timed_out(row_agent(row))


def row_patch_candidate_submitted(row: dict[str, Any]) -> bool:
    agent = row_agent(row)
    return bool(row.get("patch_candidate_submitted")) or (
        isinstance(agent, dict) and bool(agent.get("patch_candidate_submitted"))
    )


def row_submitted(row: dict[str, Any]) -> bool:
    return (
        not row_step_exhausted(row)
        and not row_repeated_command_loop(row)
        and not row_timed_out(row)
        and (
            has_nonempty_patch(row.get("model_patch"))
            or row_patch_candidate_submitted(row)
        )
    )


def row_run_completed(row: dict[str, Any]) -> bool:
    return (
        row_submitted(row)
        or row_step_exhausted(row)
        or row_repeated_command_loop(row)
        or row_timed_out(row)
    )


def row_status(row: dict[str, Any]) -> RunStatus:
    if row_step_exhausted(row):
        return RunStatus.STEP_EXHAUSTED
    if row_repeated_command_loop(row):
        return RunStatus.REPEATED_COMMAND_LOOP
    if row_timed_out(row):
        return RunStatus.TIMED_OUT
    if row_submitted(row):
        return RunStatus.SUBMITTED
    return RunStatus.FAILED
