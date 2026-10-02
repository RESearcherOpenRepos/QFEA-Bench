"""Pytest plugin that writes exact node IDs and phase outcomes as JSON.

The evaluator injects this file into its container and loads it with
``-p pytest_case_report``. Keep it compatible with the historical Python and
pytest versions used by benchmark samples.
"""

import json
import os


_collected = []
_collected_items = []
_reports = []
_collection_errors = []
_rootdir = os.getcwd()


def _relative_path(path):
    path = str(path)
    if not os.path.isabs(path):
        path = os.path.join(_rootdir, path)
    return os.path.relpath(path, os.environ.get("QUANBENCH_CASE_ROOT", os.getcwd())).replace(os.sep, "/")


def pytest_configure(config):
    global _rootdir
    _rootdir = str(getattr(config, "rootpath", None) or getattr(config, "rootdir", os.getcwd()))


def pytest_collection_modifyitems(session, config, items):
    _collected[:] = [item.nodeid for item in items]
    _collected_items[:] = []
    for item in items:
        path = getattr(item, "path", None) or getattr(item, "fspath", None)
        suffix = item.nodeid.split("::", 1)
        selector = _relative_path(path)
        if len(suffix) == 2:
            selector += "::" + suffix[1]
        _collected_items.append({"nodeid": item.nodeid, "selector": selector})


def pytest_collectreport(report):
    if report.failed:
        path = getattr(report, "fspath", None)
        if not path and report.nodeid:
            path = os.path.join(_rootdir, report.nodeid.split("::", 1)[0])
        _collection_errors.append(
            {"nodeid": report.nodeid,
             "path": _relative_path(path) if path else "",
             "message": str(report.longrepr)}
        )


def pytest_runtest_logreport(report):
    _reports.append(
        {
            "nodeid": report.nodeid,
            "when": report.when,
            "outcome": report.outcome,
            "wasxfail": bool(getattr(report, "wasxfail", False)),
        }
    )


def pytest_sessionfinish(session, exitstatus):
    path = os.environ.get("QUANBENCH_CASE_REPORT")
    if not path:
        return
    payload = {
        "schema_version": 1,
        "exitstatus": int(exitstatus),
        "collected": _collected,
        "collected_items": _collected_items,
        "reports": _reports,
        "collection_errors": _collection_errors,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"), ensure_ascii=False)
