#!/usr/bin/env python3
"""Evaluate agent predictions on benchmark samples."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.minisweagent.scripts.export_sweagent_instances import DEFAULT_SAMPLES_DIR
from benchmark.evaluation.common.io_utils import read_json, read_jsonl
from benchmark.evaluation.common.evaluation_repeats import evaluation_repeat_metadata
from benchmark.evaluation.common.model_pricing import estimated_cost_usd
from benchmark.evaluation.common.run_status import (
    has_nonempty_patch,
    row_repeated_command_loop,
    row_step_exhausted,
    row_submitted,
    row_timed_out,
)
from benchmark.evaluation.common.token_usage import (
    token_records_from_usages,
    token_totals_from_records,
)
from benchmark.evaluation.common.output_schema import normalize_agent_metrics
from benchmark.evaluation.common.patch_candidates import patch_candidate_metadata
from benchmark.evaluation.common.testcase_results import (
    extract_case_reports,
    summarize_structured_suite,
)

DEFAULT_OUTPUT = ROOT / "benchmark" / "evaluation" / "results.json"
RESULT_OMITTED_KEYS = {"token_by_step", "cumulative_token_by_step"}


def sanitize_result_payload(value: Any) -> Any:
    """Drop bulky per-step token arrays from evaluator result JSON."""
    if isinstance(value, dict):
        return {
            key: sanitize_result_payload(item)
            for key, item in value.items()
            if key not in RESULT_OMITTED_KEYS
        }
    if isinstance(value, list):
        return [sanitize_result_payload(item) for item in value]
    return value


EVAL_SCRIPT_TEMPLATE = r"""set -uo pipefail
cat > /tmp/model.patch
cat > /tmp/sample-run.sh <<'__RUN_SH__'
__RUN_SH_CONTENT__
__RUN_SH__
chmod +x /tmp/sample-run.sh
cat > /tmp/pytest_case_report.py <<'__CASE_PLUGIN__'
__PYTEST_CASE_REPORT_PLUGIN__
__CASE_PLUGIN__
export PYTHONPATH="/tmp${PYTHONPATH:+:${PYTHONPATH}}"
export MODEL_PATCH_FILE=/tmp/model.patch
REPO_DIR="${REPO_DIR:-/workspace/repo}"
FAIL_PASS_TESTS="${FAIL_PASS_TEST_PATHS:-${TEST_PATHS:-${TEST_PATH:-}}}"
PASS_PASS_TESTS="${PASS_PASS_TEST_PATHS:-${REGRESSION_TEST_PATHS:-${REGRESSION_TEST_PATH:-}}}"
FAIL_PASS_SUPPORT_FILES="${FAIL_PASS_SUPPORT_PATHS:-} ${FAIL_PASS_EXTRA_FILES:-}"
__EVALUATION_RESOURCE_CONFIG__
fail_pass_status=0
pass_pass_status=0
emit_case_report() {
  local suite="$1"
  local code="$2"
  local path="$3"
  printf '\n__QUANBENCH_CASE_REPORT_BEGIN__%s\n' "${suite}"
  printf '{"pytest_exit_code":%s,"report":' "${code}"
  if [ -s "${path}" ]; then
    cat "${path}"
  else
    printf 'null'
  fi
  printf '}\n__QUANBENCH_CASE_REPORT_END__%s\n' "${suite}"
}
QUANBENCH_EVAL_OFFLINE="${QUANBENCH_EVAL_OFFLINE:-1}"
export QUANBENCH_EVAL_OFFLINE
export GIT_NO_LAZY_FETCH=1

# Keep sample-specific PREP_ONLY logic from run.sh, but make batch
# evaluation independent of GitHub availability.
git() {
  if [ "${QUANBENCH_EVAL_OFFLINE}" = "1" ]; then
    case "${1:-}" in
      clone)
        echo "Evaluator offline mode: git clone is disabled; benchmark image must contain ${REPO_DIR}." >&2
        return 92
        ;;
      fetch)
        echo "Evaluator offline mode: skipping git fetch $*" >&2
        return 0
        ;;
    esac
  fi
  command git "$@"
}
export -f git

mark_eval_infra_failure() {
  echo "Evaluator infrastructure failure: $*" >&2
}

require_local_repo() {
  if [ ! -d "${REPO_DIR}/.git" ]; then
    mark_eval_infra_failure "benchmark image is missing local git repo at ${REPO_DIR}"
    exit 92
  fi
  cd "${REPO_DIR}"
  if ! git cat-file -e "${BASE_COMMIT}^{commit}" >/dev/null 2>&1; then
    mark_eval_infra_failure "local repo is missing BASE_COMMIT ${BASE_COMMIT}"
    exit 93
  fi
  if ! git cat-file -e "${PATCHED_COMMIT}^{commit}" >/dev/null 2>&1; then
    mark_eval_infra_failure "local repo is missing PATCHED_COMMIT ${PATCHED_COMMIT}"
    exit 94
  fi
}

apply_model_patch() {
  local patch_file="$1"
  if [ ! -s "${patch_file}" ]; then
    echo "Patch applied: false (empty model patch)." >&2
    return 20
  fi
  if git apply --whitespace=nowarn "${patch_file}"; then
    echo "Patch applied: true"
    return 0
  fi
  echo "Retrying git apply with --ignore-whitespace for normalized line endings." >&2
  if git apply --ignore-whitespace --whitespace=nowarn "${patch_file}"; then
    echo "Patch applied: true"
    return 0
  fi
  echo "Patch applied: false (git apply failed)." >&2
  return 21
}

checkout_files_from_selectors() {
  local commit="$1"
  shift
  local selector
  local file
  local files=()
  local seen=" "
  for selector in "$@"; do
    file="${selector%%::*}"
    if [ -n "${file}" ] && [[ "${seen}" != *" ${file} "* ]]; then
      files+=("${file}")
      seen+="${file} "
    fi
  done
  if [ "${#files[@]}" -gt 0 ]; then
    git checkout "${commit}" -- "${files[@]}"
  fi
}

require_local_repo
MODEL_PATCH_FILE= PREP_ONLY=1 /tmp/sample-run.sh base pass-pass
prep_status=$?
if [ "${prep_status}" -ne 0 ]; then
  mark_eval_infra_failure "sample prep failed before patch apply (exit ${prep_status})"
  exit "${prep_status}"
fi
cd "${REPO_DIR}"
apply_model_patch "${MODEL_PATCH_FILE}"
patch_status=$?
if [ "${patch_status}" -ne 0 ]; then
  exit "${patch_status}"
fi
echo "Running fail-pass tests..."
if ! checkout_files_from_selectors "${PATCHED_COMMIT}" ${FAIL_PASS_SUPPORT_FILES} ${FAIL_PASS_TESTS}; then
  mark_eval_infra_failure "failed to inject patched fail-pass test files"
  exit 90
