#!/usr/bin/env python3
"""Migrate benchmark validation names to fail-pass/pass-pass.

The project originally used primary/regression for the two validation suites.
This script updates built samples and CSV notes to use SWE-bench Pro aligned
fail-pass/pass-pass terminology.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
REVIEW_CSV = ROOT / "preprocessing" / "result" / "review_candidates.csv"

def migrate_validation(validation: dict) -> bool:
    changed = False
    for side in ("patched", "base"):
        section = validation.get(side)
        if not isinstance(section, dict):
            continue
        if "primary" in section and "fail_pass" not in section:
            section["fail_pass"] = section.pop("primary")
            changed = True
        elif "primary" in section:
            section.pop("primary")
            changed = True
        if "regression" in section and "pass_pass" not in section:
            section["pass_pass"] = section.pop("regression")
            changed = True
        elif "regression" in section:
            section.pop("regression")
            changed = True
    return changed


def replace_text(path: Path, replacements: list[tuple[str, str]]) -> bool:
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    updated = original
    for old, new in replacements:
        updated = updated.replace(old, new)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def migrate_sample(sample_path: Path) -> list[Path]:
    changed_files: list[Path] = []
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    if migrate_validation(sample.get("validation", {})):
        sample_path.write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed_files.append(sample_path)

    sample_dir = sample_path.parent
    docker_replacements = [
        ("ENV TEST_PATH=", "ENV FAIL_PASS_TEST_PATHS="),
        ("ENV TEST_PATHS=", "ENV FAIL_PASS_TEST_PATHS="),
        ("ENV REGRESSION_TEST_PATHS=", "ENV PASS_PASS_TEST_PATHS="),
        ("ENV PRIMARY_SUPPORT_PATHS=", "ENV FAIL_PASS_SUPPORT_PATHS="),
        ("__PRIMARY_TEST_FILES__", "__FAIL_PASS_TEST_FILES__"),
        ("__REGRESSION_TEST_FILES__", "__PASS_PASS_TEST_FILES__"),
    ]
    if replace_text(sample_dir / "Dockerfile", docker_replacements):
        changed_files.append(sample_dir / "Dockerfile")

    run_sh = sample_dir / "run.sh"
    run_replacements = [
        ('TEST_SUITE="${2:-${TEST_SUITE:-primary}}"', 'TEST_SUITE="${2:-${TEST_SUITE:-fail-pass}}"'),
        ('TEST_PATHS="${TEST_PATHS:-${TEST_PATH:-}}"', 'FAIL_PASS_TEST_PATHS="${FAIL_PASS_TEST_PATHS:-}"'),
        ('REGRESSION_TEST_PATHS="${REGRESSION_TEST_PATHS:-${REGRESSION_TEST_PATH:-}}"', 'PASS_PASS_TEST_PATHS="${PASS_PASS_TEST_PATHS:-}"'),
        ('FAIL_PASS_TEST_PATHS="${FAIL_PASS_TEST_PATHS:-${TEST_PATHS:-${TEST_PATH:-}}}"', 'FAIL_PASS_TEST_PATHS="${FAIL_PASS_TEST_PATHS:-}"'),
        ('PASS_PASS_TEST_PATHS="${PASS_PASS_TEST_PATHS:-${REGRESSION_TEST_PATHS:-${REGRESSION_TEST_PATH:-}}}"', 'PASS_PASS_TEST_PATHS="${PASS_PASS_TEST_PATHS:-}"'),
        ("PRIMARY_SUPPORT_PATHS", "FAIL_PASS_SUPPORT_PATHS"),
        ('echo "Test path: ${TEST_PATH}"', 'echo "Fail-pass test paths: ${FAIL_PASS_TEST_PATHS}"'),
        ('echo "Test paths: ${TEST_PATHS}"', 'echo "Fail-pass test paths: ${FAIL_PASS_TEST_PATHS}"'),
        ('echo "Regression test paths: ${REGRESSION_TEST_PATHS}"', 'echo "Pass-pass test paths: ${PASS_PASS_TEST_PATHS}"'),
        ('[ "${TEST_SUITE}" = "primary" ]', '[ "${TEST_SUITE}" = "fail-pass" ]'),
        ('{ [ "${TEST_SUITE}" = "fail-pass" ] || [ "${TEST_SUITE}" = "primary" ]; }', '[ "${TEST_SUITE}" = "fail-pass" ]'),
        ("# Primary tests may be introduced or modified by the patch.", "# Fail-pass tests may be introduced or modified by the patch."),
        ("# Primary tests were introduced by the patch.", "# Fail-pass tests were introduced by the patch."),
        ("# Primary tests were modified by the patch.", "# Fail-pass tests were modified by the patch."),
        ("checkout_patched_files_from_selectors ${TEST_PATHS}", "checkout_patched_files_from_selectors ${FAIL_PASS_TEST_PATHS}"),
        ('checkout_patched_files_from_selectors "${TEST_PATH}"', "checkout_patched_files_from_selectors ${FAIL_PASS_TEST_PATHS}"),
        ("fail-pass|primary)", "fail-pass)"),
        ("primary)", "fail-pass)"),
        ('if [ -z "${TEST_PATHS}" ]; then', 'if [ -z "${FAIL_PASS_TEST_PATHS}" ]; then'),
        ('echo "No primary tests configured." >&2', 'echo "No fail-pass tests configured." >&2'),
        ('python -m pytest -q "${TEST_PATH}"', "python -m pytest -q ${FAIL_PASS_TEST_PATHS}"),
        ("python -m pytest -q ${TEST_PATHS}", "python -m pytest -q ${FAIL_PASS_TEST_PATHS}"),
        ("pass-pass|regression)", "pass-pass)"),
        ("regression)", "pass-pass)"),
        ('SELECTED_REGRESSION_TEST_PATHS="${REGRESSION_TEST_PATHS}"', 'SELECTED_PASS_PASS_TEST_PATHS="${PASS_PASS_TEST_PATHS}"'),
        ('if [ -z "${SELECTED_REGRESSION_TEST_PATHS}" ]; then', 'if [ -z "${SELECTED_PASS_PASS_TEST_PATHS}" ]; then'),
        ('echo "No regression tests configured."', 'echo "No pass-pass tests configured."'),
        ("python -m pytest -q ${SELECTED_REGRESSION_TEST_PATHS}", "python -m pytest -q ${SELECTED_PASS_PASS_TEST_PATHS}"),
        ('echo "Use \'primary\' or \'regression\'." >&2', 'echo "Use \'fail-pass\' or \'pass-pass\'." >&2'),
    ]
    if replace_text(run_sh, run_replacements):
        changed_files.append(run_sh)

    return changed_files


def migrate_review_csv() -> bool:
    if not REVIEW_CSV.exists():
        return False
    rows = list(csv.DictReader(REVIEW_CSV.open(newline="", encoding="utf-8")))
    if not rows:
        return False
    fieldnames = list(rows[0].keys())
    changed = False
    for row in rows:
        notes = row.get("benchmark_notes")
        if not notes:
            continue
        updated = notes
        for old, new in [
            ("patched primary", "patched fail-pass"),
            ("patched regression", "patched pass-pass"),
            ("base primary", "base fail-pass"),
            ("base regression", "base pass-pass"),
            ("Primary", "Fail-pass"),
            ("Regression", "Pass-pass"),
            (" primary ", " fail-pass "),
            (" regression ", " pass-pass "),
        ]:
            updated = updated.replace(old, new)
        if updated != notes:
            row["benchmark_notes"] = updated
            changed = True
    if not changed:
        return False
    with REVIEW_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return True


def main() -> None:
    changed: list[Path] = []
    for sample_path in sorted(SAMPLES_DIR.rglob("sample.json")):
        changed.extend(migrate_sample(sample_path))
    if migrate_review_csv():
        changed.append(REVIEW_CSV)

    print(f"Migrated {len(changed)} files.")
    for path in changed:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
