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


if [ "${TARGET_COMMIT_MODE}" = "base" ] && { [ "${TEST_SUITE}" = "fail-pass" ]; }; then
  # The BosonicOp and BosonicLinearMapper tests were introduced by the patch.
  # Bring those tests into the base tree so they can fail against the missing implementation.
  # shellcheck disable=SC2086
  checkout_patched_files_from_selectors ${FAIL_PASS_TEST_PATHS}
fi

if [ "${PREP_ONLY:-0}" = "1" ]; then
  exit 0
fi

case "${TEST_SUITE}" in
  fail-pass)
    # shellcheck disable=SC2086
    python -m pytest -q ${FAIL_PASS_TEST_PATHS}
    ;;
  pass-pass)
    SELECTED_PASS_PASS_TEST_PATHS="${PASS_PASS_TEST_PATHS}"
    if [ -z "${SELECTED_PASS_PASS_TEST_PATHS}" ]; then
      echo "No pass-pass tests configured."
      exit 0
    fi
    # shellcheck disable=SC2086
    python -m pytest -q ${SELECTED_PASS_PASS_TEST_PATHS}
    ;;
  *)
    echo "Unsupported test suite: ${TEST_SUITE}" >&2
    echo "Use 'fail-pass' or 'pass-pass'." >&2
    exit 2
    ;;
esac
