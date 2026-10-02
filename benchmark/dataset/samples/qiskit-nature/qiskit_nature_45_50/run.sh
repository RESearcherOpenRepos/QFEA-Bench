#!/usr/bin/env bash
set -euo pipefail

echo "Sample: ${SAMPLE_ID}"
echo "Repository: ${REPOSITORY}"
echo "Issue: ${ISSUE_URL}"
echo "PR: ${PR_URL}"

TARGET_COMMIT_MODE="${1:-${TARGET:-${DEFAULT_TARGET:-patched}}}"
TEST_SUITE="${2:-${TEST_SUITE:-fail-pass}}"
REPO_DIR="${REPO_DIR:-/workspace/repo}"
FAIL_PASS_TEST_PATHS="${FAIL_PASS_TEST_PATHS:-}"
PASS_PASS_TEST_PATHS="${PASS_PASS_TEST_PATHS:-}"
FAIL_PASS_EXTRA_FILES="${FAIL_PASS_EXTRA_FILES:-}"

case "${TARGET_COMMIT_MODE}" in
  base)
    TARGET_COMMIT="${BASE_COMMIT}"
    ;;
  patched)
    TARGET_COMMIT="${PATCHED_COMMIT}"
    ;;
  *)
    echo "Unsupported target mode: ${TARGET_COMMIT_MODE}" >&2
    echo "Use 'base' or 'patched'." >&2
    exit 2
    ;;
esac

echo "Target mode: ${TARGET_COMMIT_MODE}"
echo "Target commit: ${TARGET_COMMIT}"
echo "Repository URL: ${REPOSITORY_URL}"
echo "Fail-pass test paths: ${FAIL_PASS_TEST_PATHS}"
echo "Pass-pass test paths: ${PASS_PASS_TEST_PATHS}"
echo "Fail-pass extra files: ${FAIL_PASS_EXTRA_FILES}"
echo "Test suite: ${TEST_SUITE}"

retry() {
  local attempts="$1"
  shift
  local try=1
  while true; do
    if "$@"; then
      return 0
    fi
    if [ "${try}" -ge "${attempts}" ]; then
      return 1
    fi
    echo "Command failed. Retrying (${try}/${attempts})..." >&2
    try=$((try + 1))
    sleep 3
  done
}

run_selectors_individually() {
  local expectation="$1"
  shift
  local selectors=("$@")
  local selector
  local selector_status
  local passed_count=0
  local failed_count=0

  if [ "${#selectors[@]}" -eq 0 ]; then
    echo "No selectors provided." >&2
    return 2
  fi

  for selector in "${selectors[@]}"; do
    echo "Running selector: ${selector}"
    set +e
    python -m pytest -q "${selector}"
    selector_status=$?
    set -e

    if [ "${selector_status}" -eq 0 ]; then
      passed_count=$((passed_count + 1))
    else
      failed_count=$((failed_count + 1))
    fi

    case "${expectation}" in
      pass)
        if [ "${selector_status}" -ne 0 ]; then
          echo "Selector failed unexpectedly: ${selector}" >&2
          return "${selector_status}"
        fi
        ;;
      fail)
        if [ "${selector_status}" -eq 0 ]; then
          echo "Selector passed unexpectedly on base fail-pass: ${selector}" >&2
          return 22
        fi
        ;;
      *)
        echo "Unsupported selector expectation: ${expectation}" >&2
        return 2
        ;;
    esac
  done

  echo "Selector summary: ${passed_count} passed runs, ${failed_count} failed runs."

  if [ "${expectation}" = "fail" ]; then
    return 1
  fi
  return 0
}

checkout_patched_files_from_selectors() {
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
    git checkout "${PATCHED_COMMIT}" -- "${files[@]}"
  fi
}

if [ ! -d "${REPO_DIR}/.git" ]; then
  retry 3 git clone "${REPOSITORY_URL}" "${REPO_DIR}"
fi

cd "${REPO_DIR}"
retry 3 git fetch --all --tags --prune
git checkout --force "${TARGET_COMMIT}"
git clean -fdx
if [ -n "${MODEL_PATCH_FILE:-}" ]; then
  if [ -s "${MODEL_PATCH_FILE}" ]; then
    if git apply --whitespace=nowarn "${MODEL_PATCH_FILE}"; then
      echo "Patch applied: true"
    else
      echo "Patch applied: false (git apply failed)." >&2
      exit 21
    fi
  else
    echo "Patch applied: false (empty model patch)." >&2
    exit 20
  fi
fi

if [ "${TARGET_COMMIT_MODE}" = "base" ] && [ "${TEST_SUITE}" = "fail-pass" ]; then
  # shellcheck disable=SC2086
  checkout_patched_files_from_selectors ${FAIL_PASS_TEST_PATHS}
  if [ -n "${FAIL_PASS_EXTRA_FILES}" ]; then
    # shellcheck disable=SC2086
    git checkout "${PATCHED_COMMIT}" -- ${FAIL_PASS_EXTRA_FILES}
  fi
fi

if [ "${PREP_ONLY:-0}" = "1" ]; then
  exit 0
fi

case "${TEST_SUITE}" in
  fail-pass)
    if [ -z "${FAIL_PASS_TEST_PATHS}" ]; then
      echo "No fail-pass tests configured." >&2
      exit 2
    fi
    read -r -a fail_pass_selectors <<< "${FAIL_PASS_TEST_PATHS}"
    if [ "${TARGET_COMMIT_MODE}" = "base" ]; then
      run_selectors_individually fail "${fail_pass_selectors[@]}"
    else
      run_selectors_individually pass "${fail_pass_selectors[@]}"
    fi
    ;;
  pass-pass)
    if [ -z "${PASS_PASS_TEST_PATHS}" ]; then
      echo "No pass-pass tests configured."
      exit 0
    fi
    read -r -a pass_pass_selectors <<< "${PASS_PASS_TEST_PATHS}"
    run_selectors_individually pass "${pass_pass_selectors[@]}"
    ;;
  *)
    echo "Unsupported test suite: ${TEST_SUITE}" >&2
    echo "Use 'fail-pass' or 'pass-pass'." >&2
    exit 2
    ;;
esac
