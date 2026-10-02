#!/usr/bin/env python3
"""Build leak-free benchmark-agent-base images from partial repo-base images."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS_JSON = ROOT / "benchmark" / "dataset" / "build_logs" / "image_rebuild_progress.json"

DOCKERFILE_TEXT = """\
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG BASE_COMMIT
ARG PATCHED_COMMIT=
RUN set -eux; \\
    test -n "${BASE_COMMIT}"; \\
    test -d /workspace/repo; \\
    cd /workspace/repo; \\
    git_retry() { \\
        for attempt in 1 2 3; do \\
            if "$@"; then return 0; fi; \\
            if [ "${attempt}" = "3" ]; then return 1; fi; \\
            sleep 3; \\
        done; \\
    }; \\
    git_retry git fetch origin "${BASE_COMMIT}" || true; \\
    git_retry git checkout --force "${BASE_COMMIT}"; \\
    git_retry git reset --hard "${BASE_COMMIT}"; \\
    git clean -fdx; \\
    BASE_TREE="$(git show -s --format=%T "${BASE_COMMIT}")"; \\
    git cat-file commit "${BASE_COMMIT}" > /tmp/base.commit; \\
    tar --exclude=.git -cf /tmp/base-worktree.tar .; \\
    cd /workspace; \\
    mkdir /workspace/repo.baseonly; \\
    cd /workspace/repo.baseonly; \\
    git init; \\
    tar -xf /tmp/base-worktree.tar; \\
    git add -A -f; \\
    git -C /workspace/repo ls-tree -r "${BASE_COMMIT}" | while IFS="$(printf '\\t')" read -r meta path; do \\
      mode="${meta%% *}"; object="${meta##* }"; \\
      if [ "${mode}" = "160000" ]; then \\
        mkdir -p "$(dirname "${path}")"; \\
        git update-index --add --cacheinfo 160000 "${object}" "${path}"; \\
      fi; \\
    done; \\
    test "$(git write-tree)" = "${BASE_TREE}"; \\
    test "$(git hash-object -t commit -w /tmp/base.commit)" = "${BASE_COMMIT}"; \\
    echo "${BASE_COMMIT}" > .git/shallow; \\
    git update-ref refs/heads/benchmark-base "${BASE_COMMIT}"; \\
    git symbolic-ref HEAD refs/heads/benchmark-base; \\
    git reset --hard "${BASE_COMMIT}"; \\
    rm -f /tmp/base.commit /tmp/base-worktree.tar; \\
    cd /workspace; \\
    rm -rf /workspace/repo; \\
    mv /workspace/repo.baseonly /workspace/repo; \\
    cd /workspace/repo; \\
    git reflog expire --expire=now --expire-unreachable=now --all; \\
    git gc --prune=now; \\
    test "$(git rev-parse HEAD)" = "${BASE_COMMIT}"; \\
    if [ -n "${PATCHED_COMMIT}" ]; then ! git cat-file -e "${PATCHED_COMMIT}^{commit}"; fi; \\
    rm -rf /benchmark; \\
    rm -rf /testbed
__POST_CLEAN_SETUP__
ENV SAMPLE_ID= \\
    REPOSITORY= \\
    REPOSITORY_URL= \\
    ISSUE_URL= \\
    PR_URL= \\
    BASE_COMMIT= \\
    PATCHED_COMMIT= \\
    PR_HEAD_COMMIT= \\
    DEFAULT_TARGET= \\
    FAIL_PASS_TEST_PATHS= \\
    FAIL_PASS_SUPPORT_PATHS= \\
    FAIL_PASS_EXTRA_FILES= \\
    PASS_PASS_TEST_PATHS= \\
    PASS_PASS_SUPPORT_PATHS= \\
    TEST_PATHS= \\
    TEST_PATH= \\
    SUPPORT_PATHS= \\
    PRIMARY_SUPPORT_PATHS= \\
    REGRESSION_TEST_PATHS= \\
    REGRESSION_TEST_PATH= \\
    REGRESSION_SUPPORT_PATHS=