fi
# shellcheck disable=SC2086
rm -f /tmp/quanbench-fail-pass-cases.json
QUANBENCH_CASE_REPORT=/tmp/quanbench-fail-pass-cases.json python -m pytest -q -p pytest_case_report ${FAIL_PASS_TESTS} || fail_pass_status=$?
emit_case_report fail_pass "${fail_pass_status}" /tmp/quanbench-fail-pass-cases.json
if [ -n "${PASS_PASS_TESTS}" ]; then
  echo "Running pass-pass tests..."
  if ! checkout_files_from_selectors "${BASE_COMMIT}" ${PASS_PASS_TESTS}; then
    mark_eval_infra_failure "failed to restore base pass-pass test files"
    exit 91
  fi
  if ! checkout_files_from_selectors "${PATCHED_COMMIT}" ${PATCHED_PASS_PASS_FILES}; then
    mark_eval_infra_failure "failed to restore corrected pass-pass test files"
    exit 91
  fi
  # shellcheck disable=SC2086
  rm -f /tmp/quanbench-pass-pass-cases.json
  QUANBENCH_CASE_REPORT=/tmp/quanbench-pass-pass-cases.json python -m pytest -q -p pytest_case_report ${PASS_PASS_TESTS} || pass_pass_status=$?
  emit_case_report pass_pass "${pass_pass_status}" /tmp/quanbench-pass-pass-cases.json
else
  echo "No pass-pass tests configured."
fi
if [ "${fail_pass_status}" -ne 0 ]; then
  exit "${fail_pass_status}"
