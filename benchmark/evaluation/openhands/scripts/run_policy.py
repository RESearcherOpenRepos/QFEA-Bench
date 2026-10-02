"""Shared OpenHands run-completion and step-budget policy."""

from __future__ import annotations

from typing import Any


def event_value(event: Any, name: str, default: Any = None) -> Any:
    if isinstance(event, dict):
        return event.get(name, default)
    return getattr(event, name, default)


def event_kind(event: Any) -> str:
    return str(event_value(event, "kind") or event_value(event, "event_type") or event.__class__.__name__)


def count_unique_agent_steps(events: list[Any]) -> int:
    response_ids: set[str] = set()
    action_events_without_response_id = 0
    for event in events:
        if event_kind(event) != "ActionEvent":
            continue
        if not event_value(event, "tool_name"):
            continue
        response_id = event_value(event, "llm_response_id")
        if response_id:
            response_ids.add(str(response_id))
        else:
            action_events_without_response_id += 1
    return len(response_ids) + action_events_without_response_id


def has_finish_action(events: list[Any]) -> bool:
    return any(
        event_kind(event) == "ActionEvent"
        and event_value(event, "tool_name") == "finish"
        for event in events
    )


def has_finished_status(events: list[Any]) -> bool:
    return any(
        event_kind(event) == "ConversationStateUpdateEvent"
        and event_value(event, "key") == "execution_status"
        and str(event_value(event, "value") or "").lower() == "finished"
        for event in events
    )


def _message_has_text(event: Any) -> bool:
    message = event_value(event, "llm_message")
    content = event_value(message, "content", []) or []
    for item in content:
        text = event_value(item, "text")
        if isinstance(text, str) and text.strip():
            return True
    return False


def has_final_agent_message(events: list[Any]) -> bool:
    """Return whether OpenHands ended with its native agent text response."""
    for event in reversed(events):
        kind = event_kind(event)
        if kind == "MessageEvent":
            return (
                event_value(event, "source") == "agent"
                and _message_has_text(event)
            )
        if kind == "ActionEvent":
            return False
    return False


def completion_signal(events: list[Any]) -> str | None:
    if has_finish_action(events):
        return "finish_tool"
    if has_final_agent_message(events):
        return "agent_message"
    return None


def has_completion_signal(events: list[Any]) -> bool:
    return completion_signal(events) is not None


def has_max_iterations_error(events: list[Any]) -> bool:
    for event in events:
        if event_kind(event) != "ConversationErrorEvent":
            continue
        code = str(event_value(event, "code") or "")
        detail = str(event_value(event, "detail") or "")
        if code == "MaxIterationsReached" or "maximum iterations" in detail.lower():
            return True
    return False


def step_budget_exhausted(
    *,
    events: list[Any],
    max_iterations: int | None,
    explicit_exhausted: bool = False,
    observed_steps: int = 0,
) -> bool:
    if explicit_exhausted or has_max_iterations_error(events):
        return True
    if max_iterations is None:
        return False
    steps = max(observed_steps, count_unique_agent_steps(events))
    if steps > max_iterations:
        return True
    return steps >= max_iterations and not has_completion_signal(events)


def row_max_iterations(row: dict[str, Any]) -> int | None:
    metadata = row.get("metadata") or {}
    max_iterations = (
        row.get("max_iterations")
        or metadata.get("max_iterations")
        or (row.get("instance") or {}).get("max_iterations")
    )
    try:
        return int(max_iterations)
    except (TypeError, ValueError):
        return None


def row_step_budget_exhausted(row: dict[str, Any]) -> bool:
    test_result = row.get("test_result") or {}
    return step_budget_exhausted(
        events=row.get("history") or [],
        max_iterations=row_max_iterations(row),
        explicit_exhausted=bool(
            isinstance(test_result, dict) and test_result.get("step_budget_exhausted")
        ),
    )