WORKDIR /workspace/repo
ENTRYPOINT []
CMD ["/bin/bash"]
"""

PLUGIN_REINSTALL_STEP = """\
# Rebuild legacy PennyLane entry points from the leak-free base checkout.
ENV PYTHONPATH=/workspace/repo
RUN set -eux; \\
    cd /workspace/repo; \\
    python -m pip install --no-index --no-deps --no-build-isolation --force-reinstall --no-cache-dir .; \\
    git clean -fdx; \\
    python -c 'import pennylane as qml; qml.device("default.qubit", wires=1)'
"""


@dataclass(frozen=True)
class AgentBaseSpec:
    sample_id: str
    sample_path: Path
    source_image: str
    output_image: str
    base_commit: str
    patched_commit: str | None
    repair_plugin_entry_points_after_clean: bool


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_index_samples(samples_dir: Path) -> list[dict[str, Any]]:
    index = read_json(samples_dir / "index.json")
    return list(index.get("samples", []))


def load_specs(samples_dir: Path, sample_filter: str | None, limit: int | None) -> list[AgentBaseSpec]:
    specs: list[AgentBaseSpec] = []
    for item in iter_index_samples(samples_dir):
        sample_id = item["sample_id"]
        if sample_filter and sample_filter not in sample_id and sample_filter not in item.get("sample_path", ""):
            continue
        sample_path = samples_dir / item["sample_path"] / "sample.json"
        sample = read_json(sample_path)
        instance = sample["instance"]
        specs.append(
            AgentBaseSpec(
                sample_id=sample_id,
                sample_path=sample_path,
                source_image=f"benchmark-base:{sample_id}",
                output_image=f"benchmark-agent-base:{sample_id}",
                base_commit=instance["base_commit"],
                patched_commit=instance.get("patch"),
                repair_plugin_entry_points_after_clean=sample.get("runtime", {}).get("environment", {}).get(
                    "repair_plugin_entry_points_after_clean", False
                ),
            )
        )
    if limit is not None:
        specs = specs[:limit]
    return specs


def phase_record() -> dict[str, Any]:
    return {
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "duration_seconds": None,
        "log_path": None,
        "image_id": None,
        "summary": None,
        "error": None,
    }


def ensure_progress_phase(progress: dict[str, Any], phase_name: str) -> None:
    statuses = progress.get("status_values") or ["pending", "running", "passed", "failed", "skipped", "blocked"]
    for sample in progress.get("samples", []):
        sample.setdefault("phases", {}).setdefault(phase_name, phase_record())
    progress.setdefault("summary", {}).setdefault("phases", {}).setdefault(
        phase_name,
        {status: 0 for status in statuses},
    )


def recompute_progress(progress: dict[str, Any]) -> None:
    statuses = progress.get("status_values") or ["pending", "running", "passed", "failed", "skipped", "blocked"]
    phase_names = progress.get("stage_order") or []
    progress["summary"] = {
        "overall": {status: 0 for status in statuses},
        "phases": {},
    }
    for sample in progress.get("samples", []):
        overall = sample.get("overall_status") or "pending"
        progress["summary"]["overall"][overall] = progress["summary"]["overall"].get(overall, 0) + 1
    for phase_name in phase_names:
        counts = {status: 0 for status in statuses}
        for sample in progress.get("samples", []):
            status = (sample.get("phases", {}).get(phase_name) or {}).get("status") or "pending"
            counts[status] = counts.get(status, 0) + 1
        progress["summary"]["phases"][phase_name] = counts


def update_progress(
    progress_path: Path,
    sample_id: str,
    phase_name: str,
    *,
    status: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_seconds: float | None = None,
    log_path: Path | None = None,
    image_id: str | None = None,
    summary: str | None = None,
    error: str | None = None,
) -> None:
    if not progress_path.exists():
        return
    progress = read_json(progress_path)
    ensure_progress_phase(progress, phase_name)
    for sample in progress.get("samples", []):
        if sample.get("sample_id") != sample_id:
            continue
        phase = sample["phases"][phase_name]
        phase["status"] = status
        if started_at is not None:
            phase["started_at"] = started_at
        if finished_at is not None:
            phase["finished_at"] = finished_at
        if duration_seconds is not None:
            phase["duration_seconds"] = round(duration_seconds, 3)
        if log_path is not None:
            phase["log_path"] = str(log_path)
        if image_id is not None:
            phase["image_id"] = image_id
        if summary is not None:
            phase["summary"] = summary
        if error is not None:
            phase["error"] = error
            sample["last_error"] = error
        break
    progress["updated_at"] = now_iso()
    recompute_progress(progress)
    progress_path.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def docker_image_id(image: str) -> str | None:
    completed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def build_command(spec: AgentBaseSpec, context_dir: Path) -> list[str]:
    return [
        "docker",
        "build",
        "--platform",
        "linux/amd64",
        "--build-arg",
        f"BASE_IMAGE={spec.source_image}",
        "--build-arg",
        f"BASE_COMMIT={spec.base_commit}",
        "--build-arg",
        f"PATCHED_COMMIT={spec.patched_commit or ''}",
        "-t",
        spec.output_image,
        str(context_dir),
    ]


def build_one(spec: AgentBaseSpec, log_dir: Path, progress_path: Path, dry_run: bool) -> bool:
    phase_name = "agent_base_build"
    log_path = log_dir / f"{spec.sample_id}.agent_base.log"
    with tempfile.TemporaryDirectory(prefix="quanbench-agent-base-") as tmp:
        context_dir = Path(tmp)
        dockerfile = DOCKERFILE_TEXT.replace(
            "__POST_CLEAN_SETUP__",
            PLUGIN_REINSTALL_STEP if spec.repair_plugin_entry_points_after_clean else "",
        )
        (context_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        command = build_command(spec, context_dir)
        if dry_run:
            print(" ".join(command))
            return True
        started = now_iso()
        update_progress(progress_path, spec.sample_id, phase_name, status="running", started_at=started, log_path=log_path)
        start = time.monotonic()
        with log_path.open("w", encoding="utf-8") as log_file:
            log_file.write(" ".join(command) + "\n\n")
            completed = subprocess.run(command, stdout=log_file, stderr=subprocess.STDOUT, text=True, check=False)
    duration = time.monotonic() - start
    if completed.returncode == 0:
        image_id = docker_image_id(spec.output_image)
        update_progress(
            progress_path,
            spec.sample_id,
            phase_name,
            status="passed",
            finished_at=now_iso(),
            duration_seconds=duration,
            log_path=log_path,
            image_id=image_id,
            summary=f"built {spec.output_image}",
            error=None,
        )
        print(f"{spec.sample_id}: OK {spec.output_image}", flush=True)
        return True
    update_progress(
        progress_path,
        spec.sample_id,
        phase_name,
        status="failed",
        finished_at=now_iso(),
        duration_seconds=duration,
        log_path=log_path,
        summary=f"docker build exited {completed.returncode}",
        error=f"agent-base build failed; see {log_path}",
    )
    print(f"{spec.sample_id}: FAIL see {log_path}", flush=True)
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build leak-free benchmark-agent-base images.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS_JSON)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--filter", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    specs = load_specs(args.samples_dir, args.filter, args.limit)
    if not specs:
        raise SystemExit("No samples matched.")
    log_dir = args.log_dir or (ROOT / "benchmark" / "dataset" / "build_logs" / now_iso().replace(":", ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for spec in specs:
        if not build_one(spec, log_dir, args.progress_json, args.dry_run):
            failures += 1
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
