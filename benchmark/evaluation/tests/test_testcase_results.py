"""Contract tests for machine-readable testcase capture and suite aggregation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from benchmark.evaluation.common.testcase_results import (
    BEGIN, END, extract_case_reports, summarize_structured_suite,
)
from benchmark.evaluation.scripts.evaluate_agent_preds import (
    aggregate_structured_test_cases,
    attach_unrun_test_cases,
)


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "scripts"


def run_pytest(tmp_path: Path, source: str, selectors: list[str]):
    test_file = tmp_path / "test_example.py"
    test_file.write_text(source)
    report_path = tmp_path / "cases.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PLUGIN_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["QUANBENCH_CASE_REPORT"] = str(report_path)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "pytest_case_report", *selectors],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert report_path.exists(), completed.stderr
    report = json.loads(report_path.read_text())
    return completed.returncode, report


def test_exact_case_outcomes_include_setup_skip_and_parameters(tmp_path):
    source = '''
import pytest

def test_pass():
    assert True

def test_fail():
    assert False

@pytest.mark.skip(reason="not available")
def test_skip():
    assert True

@pytest.fixture
def broken():
    raise RuntimeError("fixture failed")

def test_setup(broken):
    assert True

@pytest.mark.parametrize("value", [0, 1])
def test_param(value):
    assert value == 0
'''
    selectors = [
        "test_example.py::test_pass", "test_example.py::test_fail",
        "test_example.py::test_skip", "test_example.py::test_setup",
        "test_example.py::test_param",
    ]
    code, report = run_pytest(tmp_path, source, selectors)
    fraction, cases = summarize_structured_suite(
        selectors, {"pytest_exit_code": code, "report": report}
    )
    assert [(case["status"], case["phase"]) for case in cases] == [
        ("passed", ""), ("failed", "call"), ("skipped", ""),
        ("failed", "setup"), ("failed", "call"),
    ]
    assert len(cases[-1]["pytest_items"]) == 2
    assert fraction["passed"] == 1
    assert fraction["total"] == 5
    assert fraction["status"] == "failed"


def test_collection_error_does_not_invent_other_test_outcomes(tmp_path):
    source = "from missing_benchmark_dependency import nope\n\ndef test_never_collected():\n    assert True\n"
    selectors = ["test_example.py::test_never_collected"]
    code, report = run_pytest(tmp_path, source, selectors)
    fraction, cases = summarize_structured_suite(
        selectors, {"pytest_exit_code": code, "report": report}
    )
    assert fraction["status"] == "failed"
    assert fraction["passed"] == 0
    assert cases[0]["status"] == "not_collected"
    assert cases[0]["phase"] == "collection"
    assert fraction["collection_errors"]


def test_all_skipped_suite_is_not_passed_even_when_pytest_exits_zero(tmp_path):
    source = 'import pytest\n\n@pytest.mark.skip(reason="optional dependency absent")\ndef test_optional():\n    pass\n'
    selectors = ["test_example.py::test_optional"]
    code, report = run_pytest(tmp_path, source, selectors)
    assert code == 0
    fraction, cases = summarize_structured_suite(
        selectors, {"pytest_exit_code": code, "report": report}
    )
    assert fraction["passed"] == 0
    assert fraction["status"] == "unknown"
    assert cases[0]["status"] == "skipped"


def test_pytest_rootdir_can_differ_from_selected_path(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "pytest.ini").write_text("[pytest]\n")
    (tests_dir / "test_example.py").write_text("def test_ok():\n    assert True\n")
    report_path = tmp_path / "cases.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PLUGIN_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["QUANBENCH_CASE_REPORT"] = str(report_path)
    selector = "tests/test_example.py::test_ok"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "pytest_case_report", selector],
        cwd=tmp_path, env=env, text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(report_path.read_text())
    assert report["collected"][0] == "test_example.py::test_ok"
    fraction, cases = summarize_structured_suite(
        [selector], {"pytest_exit_code": 0, "report": report}
    )
    assert fraction["status"] == "passed"
    assert cases[0]["status"] == "passed"


def test_collection_error_uses_source_path_under_nested_rootdir(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "pytest.ini").write_text("[pytest]\n")
    (tests_dir / "test_example.py").write_text(
        "from missing_benchmark_dependency import nope\n\ndef test_uncollected():\n    pass\n"
    )
    report_path = tmp_path / "cases.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PLUGIN_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["QUANBENCH_CASE_REPORT"] = str(report_path)
    selector = "tests/test_example.py::test_uncollected"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "pytest_case_report", selector],
        cwd=tmp_path, env=env, text=True, capture_output=True, check=False,
    )
    report = json.loads(report_path.read_text())
    fraction, cases = summarize_structured_suite(
        [selector], {"pytest_exit_code": completed.returncode, "report": report}
    )
    assert fraction["status"] == "failed"
    assert cases[0]["status"] == "not_collected"
    assert cases[0]["phase"] == "collection"


def test_repeated_runs_count_only_tests_passing_every_time():
    one = [
        {"selector": "a", "status": "passed", "phase": ""},
        {"selector": "b", "status": "failed", "phase": "call"},
    ]
    two = [
        {"selector": "a", "status": "failed", "phase": "call"},
        {"selector": "b", "status": "passed", "phase": ""},
    ]
    runs = [
        {"test_cases": {"fail_pass": one}, "fail_pass": {"status": "failed"}},
        {"test_cases": {"fail_pass": two}, "fail_pass": {"status": "failed"}},
    ]
    fraction, cases = aggregate_structured_test_cases(runs, "fail_pass")
    assert fraction["passed"] == 0
    assert fraction["total"] == 2
    assert [case["status"] for case in cases] == ["failed", "failed"]


def test_report_envelope_preserves_exact_pytest_exit_code():
    payload = {"schema_version": 1, "exitstatus": 1, "collected": [],
               "reports": [], "collection_errors": []}
    envelope = {"pytest_exit_code": 1, "report": payload}
    stdout = f"pytest output\n{BEGIN}fail_pass\n{json.dumps(envelope)}\n{END}fail_pass\n"
    assert extract_case_reports(stdout)["fail_pass"] == envelope


def test_unsubmitted_patch_keeps_each_selected_case_as_not_run():
    sample = PLUGIN_DIR.parents[1] / "dataset/samples/openfermion/openfermion_151_352/sample.json"
    result = attach_unrun_test_cases(sample, {"instance_id": "openfermion_151_352"})
    assert result["fail_pass"]["status"] == "not_run"
    assert result["fail_pass"]["total"] == 5
    assert len(result["test_cases"]["fail_pass"]) == 5
    assert all(case["status"] == "not_run" for case in result["test_cases"]["fail_pass"])


def test_case_report_preserves_repository_paths_from_test_subdirectory(tmp_path):
    """A resource-dependent test can run in tests/ without losing selector identity."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_resource.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', ['H 0.0 0.0', 'Li 0.0 1.5'])\n"
        "def test_resource(value):\n"
        "    assert open('fixture.txt').read() == 'ok'\n"
    )
    (tests / "fixture.txt").write_text("ok")
    report_path = tmp_path / "report.json"
    env = dict(os.environ)
    env.update(PYTHONPATH=str(PLUGIN_DIR), QUANBENCH_CASE_REPORT=str(report_path),
               QUANBENCH_CASE_ROOT=str(tmp_path))
    selectors = ["tests/test_resource.py::test_resource[H 0.0 0.0]",
                 "tests/test_resource.py::test_resource[Li 0.0 1.5]"]
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "pytest_case_report",
         "--rootdir=" + str(tmp_path), *[str(tmp_path / s) for s in selectors]],
        cwd=tests, env=env, text=True, capture_output=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text())
    fraction, cases = summarize_structured_suite(selectors, {"pytest_exit_code": 0, "report": report})
    assert fraction["passed"] == 2
    assert all(case["status"] == "passed" for case in cases)
