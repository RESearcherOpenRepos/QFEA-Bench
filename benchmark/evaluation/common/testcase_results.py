"""Build suite outcomes from pytest's structured per-node reports.

This module never guesses a passing test from stdout or a suite-level count.
Only a reported call-phase pass with no failed or skipped phase counts as a
passed test case. Selected tests absent from the report remain explicit.
"""

from __future__ import annotations

import json
from typing import Any


SUITES = ("fail_pass", "pass_pass")
BEGIN = "__QUANBENCH_CASE_REPORT_BEGIN__"
END = "__QUANBENCH_CASE_REPORT_END__"


def extract_case_reports(stdout: str) -> dict[str, dict[str, Any]]:
    """Read the evaluator's delimited JSON, never pytest's prose summary."""
    lines = stdout.splitlines()
    reports: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(lines):
        if not line.startswith(BEGIN):
            continue
        suite = line[len(BEGIN):]
        if suite not in SUITES or suite in reports or index + 2 >= len(lines):
            raise ValueError(f"Malformed or duplicate case-report marker: {line}")
        payload_line = lines[index + 1]
        if lines[index + 2] != END + suite:
            raise ValueError(f"Missing case-report end marker for {suite}")
        envelope = json.loads(payload_line)
        if not isinstance(envelope, dict) or not isinstance(envelope.get("pytest_exit_code"), int):
            raise ValueError(f"Invalid case-report envelope for {suite}")
        report = envelope.get("report")
        if report is not None:
            if not isinstance(report, dict) or report.get("schema_version") != 1:
                raise ValueError(f"Unsupported case-report schema for {suite}")
            if report.get("exitstatus") != envelope["pytest_exit_code"]:
                raise ValueError(f"Pytest exit code disagrees with case report for {suite}")
        reports[suite] = envelope
    return reports


def _node_matches(parent: str, child: str) -> bool:
    parent = parent.removeprefix("./")
    child = child.removeprefix("./")
    return child == parent or any(
        child.startswith(parent + suffix) for suffix in ("[", "::", " (")
    )


def _item_status(events: list[dict[str, Any]]) -> tuple[str, str]:
    if any(event["outcome"] == "failed" for event in events):
        failed = next(event for event in events if event["outcome"] == "failed")
        return "failed", failed["when"]
    if any(event["outcome"] == "skipped" for event in events):
        return "skipped", ""
    if any(event["when"] == "call" and event["outcome"] == "passed" for event in events):
        return "passed", ""
    return "not_run", ""


def summarize_structured_suite(
    selectors: list[str], envelope: dict[str, Any] | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return a suite fraction and one result for every selected testcase."""
    if not selectors:
        return (
            {"passed": 0, "total": 0, "summary": "0/0", "status": "not_applicable", "counts": {}},
            [],
        )
    if envelope is None:
        cases = [{"selector": selector, "status": "not_run", "phase": "", "pytest_items": []}
                 for selector in selectors]
        return (
            {"passed": 0, "total": len(cases), "summary": f"0/{len(cases)}",
             "status": "not_run", "counts": {"not_run": len(cases)}},
            cases,
        )

    report = envelope.get("report")
    exit_code = envelope["pytest_exit_code"]
    if report is None:
        cases = [
            {"selector": selector, "status": "not_collected", "phase": "startup", "pytest_items": []}
            for selector in selectors
        ]
        return (
            {"passed": 0, "total": len(cases), "summary": f"0/{len(cases)}",
             "status": "failed" if exit_code else "unknown",
             "counts": {"not_collected": len(cases)}, "pytest_exit_code": exit_code,
             "report_missing": True},
            cases,
        )

    collected = report.get("collected") or []
    collected_items = report.get("collected_items") or [
        {"nodeid": nodeid, "selector": nodeid} for nodeid in collected
    ]
    events = report.get("reports") or []
    collection_errors = report.get("collection_errors") or []
    if not isinstance(collected, list) or not isinstance(collected_items, list) or not isinstance(events, list) or not isinstance(collection_errors, list):
        raise ValueError("Malformed pytest case report")
    if [item["nodeid"] for item in collected_items] != collected:
        raise ValueError("Collected node IDs disagree with source-file identities")
    unmatched = [
        event["nodeid"] for event in events
        if not any(_node_matches(item, event["nodeid"]) for item in collected)
    ]
    cases = []
    for selector in selectors:
        items = [item["nodeid"] for item in collected_items
                 if _node_matches(selector, item["selector"])]
        blocked = [
            error for error in collection_errors
            if _node_matches(error.get("path") or error["nodeid"], selector)
        ]
        if items:
            item_results = []
            for item in items:
                item_events = [event for event in events if _node_matches(item, event["nodeid"])]
                status, phase = _item_status(item_events)
                item_results.append((status, phase))
            if any(status == "failed" for status, _ in item_results):
                status, phase = next((status, phase) for status, phase in item_results if status == "failed")
            elif any(status == "skipped" for status, _ in item_results):
                status, phase = "skipped", ""
            elif all(status == "passed" for status, _ in item_results):
                status, phase = "passed", ""
            else:
                status, phase = "not_run", ""
        elif blocked:
            status, phase = "not_collected", "collection"
        else:
            status, phase = "not_collected", ""
        cases.append({"selector": selector, "status": status, "phase": phase,
                      "pytest_items": items})

    counts = {status: sum(case["status"] == status for case in cases)
              for status in ("passed", "failed", "skipped", "not_run", "not_collected")}
    passed = counts["passed"]
    if counts["failed"] or collection_errors or exit_code not in (0, 5):
        suite_status = "failed"
    elif passed == len(selectors) and exit_code == 0 and not unmatched:
        suite_status = "passed"
    else:
        suite_status = "unknown"
    fraction = {
        "passed": passed,
        "total": len(selectors),
        "summary": f"{passed}/{len(selectors)}",
        "status": suite_status,
        "counts": counts,
        "pytest_exit_code": exit_code,
        "collection_errors": collection_errors,
        "unmatched_report_nodeids": sorted(set(unmatched)),
    }
    return fraction, cases