fi
exit "${pass_pass_status}"
"""


PYTEST_SUMMARY_RE = re.compile(
    r"\b(?:passed|failed|error|errors|skipped|warning|warnings|xfailed|xpassed)\b.*\bin\s+[\d.]+s\b"
)
PYTEST_COUNT_RE = re.compile(
    r"(?P<count>\d+)\s+(?P<kind>subtests passed|subtests failed|passed|failed|errors?|skipped|warnings?|xfailed|xpassed)"
)
FAILED_TEST_RE = re.compile(r"^FAILED\s+(?P<nodeid>\S+)")
FAILURE_HEADING_RE = re.compile(r"^_+\s+(?P<case>.+?)\s+_+$")
PATCH_APPLIED_RE = re.compile(r"Patch applied:\s+(?P<value>true|false)")
EVAL_INFRA_FAILURE_RE = re.compile(r"Evaluator infrastructure failure:\s*(?P<reason>.*)")
GIT_INFRA_FAILURE_PATTERNS = (
    "GnuTLS",
    "TLS connection",
    "unable to access",
    "could not fetch",
    "promisor remote",
    "Could not resolve host",
    "Connection timed out",
    "RPC failed",
    "early EOF",
    "Evaluator offline mode",
    "missing local git repo",
    "missing BASE_COMMIT",
    "missing PATCHED_COMMIT",
)


def load_predictions(path: Path) -> dict[str, str]:
    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
        return {row["instance_id"]: row.get("model_patch", "") for row in rows}

    payload = read_json(path)
    if isinstance(payload, list):
        return {row["instance_id"]: row.get("model_patch", "") for row in payload}
    if isinstance(payload, dict):
        if isinstance(payload.get("predictions"), dict):
            payload = payload["predictions"]
        predictions = {}
        for key, value in payload.items():
            if key == "summary":
                continue
            if isinstance(value, dict):
                predictions[key] = value.get("model_patch", "")
            elif isinstance(value, str):
                predictions[key] = value
        return predictions
    raise TypeError(f"Unsupported predictions format: {path}")


PREDICTION_MODEL_NAME_KEYS = (
    "model_name_or_path",
    "model",
    "model_id",
    "llm",
)


def prediction_rows(path: Path) -> list[dict[str, Any]]:
    """Return prediction rows from supported preds.json/jsonl formats."""
    if path.suffix == ".jsonl":
        return [row for row in read_jsonl(path) if isinstance(row, dict)]

    payload = read_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows: list[dict[str, Any]] = []
        for key in PREDICTION_MODEL_NAME_KEYS:
            if payload.get(key):
                rows.append(payload)
                break
        predictions = payload.get("predictions")
        if isinstance(predictions, dict):
            rows.extend(
                row for row in predictions.values() if isinstance(row, dict)
            )
            return rows
        rows.extend(
            value
            for key, value in payload.items()
            if key != "summary" and isinstance(value, dict)
        )
        return rows
    return []


def load_prediction_model_name(path: Path) -> str:
    """Infer the model name stored by the agent runner, if available."""
    for row in prediction_rows(path):
        for key in PREDICTION_MODEL_NAME_KEYS:
            value = row.get(key)
            if value:
                return str(value)
    return ""


def embedded_agent_metrics(row: dict[str, Any]) -> dict[str, Any] | None:
    agent = row.get("agent") if isinstance(row.get("agent"), dict) else {}
    embedded = dict(agent)
    for key in (
        "patch_candidate_submitted",
        "patch_extraction_status",
        "patch_extraction_statuses",
    ):
        if key in row:
            embedded[key] = row[key]
    return embedded or None


def load_prediction_agent_metrics(path: Path) -> dict[str, dict[str, Any]]:
    """Load agent metrics embedded in predictions JSON/JSONL rows."""
    metrics: dict[str, dict[str, Any]] = {}

    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
        for row in rows:
            agent = embedded_agent_metrics(row)
            if agent is not None:
                metrics[row["instance_id"]] = normalize_agent_metrics(agent)
        return metrics

    payload = read_json(path)
    if isinstance(payload, list):
        for row in payload:
            agent = embedded_agent_metrics(row)
            if agent is not None:
                metrics[row["instance_id"]] = normalize_agent_metrics(agent)
    elif isinstance(payload, dict):
        if isinstance(payload.get("predictions"), dict):
            payload = payload["predictions"]
        for key, value in payload.items():
            if key == "summary":
                continue
            if isinstance(value, dict):
                agent = embedded_agent_metrics(value)
                if agent is not None:
                    metrics[key] = normalize_agent_metrics(agent)
    return metrics


def acr_extract_status_paths(
    *,
    run_dir: Path,
    instance_id: str,
    traj: dict[str, Any],
) -> list[Path]:
    candidates: list[Path] = []
    raw_output = traj.get("raw_output") if isinstance(traj.get("raw_output"), dict) else {}
    metrics = raw_output.get("metrics") if isinstance(raw_output, dict) else {}
    task_output_dir = metrics.get("task_output_dir") if isinstance(metrics, dict) else None
    if task_output_dir:
        candidates.append(Path(task_output_dir))

    acr_output_dir = run_dir / instance_id / "acr_output"
    if acr_output_dir.exists():
        candidates.extend(
            sorted(
                (path for path in acr_output_dir.glob(f"{instance_id}_*") if path.is_dir()),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        )

    status_paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.exists():
            continue
        for status_path in candidate.glob("**/extract_status.json"):
            resolved = status_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            status_paths.append(status_path)
    return status_paths


def acr_patch_attempt_metadata(
    *,
    run_dir: Path,
    instance_id: str,
    traj: dict[str, Any],
) -> dict[str, Any]:
    statuses: list[str] = []
    for status_path in acr_extract_status_paths(
        run_dir=run_dir,
        instance_id=instance_id,
        traj=traj,
    ):
        try:
            data = read_json(status_path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        statuses.extend(
            str(status)
            for status in data.get("extract_status", [])
            if isinstance(status, str)
        )

    if not statuses:
        return {}
    return patch_candidate_metadata(extraction_statuses=statuses)


def load_agent_metrics(predictions_path: Path) -> dict[str, dict[str, Any]]:
    """Load agent step and token metrics from sibling summary files."""
    metrics = load_prediction_agent_metrics(predictions_path)
    run_dir = predictions_path.parent
    if not run_dir.exists():
        return metrics

    summary_paths = sorted(run_dir.glob("*/*.summary.json"))
    for summary_path in summary_paths:
        instance_id = summary_path.parent.name
        try:
            summary = read_json(summary_path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(summary.get("agent"), dict):
            metrics[instance_id] = normalize_agent_metrics(summary["agent"])
            metrics[instance_id]["summary_path"] = str(summary_path)

    traj_paths = sorted(run_dir.glob("*/*.traj")) + sorted(run_dir.glob("*/*.traj.json"))
    for traj_path in traj_paths:
        instance_id = traj_path.parent.name
        try:
            traj = read_json(traj_path)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(traj.get("agent"), dict):
            metrics.setdefault(instance_id, normalize_agent_metrics(traj["agent"]))
            metrics[instance_id]["trajectory_path"] = str(traj_path)
            metrics[instance_id].update(
                acr_patch_attempt_metadata(
                    run_dir=run_dir,
                    instance_id=instance_id,
                    traj=traj,
                )
            )
            continue

        traj = traj.get("raw_output") or traj
        info = traj.get("info") or {}
        model_stats = info.get("model_stats") or {}
        prompt_tokens, completion_tokens = token_usage_from_traj(traj)
        token_by_step, cumulative_token_by_step = token_usage_by_step_from_traj(traj)
        response_steps = count_assistant_responses(traj)
        metrics.setdefault(instance_id, {})
        metrics[instance_id].update({
            # mini-SWE-agent steps are assistant responses. A single response may
            # contain multiple bash actions.
            "steps": response_steps
            if response_steps is not None
            else len(traj.get("trajectory") or []) or len(traj.get("messages") or []),
            "input_tokens": model_stats.get("input_tokens")
            or model_stats.get("tokens_sent")
            or prompt_tokens,
            "output_tokens": model_stats.get("output_tokens")
            or model_stats.get("tokens_received")
            or completion_tokens,
            "instance_cost": model_stats.get("instance_cost"),
            "exit_status": info.get("exit_status"),
            "trajectory_path": str(traj_path),
            "token_by_step": token_by_step,
            "cumulative_token_by_step": cumulative_token_by_step,
        })

    return metrics


def count_assistant_responses(traj: dict[str, Any]) -> int | None:
    """Count assistant model responses in a mini-SWE-agent trajectory."""
    messages = traj.get("messages")
    if not isinstance(messages, list):
        return None
    return sum(1 for message in messages if isinstance(message, dict) and message.get("role") == "assistant")


def token_usage_from_traj(traj: dict[str, Any]) -> tuple[int, int]:
    """Sum prompt/completion tokens from mini-swe-agent message responses."""
    records, _ = token_usage_by_step_from_traj(traj)
    totals = token_totals_from_records(records)
    return totals["input_tokens"], totals["output_tokens"]


def token_usage_by_step_from_traj(traj: dict[str, Any]) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    """Return per-assistant-response token usage for a mini-SWE-agent trajectory."""
    usages: list[dict[str, Any]] = []
    for message in traj.get("messages") or []:
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        response = ((message.get("extra") or {}).get("response") or {})
        usages.append(response.get("usage") or {})
    return token_records_from_usages(usages)


def _normalize_count_key(kind: str) -> str:
    return kind.replace(" ", "_").rstrip("s") if kind != "subtests passed" else "subtests_passed"


def parse_pytest_output(output: str) -> dict[str, Any]:
    """Extract structured pytest details from the evaluator stdout."""
    sections: dict[str, list[str]] = {"fail_pass": [], "pass_pass": []}
    current: str | None = None
    pass_pass_configured = "Running pass-pass tests..." in output or "Running regression tests..." in output

    for line in output.splitlines():
        if line in {"Running fail-pass tests...", "Running primary tests..."}:
            current = "fail_pass"
            continue
        if line in {"Running pass-pass tests...", "Running regression tests..."}:
            current = "pass_pass"
            continue
        if line in {"No pass-pass tests configured.", "No regression tests configured."}:
            current = None
            continue
        if current is not None:
            sections[current].append(line)

    return {
        "fail_pass": parse_pytest_section(sections["fail_pass"], ran=bool(sections["fail_pass"])),
        "pass_pass": parse_pytest_section(sections["pass_pass"], ran=pass_pass_configured),
    }


def parse_patch_applied(output: str) -> bool | None:
    """Return whether the model patch was applied before tests ran."""
    match = PATCH_APPLIED_RE.search(output)
    if not match:
        return None
    return match.group("value") == "true"


def parse_eval_infra_failure(
    output: str, patch_applied: bool | None, returncode: int | None = None,
) -> str | None:
    """Return an evaluator infrastructure failure reason, if one is visible."""
    match = EVAL_INFRA_FAILURE_RE.search(output)
    if match:
        return match.group("reason").strip() or "evaluator infrastructure failure"
    if patch_applied is None and returncode in {125, 126, 127}:
        return f"Docker failed before evaluation started (exit {returncode})"
    if patch_applied is None and any(pattern in output for pattern in GIT_INFRA_FAILURE_PATTERNS):
        return "git setup failed before model patch application"
    return None


def parse_pytest_section(lines: list[str], *, ran: bool) -> dict[str, Any]:
    summary_line = None
    for line in reversed(lines):
        normalized = line.strip("= ")
        if PYTEST_SUMMARY_RE.search(normalized):
            summary_line = normalized
            break

    counts: dict[str, int] = {}
    if summary_line:
        for match in PYTEST_COUNT_RE.finditer(summary_line):
            key = _normalize_count_key(match.group("kind"))
            counts[key] = counts.get(key, 0) + int(match.group("count"))

    failed_tests = [
        match.group("nodeid")
        for line in lines
        if (match := FAILED_TEST_RE.match(line.strip()))
    ]
    failure_cases = []
    for line in lines:
        match = FAILURE_HEADING_RE.match(line.strip())
        if match and re.search(r"[A-Za-z0-9]", match.group("case")):
            failure_cases.append(match.group("case"))

    if not ran:
        status = "not_run"
    elif counts.get("failed", 0) or counts.get("error", 0) or counts.get("errors", 0):
        status = "failed"
    elif summary_line:
        status = "passed"
    else:
        status = "unknown"

    return {
        "status": status,
        "summary_line": summary_line,
        "counts": counts,
        "failed_tests": failed_tests,
        "failure_cases": failure_cases,
    }


def selector_count(sample: dict[str, Any], section: str) -> int:
    legacy_section = {"fail_pass": "primary", "pass_pass": "regression"}.get(section)
    validation = sample.get("validation", {}).get("patched", {})
    if section in validation:
        return len(validation.get(section, {}).get("file_list", []))
    if legacy_section:
        return len(validation.get(legacy_section, {}).get("file_list", []))
    return len(
        validation.get(section, {}).get("file_list", [])
    )


def selectors_from_sample(sample: dict[str, Any], section: str) -> list[str]:
    legacy_section = {"fail_pass": "primary", "pass_pass": "regression"}.get(section)
    validation = sample.get("validation", {}).get("patched", {})
    if section in validation:
        return list(validation.get(section, {}).get("file_list", []))
    if legacy_section and legacy_section in validation:
        return list(validation.get(legacy_section, {}).get("file_list", []))
    return list(validation.get(section, {}).get("file_list", []))


def test_pass_fraction(test_section: dict[str, Any], expected_total: int) -> dict[str, Any]:
    counts = test_section.get("counts") or {}
    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0)
    observed_total = passed + failed
    total = observed_total or expected_total
    if test_section.get("status") == "passed" and passed == 0 and total:
        passed = total
    return {
        "passed": passed,
        "total": total,
        "summary": f"{passed}/{total}" if total else "0/0",
        "status": test_section.get("status"),
    }


def attach_pass_fractions(
    sample: dict[str, Any],
    result: dict[str, Any],
    tests: dict[str, Any],
) -> dict[str, Any]:
    result["fail_pass"] = test_pass_fraction(
        tests.get("fail_pass", {}),
        selector_count(sample, "fail_pass"),
    )
    result["pass_pass"] = test_pass_fraction(
        tests.get("pass_pass", {}),
        selector_count(sample, "pass_pass"),
    )
    return result


def aggregate_test_fraction(run_results: list[dict[str, Any]], section: str) -> dict[str, Any]:
    """Summarize repeated test runs conservatively.

    A section is considered passed only if it passed in every run. The passed
    count is the minimum observed pass count so flaky partial failures cannot
    inflate the aggregate summary.
    """
    fractions = [result.get(section) or {} for result in run_results]
    totals = [fraction.get("total") or 0 for fraction in fractions]
    passed_counts = [fraction.get("passed") or 0 for fraction in fractions]
    total = max(totals, default=0)
    passed = min(passed_counts, default=0)
    statuses = [fraction.get("status") for fraction in fractions]
    if statuses and all(status == "passed" for status in statuses):
        status = "passed"
    elif any(status == "failed" for status in statuses):
        status = "failed"
    elif any(status == "unknown" for status in statuses):
        status = "unknown"
    else:
        status = statuses[0] if statuses else "not_run"
    return {
        "passed": passed,
        "total": total,
        "summary": f"{passed}/{total}" if total else "0/0",
        "status": status,
    }


def aggregate_structured_test_cases(
    run_results: list[dict[str, Any]], section: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Count a selected test as passed only when it passed in every run."""
    case_runs = [result["test_cases"][section] for result in run_results]
    selectors = [case["selector"] for case in case_runs[0]]
    if any([case["selector"] for case in cases] != selectors for cases in case_runs):
        raise ValueError(f"Repeated runs have different selected {section} test cases")
    if not selectors:
        return (
            {"passed": 0, "total": 0, "summary": "0/0", "status": "not_applicable", "counts": {}},
            [],
        )
    cases = []
    for index, selector in enumerate(selectors):
        run_cases = [run[index] for run in case_runs]
        statuses = [case["status"] for case in run_cases]
        if all(status == "passed" for status in statuses):
            status = "passed"
        elif "failed" in statuses:
            status = "failed"
        elif "not_collected" in statuses:
            status = "not_collected"
        elif "skipped" in statuses:
            status = "skipped"
        else:
            status = "not_run"
        phase = next((case["phase"] for case in run_cases if case["status"] == status), "")
        cases.append({
            "selector": selector,
            "status": status,
            "phase": phase,
            "run_statuses": statuses,
        })
    counts = {status: sum(case["status"] == status for case in cases)
              for status in ("passed", "failed", "skipped", "not_run", "not_collected")}
    passed = counts["passed"]
    run_statuses = [result[section]["status"] for result in run_results]
    status = (
        "passed" if passed == len(cases) and all(value == "passed" for value in run_statuses)
        else "failed" if "failed" in run_statuses or counts["failed"]
        else "unknown"
    )
    return (
        {"passed": passed, "total": len(cases), "summary": f"{passed}/{len(cases)}",
         "status": status, "counts": counts, "run_statuses": run_statuses},
        cases,
    )


def aggregate_repeated_results(
    sample_id: str,
    run_results: list[dict[str, Any]],
    agent_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the stable top-level result from repeated evaluator runs."""
    resolved_runs = sum(1 for result in run_results if result.get("resolved"))
    stable_runs = len(run_results)
    patch_values = [
        result.get("patch_applied")
        for result in run_results
        if result.get("patch_applied") is not None
    ]
    patch_applied = None if not patch_values else all(bool(value) for value in patch_values)
    nonzero_returncodes = [
        result.get("returncode")
        for result in run_results
        if result.get("returncode") not in (0, None)
    ]
    returncode = 0 if resolved_runs == stable_runs else (nonzero_returncodes[0] if nonzero_returncodes else -1)
    timed_out = any(bool(result.get("timed_out")) for result in run_results)
    eval_infra_failures = [
        result.get("eval_infra_failure")
        for result in run_results
        if result.get("eval_infra_failed")
    ]
    stdout = "\n".join(
        f"===== evaluation run {index + 1}/{stable_runs} =====\n{result.get('stdout', '')}"
        for index, result in enumerate(run_results)
    )
    stderr = "\n".join(
        f"===== evaluation run {index + 1}/{stable_runs} =====\n{result.get('stderr', '')}"
        for index, result in enumerate(run_results)
        if result.get("stderr")
    )
    structured = all("test_cases" in result for result in run_results)
    if structured:
        fail_fraction, fail_cases = aggregate_structured_test_cases(run_results, "fail_pass")
        pass_fraction, pass_cases = aggregate_structured_test_cases(run_results, "pass_pass")
    else:
        fail_fraction = aggregate_test_fraction(run_results, "fail_pass")
        pass_fraction = aggregate_test_fraction(run_results, "pass_pass")
    return {
        "instance_id": sample_id,
        "resolved": stable_runs > 0 and resolved_runs == stable_runs,
        "resolved_runs": resolved_runs,
        "returncode": returncode,
        "returncodes": [result.get("returncode") for result in run_results],
        "patch_applied": patch_applied,
        "eval_infra_failed": bool(eval_infra_failures),
        "eval_infra_failures": eval_infra_failures,
        "eval_infra_failure": eval_infra_failures[0] if eval_infra_failures else None,
        "agent": agent_metrics or {},
        "fail_pass": fail_fraction,
        "pass_pass": pass_fraction,
        **({"test_cases": {"fail_pass": fail_cases, "pass_pass": pass_cases}} if structured else {}),
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "eval_runs": run_results,
    }


def sample_files(samples_dir: Path, instance_filter: str | None = None) -> list[Path]:
    index_path = samples_dir / "index.json"
    if index_path.exists():
        index = read_json(index_path)
        files = [
            samples_dir / item["sample_path"] / "sample.json"
            for item in index.get("samples", [])
        ]
    else:
        files = sorted(samples_dir.rglob("sample.json"))
    if instance_filter is None:
        return files
    return [path for path in files if instance_filter in str(path.parent.relative_to(samples_dir))]


def sample_repo_metadata(sample_path: Path) -> dict[str, str]:
    sample = read_json(sample_path)
    return {
        "repo_slug": sample_path.parent.parent.name,
        "repo_full": sample["instance"]["repo"],
    }


def build_repo_summary(
    completed_results: list[dict[str, Any]],
    sample_metadata_by_id: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for result in completed_results:
        metadata = sample_metadata_by_id.get(result["instance_id"])
        if not metadata:
            continue
        repo_slug = metadata["repo_slug"]
        repo_summary = summary.setdefault(
            repo_slug,
            {
                "repo": metadata["repo_full"],
                "resolved": 0,
                "total": 0,
            },
        )
        repo_summary["total"] += 1
        repo_summary["resolved"] += int(bool(result.get("resolved")))

    for repo_summary in summary.values():
        total = repo_summary["total"]
        resolved = repo_summary["resolved"]
        rate = resolved / total if total else 0.0
        repo_summary["resolve_rate"] = rate

    return dict(sorted(summary.items()))


def build_eval_script(sample_path: Path) -> str:
    run_sh_path = sample_path.parent / "run.sh"
    if not run_sh_path.exists():
        raise FileNotFoundError(f"Missing run.sh next to sample: {sample_path}")
    run_sh = run_sh_path.read_text(encoding="utf-8").rstrip() + "\n"
    sample = read_json(sample_path)
    resources = sample.get("evaluation_resources", {})
    support = resources.get("patched_f2p_support_files", [])
    regression = resources.get("patched_p2p_test_files", [])
    selected_p2p_files = {s.split("::")[0] for s in selectors_from_sample(sample, "pass_pass")}
    if not set(regression) <= selected_p2p_files:
        raise ValueError("Corrected P2P files must belong to the selected test suite")
    for file in [*support, *regression]:
        path = Path(file)
        if path.is_absolute() or ".." in path.parts or path.parts[0] not in {"test", "tests"}:
            raise ValueError(f"Evaluation resources must be repository test files: {file}")
    resource_config = (
        'FAIL_PASS_SUPPORT_FILES="$FAIL_PASS_SUPPORT_FILES "' + shlex.quote(" ".join(support))
        + "\nPATCHED_PASS_PASS_FILES=" + shlex.quote(" ".join(regression))
    )
    # Parameterized nodeids may contain spaces or shell metacharacters.
    # Keep each selector as one argument for both Git checkout and pytest.
    for suite, variable in (("fail_pass", "FAIL_PASS_TEST_ITEMS"), ("pass_pass", "PASS_PASS_TEST_ITEMS")):
        resource_config += "\n" + variable + "=(" + " ".join(
            shlex.quote(s) for s in selectors_from_sample(sample, suite)
        ) + ")"
    plugin_path = Path(__file__).with_name("pytest_case_report.py")
    plugin = plugin_path.read_text(encoding="utf-8").rstrip() + "\n"
    script = (
        EVAL_SCRIPT_TEMPLATE
        .replace("__EVALUATION_RESOURCE_CONFIG__", resource_config)
        .replace("__RUN_SH_CONTENT__", run_sh)
        .replace("__PYTEST_CASE_REPORT_PLUGIN__", plugin)
    )
    test_workdir = sample.get("runtime", {}).get("environment", {}).get("test_workdir")
    if test_workdir:
        relative = Path(test_workdir)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Test working directory must be repository-relative")
        for suite, variable in (("fail_pass", "FAIL_PASS_TESTS"), ("pass_pass", "PASS_PASS_TESTS")):
            selectors = " ".join(shlex.quote("/workspace/repo/" + s) for s in selectors_from_sample(sample, suite))
            invocation = "python -m pytest -q -p pytest_case_report ${" + variable + "}"
            replacement = "QUANBENCH_CASE_ROOT=/workspace/repo bash -c " + shlex.quote(
                "cd " + shlex.quote("/workspace/repo/" + test_workdir)
                + " && python -m pytest -q -p pytest_case_report --rootdir=/workspace/repo "
                + selectors
            )
            script = script.replace(invocation, replacement)
    return script.replace(' ${FAIL_PASS_TESTS}', ' "${FAIL_PASS_TEST_ITEMS[@]}"').replace(
        ' ${PASS_PASS_TESTS}', ' "${PASS_PASS_TEST_ITEMS[@]}"'
    )


def cleanup_docker_container(container_name: str) -> str:
    """Force-remove a named evaluator container after a subprocess timeout."""
    completed = subprocess.run(
        ["docker", "rm", "-f", container_name],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    if completed.returncode == 0:
        return f"Removed evaluator container {container_name} after timeout."
    return f"Failed to remove evaluator container {container_name}: {output.strip()}"


def _evaluate_one_run_once(
    sample_path: Path,
    model_patch: str,
    timeout: int,
    agent_metrics: dict[str, Any] | None = None,
    run_index: int = 1,
    total_runs: int = 1,
    eval_attempt: int = 1,
) -> dict[str, Any]:
    sample = read_json(sample_path)
    sample_id = sample["instance"]["instance_id"]
    image = sample["runtime"]["docker"]["image"]
    base_commit = sample["instance"]["base_commit"]
    patched_commit = sample["instance"]["patch"]
    fail_pass_tests = " ".join(selectors_from_sample(sample, "fail_pass"))
    pass_pass_tests = " ".join(selectors_from_sample(sample, "pass_pass"))
    eval_script = build_eval_script(sample_path)
    container_name = f"quanbench-eval-{sample_id}-{run_index}-{eval_attempt}-{uuid.uuid4().hex[:8]}"
    command = [
        "docker",
        "run",
        "--platform",
        sample.get("runtime", {}).get("docker", {}).get("platform", "linux/amd64"),
        "--name",
        container_name,
        "--rm",
        "--network",
        "none",
        "-i",
        "--entrypoint",
        "bash",
        "-e",
        f"BASE_COMMIT={base_commit}",
        "-e",
        f"PATCHED_COMMIT={patched_commit}",
        "-e",
        f"FAIL_PASS_TEST_PATHS={fail_pass_tests}",
        "-e",
        f"PASS_PASS_TEST_PATHS={pass_pass_tests}",
        image,
        "-lc",
        eval_script,
    ]

    timed_out = False
    try:
        completed = subprocess.run(
            command,
            input=model_patch,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        stdout += f"\nEvaluator timed out after {timeout} seconds.\n"
        stdout += cleanup_docker_container(container_name) + "\n"
        returncode = -1
    case_reports = extract_case_reports(stdout)
    fail_fraction, fail_cases = summarize_structured_suite(
        selectors_from_sample(sample, "fail_pass"), case_reports.get("fail_pass")
    )
    pass_fraction, pass_cases = summarize_structured_suite(
        selectors_from_sample(sample, "pass_pass"), case_reports.get("pass_pass")
    )
    combined_output = f"{stdout}\n{stderr}"
    patch_applied = parse_patch_applied(combined_output)
    eval_infra_failure = parse_eval_infra_failure(combined_output, patch_applied, returncode)
    result = {
        "instance_id": sample_id,
        "resolved": (
            returncode == 0
            and fail_fraction["status"] == "passed"
            and pass_fraction["status"] in {"passed", "not_applicable"}
        ),
        "returncode": returncode,
        "patch_applied": patch_applied,
        "eval_infra_failed": eval_infra_failure is not None,
        "eval_infra_failure": eval_infra_failure,
        "agent": agent_metrics or {},
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "run_index": run_index,
        "eval_attempt": eval_attempt,
        "fail_pass": fail_fraction,
        "pass_pass": pass_fraction,
        "test_cases": {"fail_pass": fail_cases, "pass_pass": pass_cases},
        "pytest_case_reports": case_reports,
    }
    return result


def evaluate_one_run(
    sample_path: Path,
    model_patch: str,
    timeout: int,
    agent_metrics: dict[str, Any] | None = None,
    run_index: int = 1,
    total_runs: int = 1,
    setup_retries: int = 0,
) -> dict[str, Any]:
    attempts = max(1, setup_retries + 1)
    last_result: dict[str, Any] | None = None
    sample_id = read_json(sample_path)["instance"]["instance_id"]
    for eval_attempt in range(1, attempts + 1):
        result = _evaluate_one_run_once(
            sample_path,
            model_patch,
            timeout=timeout,
            agent_metrics=agent_metrics,
            run_index=run_index,
            total_runs=total_runs,
            eval_attempt=eval_attempt,
        )
        last_result = result
        if not result.get("eval_infra_failed"):
            return result
        if eval_attempt < attempts:
            reason = result.get("eval_infra_failure") or "unknown infrastructure failure"
            print(
                f"[{sample_id}] evaluator infrastructure failure on attempt "
                f"{eval_attempt}/{attempts}: {reason}; retrying",
                flush=True,
            )
    assert last_result is not None
    return last_result


def evaluate_one(
    sample_path: Path,
    model_patch: str,
    timeout: int,
    agent_metrics: dict[str, Any] | None = None,
    stable_runs: int = 1,
    setup_retries: int = 0,
) -> dict[str, Any]:
    sample_id = read_json(sample_path)["instance"]["instance_id"]
    stable_runs = max(1, stable_runs)
    run_results = [
        evaluate_one_run(
            sample_path,
            model_patch,
            timeout=timeout,
            agent_metrics=agent_metrics,
            run_index=run_index,
            total_runs=stable_runs,
            setup_retries=setup_retries,
        )
        for run_index in range(1, stable_runs + 1)
    ]
    if stable_runs == 1:
        return run_results[0]
    return aggregate_repeated_results(sample_id, run_results, agent_metrics)


def build_evaluation_payload(
    *,
    results: list[dict[str, Any] | None],
    predictions: dict[str, str],
    sample_metadata_by_id: dict[str, dict[str, Any]],
    expected_total: int,
    model_name_or_path: str = "",
) -> dict[str, Any]:
    completed_results = [result for result in results if result is not None]
    agent_totals = {
        "total_steps": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cached_input_tokens": 0,
        "total_cache_creation_input_tokens": 0,
    }
    for result in completed_results:
        agent = normalize_agent_metrics(result.get("agent") or {})
        agent_totals["total_steps"] += agent.get("steps") or 0
        agent_totals["total_input_tokens"] += agent.get("input_tokens") or 0
        agent_totals["total_output_tokens"] += agent.get("output_tokens") or 0
        agent_totals["total_cached_input_tokens"] += agent.get("cached_input_tokens") or 0
        agent_totals["total_cache_creation_input_tokens"] += (
            agent.get("cache_creation_input_tokens") or 0
        )
    total_cost = estimated_cost_usd(
        model_name_or_path,
        {
            "input_tokens": agent_totals["total_input_tokens"],
            "cached_input_tokens": agent_totals["total_cached_input_tokens"],
            "cache_creation_input_tokens": agent_totals[
                "total_cache_creation_input_tokens"
            ],
            "output_tokens": agent_totals["total_output_tokens"],
        },
    )
    if total_cost is not None:
        agent_totals["total_cost"] = round(total_cost, 6)
        agent_totals["avg_cost"] = round(
            total_cost / len(completed_results), 6
        ) if completed_results else 0

    predicted_results = [
        result for result in completed_results if not result.get("missing_prediction")
    ]
    for result in predicted_results:
        model_patch = predictions.get(result["instance_id"], "")
        agent = result.get("agent") or {}
        prediction_status_row = {"model_patch": model_patch, "_agent": agent}
        result["agent_submitted"] = bool(result.get("agent_submitted")) or row_submitted(
            prediction_status_row
        )
        result["agent_step_exhausted"] = row_step_exhausted(prediction_status_row)
        result["agent_repeated_command_loop"] = row_repeated_command_loop(prediction_status_row)

    agent_submitted = sum(1 for result in predicted_results if result.get("agent_submitted"))
    agent_step_exhausted = sum(
        1 for result in predicted_results if result.get("agent_step_exhausted")
    )
    agent_repeated_command_loop = sum(
        1 for result in predicted_results if result.get("agent_repeated_command_loop")
    )
    submitted_results = [result for result in predicted_results if result.get("agent_submitted")]
    patch_applied = sum(1 for result in submitted_results if result.get("patch_applied") is True)
    fail_pass_total = sum(
        (result.get("fail_pass") or {}).get("total") or 0 for result in predicted_results
    )
    fail_pass_passed = sum(
        (result.get("fail_pass") or {}).get("passed") or 0 for result in predicted_results
    )
    pass_pass_total = sum(
        (result.get("pass_pass") or {}).get("total") or 0 for result in predicted_results
    )
    pass_pass_passed = sum(
        (result.get("pass_pass") or {}).get("passed") or 0 for result in predicted_results
    )

    summary = {
        "total": len(completed_results),
        "pending": max(0, expected_total - len(completed_results)),
        "submitted": agent_submitted,
        "step_exhausted": agent_step_exhausted,
        "repeated_command_loop": agent_repeated_command_loop,
        "patch_applied": patch_applied,
        "timed_out": sum(1 for result in predicted_results if result.get("timed_out")),
        "resolved": sum(1 for result in completed_results if result.get("resolved")),
        "missing_predictions": sum(
            1 for result in completed_results if result.get("missing_prediction")
        ),
        "fail_pass": {
            "passed": fail_pass_passed,
            "total": fail_pass_total,
            "summary": f"{fail_pass_passed}/{fail_pass_total}" if fail_pass_total else "0/0",
        },
        "pass_pass": {
            "passed": pass_pass_passed,
            "total": pass_pass_total,
            "summary": f"{pass_pass_passed}/{pass_pass_total}" if pass_pass_total else "0/0",
        },
        **agent_totals,
        "per_repo": build_repo_summary(completed_results, sample_metadata_by_id),
    }
    return sanitize_result_payload({"summary": summary, "results": completed_results})


def write_progress_payload(
    *,
    output_path: Path,
    results: list[dict[str, Any] | None],
    predictions: dict[str, str],
    sample_metadata_by_id: dict[str, dict[str, Any]],
    expected_total: int,
    model_name_or_path: str = "",
    final: bool = False,
) -> dict[str, Any]:
    payload = build_evaluation_payload(
        results=results,
        predictions=predictions,
        sample_metadata_by_id=sample_metadata_by_id,
        expected_total=expected_total,
        model_name_or_path=model_name_or_path,
    )
    target_path = output_path if final else output_path.with_suffix(output_path.suffix + ".partial")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if final:
        partial_path = output_path.with_suffix(output_path.suffix + ".partial")
        if partial_path.exists():
            try:
                partial_path.unlink()
            except OSError as exc:
                print(f"Warning: failed to remove partial result {partial_path}: {exc}", flush=True)
    return payload


def print_progress(
    *,
    results: list[dict[str, Any] | None],
    expected_total: int,
    latest: str,
) -> None:
    completed = [result for result in results if result is not None]
    predicted = [result for result in completed if not result.get("missing_prediction")]
    resolved = sum(1 for result in completed if result.get("resolved"))
    timed_out = sum(1 for result in predicted if result.get("timed_out"))
    patch_failed = sum(1 for result in predicted if result.get("patch_applied") is False)
    infra_failed = sum(1 for result in predicted if result.get("eval_infra_failed"))
    print(
        "[progress] "
        f"{len(completed)}/{expected_total} done, "
        f"pending {max(0, expected_total - len(completed))}, "
        f"resolved {resolved}, timed_out {timed_out}, "
        f"patch_apply_failed {patch_failed}, eval_infra_failed {infra_failed}; "
        f"latest={latest}",
        flush=True,
    )


def prediction_status_row(
    predictions: dict[str, str],
    agent_metrics_by_id: dict[str, dict[str, Any]],
    sample_id: str,
) -> dict[str, Any]:
    return {
        "model_patch": predictions.get(sample_id, ""),
        "_agent": agent_metrics_by_id.get(sample_id, {}),
    }


def prediction_has_evaluable_patch(
    predictions: dict[str, str],
    agent_metrics_by_id: dict[str, dict[str, Any]],
    sample_id: str,
) -> bool:
    row = prediction_status_row(predictions, agent_metrics_by_id, sample_id)
    return (
        not row_step_exhausted(row)
        and not row_repeated_command_loop(row)
        and not row_timed_out(row)
        and has_nonempty_patch(row.get("model_patch"))
    )


def prediction_has_patch_candidate(
    predictions: dict[str, str],
    agent_metrics_by_id: dict[str, dict[str, Any]],
    sample_id: str,
) -> bool:
    row = prediction_status_row(predictions, agent_metrics_by_id, sample_id)
    agent = agent_metrics_by_id.get(sample_id, {})
    return (
        not row_step_exhausted(row)
        and not row_repeated_command_loop(row)
        and not row_timed_out(row)
        and (
            row_submitted(row)
            or bool(agent.get("patch_candidate_submitted"))
        )
    )


def skipped_unsubmitted_result(
    predictions: dict[str, str],
    agent_metrics_by_id: dict[str, dict[str, Any]],
    sample_id: str,
) -> dict[str, Any]:
    agent = agent_metrics_by_id.get(sample_id, {})
    row = prediction_status_row(predictions, agent_metrics_by_id, sample_id)
    return {
        "instance_id": sample_id,
        "resolved": False,
        "returncode": None,
        "patch_applied": None,
        "eval_infra_failed": False,
        "eval_infra_failure": None,
        "agent": agent,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "agent_submitted": False,
        "agent_step_exhausted": row_step_exhausted(row),
        "agent_repeated_command_loop": row_repeated_command_loop(row),
        "skipped_evaluation": True,
        "skip_reason": "not_submitted",
    }


def skipped_unapplicable_patch_result(
    agent_metrics_by_id: dict[str, dict[str, Any]],
    sample_id: str,
) -> dict[str, Any]:
    agent = agent_metrics_by_id.get(sample_id, {})
    return {
        "instance_id": sample_id,
        "resolved": False,
        "returncode": None,
        "patch_applied": False,
        "eval_infra_failed": False,
        "eval_infra_failure": None,
        "agent": agent,
        "stdout": "Patch applied: false (patch candidate was not extractable as an evaluable diff).\n",
        "stderr": "",
        "timed_out": False,
        "agent_submitted": True,
        "agent_step_exhausted": False,
        "agent_repeated_command_loop": False,
        "skipped_evaluation": True,
        "skip_reason": "patch_not_extractable",
        "patch_extraction_status": agent.get("patch_extraction_status"),
    }


def attach_unrun_test_cases(sample_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Preserve selected testcase identities when no patch reaches pytest."""
    sample = read_json(sample_path)
    fail_fraction, fail_cases = summarize_structured_suite(
        selectors_from_sample(sample, "fail_pass"), None
    )
    pass_fraction, pass_cases = summarize_structured_suite(
        selectors_from_sample(sample, "pass_pass"), None
    )
    result["fail_pass"] = fail_fraction
    result["pass_pass"] = pass_fraction
    result["test_cases"] = {"fail_pass": fail_cases, "pass_pass": pass_cases}
    result["pytest_case_reports"] = {}
    return result


def evaluate_predictions(
    predictions_path: Path,
    samples_dir: Path,
    output_path: Path,
    timeout: int,
    instance_filter: str | None = None,
    workers: int = 1,
    stable_runs: int = 1,
    setup_retries: int = 2,
    resume: bool = False,
) -> dict[str, Any]:
    predictions = load_predictions(predictions_path)
    model_name_or_path = load_prediction_model_name(predictions_path)
    agent_metrics_by_id = load_agent_metrics(predictions_path)
    sample_paths = [
        sample_path
        for sample_path in sample_files(samples_dir, instance_filter=instance_filter)
        if read_json(sample_path)["instance"]["instance_id"] in predictions
    ]
    sample_metadata_by_id = {
        read_json(sample_path)["instance"]["instance_id"]: sample_repo_metadata(sample_path)
        for sample_path in sample_paths
    }
    results: list[dict[str, Any] | None] = [None] * len(sample_paths)
    restored = 0
    if resume:
        partial_path = output_path.with_suffix(output_path.suffix + ".partial")
        if partial_path.exists():
            saved = read_json(partial_path)
            by_id = {
                read_json(path)["instance"]["instance_id"]: index
                for index, path in enumerate(sample_paths)
            }
            for result in saved.get("results", []):
                sample_id = result.get("instance_id")
                if sample_id not in by_id or "test_cases" not in result:
                    raise ValueError(f"Partial result is incompatible with selected samples: {sample_id}")
                if result.get("timed_out") or result.get("eval_infra_failed"):
                    continue
                # A result from fewer validations cannot satisfy a larger
                # repeat budget merely because the sample already completed.
                if not result.get("skipped_evaluation"):
                    completed_runs = evaluation_repeat_metadata(result)["evaluation_repeats"]
                    if completed_runs != max(1, stable_runs):
                        continue
                index = by_id[sample_id]
                if results[index] is not None:
                    raise ValueError(f"Duplicate sample in partial result: {sample_id}")
                results[index] = result
                restored += 1
            print(f"[resume] restored {restored} completed samples from {partial_path}", flush=True)
    work_items: list[tuple[int, Path, str]] = []
    unapplicable_patch_candidates = 0

    for index, sample_path in enumerate(sample_paths):
        if results[index] is not None:
            continue
        sample_id = read_json(sample_path)["instance"]["instance_id"]
        if prediction_has_evaluable_patch(predictions, agent_metrics_by_id, sample_id):
            work_items.append((index, sample_path, sample_id))
            continue
        if prediction_has_patch_candidate(predictions, agent_metrics_by_id, sample_id):
            unapplicable_patch_candidates += 1
            results[index] = attach_unrun_test_cases(
                sample_path,
                skipped_unapplicable_patch_result(agent_metrics_by_id, sample_id),
            )
            continue
        else:
            results[index] = attach_unrun_test_cases(
                sample_path,
                skipped_unsubmitted_result(predictions, agent_metrics_by_id, sample_id),
            )
            continue

    print(
        "[progress] "
        f"will evaluate {len(work_items)} submitted predictions; "
        f"reusing {restored} completed samples; "
        f"marking {unapplicable_patch_candidates} submitted candidates as not applied; "
        f"skipping {sum(bool(result and result.get('skipped_evaluation') and not result.get('agent_submitted')) for result in results)} "
        "not-submitted predictions",
        flush=True,
    )

    if workers <= 1 or len(work_items) <= 1:
        for index, sample_path, sample_id in work_items:
            results[index] = evaluate_one(
                sample_path,
                predictions[sample_id],
                timeout=timeout,
                agent_metrics=agent_metrics_by_id.get(sample_id),
                stable_runs=stable_runs,
                setup_retries=setup_retries,
            )
            print_progress(results=results, expected_total=len(sample_paths), latest=sample_id)
            write_progress_payload(
                output_path=output_path,
                results=results,
                predictions=predictions,
                sample_metadata_by_id=sample_metadata_by_id,
                expected_total=len(sample_paths),
                model_name_or_path=model_name_or_path,
            )
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(
                    evaluate_one,
                    sample_path,
                    predictions[sample_id],
                    timeout,
                    agent_metrics_by_id.get(sample_id),
                    stable_runs,
                    setup_retries,
                ): index
                for index, sample_path, sample_id in work_items
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                results[index] = future.result()
                latest = results[index].get("instance_id", f"index:{index}")
                print_progress(results=results, expected_total=len(sample_paths), latest=latest)
                write_progress_payload(
                    output_path=output_path,
                    results=results,
                    predictions=predictions,
                    sample_metadata_by_id=sample_metadata_by_id,
                    expected_total=len(sample_paths),
                    model_name_or_path=model_name_or_path,
                )

    payload = write_progress_payload(
        output_path=output_path,
        results=results,
        predictions=predictions,
        sample_metadata_by_id=sample_metadata_by_id,
        expected_total=len(sample_paths),
        model_name_or_path=model_name_or_path,
        final=True,
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate agent preds.json/jsonl on benchmark samples.")
    parser.add_argument("predictions", type=Path, help="Agent preds.json or all_preds.jsonl path.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--filter", help="Evaluate only one instance id.")
    parser.add_argument("--resume", action="store_true", help="Reuse completed samples from the output .partial file; rerun timeouts and infrastructure failures.")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of samples to evaluate in parallel. Default: 1.",
    )
    parser.add_argument(
        "--stable-runs",
        type=int,
        default=1,
        help="Number of evaluator runs required for a sample to count as resolved. Default: 1.",
    )
    parser.add_argument(
        "--setup-retries",
        type=int,
        default=0,
        help=(
            "Retry evaluator infrastructure/setup failures before counting the sample result. "
            "Default: 0."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = evaluate_predictions(
        args.predictions,
        args.samples_dir,
        args.output,
        timeout=args.timeout,
        instance_filter=args.filter,
        workers=args.workers,
        stable_runs=args.stable_runs,
        setup_retries=args.setup_retries,
        resume=args.resume,
    )
    summary = payload["summary"]
    print(
        "Agent submitted "
        f"{summary['submitted']}/{summary['total']} instances; "
        f"step exhausted {summary['step_exhausted']}/{summary['total']}; "
        f"repeated command loop {summary['repeated_command_loop']}/{summary['total']}; "
        f"patch applied {summary['patch_applied']}/{summary['submitted']}; "
        f"resolved {summary['resolved']}/{summary['total']}. "
        f"Results written to {args.output}"
    )


if __name__ == "__main__":
    main()
