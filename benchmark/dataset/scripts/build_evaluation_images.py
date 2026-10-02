#!/usr/bin/env python3
"""Build final benchmark-evaluation images directly from benchmark-base images."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import re
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
FROM ${{BASE_IMAGE}}

ARG BASE_COMMIT
ARG PATCHED_COMMIT
ARG PR_HEAD_COMMIT=

{env_lines}

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

RUN set -eux; \\
    test -n "${{BASE_COMMIT}}"; \\
    test -n "${{PATCHED_COMMIT}}"; \\
    test -d /workspace/repo; \\
    cd /workspace/repo; \\
    git_retry() {{ \\
        for attempt in 1 2 3; do \\
            if "$@"; then return 0; fi; \\
            if [ "${{attempt}}" = "3" ]; then return 1; fi; \\
            sleep 3; \\
        done; \\
    }}; \\
    git_retry git fetch origin "${{BASE_COMMIT}}" || true; \\
    git_retry git fetch origin "${{PATCHED_COMMIT}}" || true; \\
    if [ -n "${{PR_HEAD_COMMIT}}" ]; then git_retry git fetch origin "${{PR_HEAD_COMMIT}}" || true; fi; \\
    git_retry git checkout --force "${{BASE_COMMIT}}"; \\
    git_retry git reset --hard "${{BASE_COMMIT}}"; \\
    git clean -fdx; \\
    git_retry git checkout --force "${{PATCHED_COMMIT}}"; \\
    git_retry git reset --hard "${{PATCHED_COMMIT}}"; \\
    git clean -fdx; \\
    GIT_NO_LAZY_FETCH=1 git checkout --force "${{BASE_COMMIT}}"; \\
    GIT_NO_LAZY_FETCH=1 git reset --hard "${{BASE_COMMIT}}"; \\
    GIT_NO_LAZY_FETCH=1 git checkout --force "${{PATCHED_COMMIT}}"; \\
    GIT_NO_LAZY_FETCH=1 git reset --hard "${{PATCHED_COMMIT}}"; \\
    git clean -fdx

{post_clean_setup}

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
"""

PLUGIN_REINSTALL_STEP = """\
# Legacy PennyLane discovers even built-in devices through installed entry points.
# Install a wheel after the final clean so metadata survives later git clean calls.
ENV PYTHONPATH=/workspace/repo
RUN set -eux; \\
    cd /workspace/repo; \\
    python -m pip install --no-index --no-deps --no-build-isolation --force-reinstall --no-cache-dir .; \\
    git clean -fdx; \\
    python -c 'import pennylane as qml; qml.device("default.qubit", wires=1)'
"""

ENV_LINE_RE = re.compile(r"^ENV\s+")


@dataclass(frozen=True)
class EvaluationBuildSpec:
    sample_id: str
    sample_path: Path
    source_image: str
    output_image: str
    base_commit: str
    patched_commit: str
    pr_head_commit: str | None
    repair_plugin_entry_points_after_clean: bool


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_index_samples(samples_dir: Path) -> list[dict[str, Any]]:
    index = read_json(samples_dir / "index.json")
    return list(index.get("samples", []))


def source_base_image(sample_id: str) -> str:
    return f"benchmark-base:{sample_id}"


def output_evaluation_image(sample_id: str) -> str:
    return f"benchmark-evaluation:{sample_id}"


def load_specs(
    samples_dir: Path,
    sample_filter: str | None,
    limit: int | None,
    output_image: str | None,
) -> list[EvaluationBuildSpec]:
    specs: list[EvaluationBuildSpec] = []
    for item in iter_index_samples(samples_dir):
        sample_id = item["sample_id"]
        if sample_filter and sample_filter not in sample_id and sample_filter not in item.get("sample_path", ""):
            continue
        sample_path = samples_dir / item["sample_path"] / "sample.json"
        sample = read_json(sample_path)
        instance = sample["instance"]
        specs.append(
            EvaluationBuildSpec(
                sample_id=sample_id,
                sample_path=sample_path,
                source_image=(sample.get("runtime", {}).get("docker", {}).get("evaluation_source_image")
                              or source_base_image(sample_id)),
                output_image=output_image or output_evaluation_image(sample_id),
                base_commit=instance["base_commit"],
                patched_commit=instance["patch"],
                pr_head_commit=instance.get("pr_head_commit"),
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


def docker_image_size(image: str) -> str | None:
    completed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Size}}", image],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def update_sample_docker_metadata(
    sample_path: Path,
    image: str,
    image_id: str | None,
    image_size: str | None,
) -> None:
    sample = read_json(sample_path)
    docker = sample.setdefault("runtime", {}).setdefault("docker", {})
    docker["image"] = image
    if image_id:
        docker["image_id"] = image_id
    if image_size:
        docker["image_size"] = image_size
    sample_path.write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def refresh_sample_index(samples_dir: Path) -> None:
    entries = []
    for sample_path in sorted(samples_dir.rglob("sample.json")):
        if sample_path.parent == samples_dir:
            continue
        sample = read_json(sample_path)
        instance = sample.get("instance", {})
        docker = sample.get("runtime", {}).get("docker", {})
        entries.append(
            {
                "id": instance.get("id"),
                "sample_id": instance.get("instance_id"),
                "repo": instance.get("repo"),
                "sample_path": str(sample_path.parent.relative_to(samples_dir)),
                "docker_build_success": docker.get("build_success"),
                "docker_platform": docker.get("platform"),
                "docker_image": docker.get("image"),
            }
        )
    ids = [entry["id"] for entry in entries]
    if any(type(sample_id) is not int for sample_id in ids) or sorted(ids) != list(
        range(1, len(entries) + 1)
    ):
        raise ValueError("Sample IDs must be unique consecutive integers from 1 to the sample count")
    entries.sort(key=lambda row: row["id"])
    payload = {"total_samples": len(entries), "samples": entries}
    (samples_dir / "index.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sample_env_lines(sample_dir: Path) -> list[str]:
    dockerfile = sample_dir / "Dockerfile"
    if not dockerfile.exists():
        raise FileNotFoundError(f"Sample Dockerfile not found: {dockerfile}")
    return [
        line.rstrip()
        for line in dockerfile.read_text(encoding="utf-8").splitlines()
        if ENV_LINE_RE.match(line)
    ]


def write_build_context(spec: EvaluationBuildSpec, context_dir: Path) -> None:
    sample_dir = spec.sample_path.parent
    env_lines = "\n".join(sample_env_lines(sample_dir))
    dockerfile = DOCKERFILE_TEXT.format(
        env_lines=env_lines,
        post_clean_setup=PLUGIN_REINSTALL_STEP if spec.repair_plugin_entry_points_after_clean else "",
    )
    (context_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    for name in ("sample.json", "run.sh"):
        source = sample_dir / name
        if not source.exists():
            raise FileNotFoundError(f"Required sample file not found: {source}")
        (context_dir / name).write_bytes(source.read_bytes())


def build_command(spec: EvaluationBuildSpec, context_dir: Path) -> list[str]:
    command = [
        "docker",
        "build",
        "--platform",
        "linux/amd64",
        "--build-arg",
        f"BASE_IMAGE={spec.source_image}",
        "--build-arg",
        f"BASE_COMMIT={spec.base_commit}",
        "--build-arg",
        f"PATCHED_COMMIT={spec.patched_commit}",
    ]
    if spec.pr_head_commit:
        command.extend(["--build-arg", f"PR_HEAD_COMMIT={spec.pr_head_commit}"])
    command.extend(["-t", spec.output_image, str(context_dir)])
    return command


def build_one(
    spec: EvaluationBuildSpec,
    log_dir: Path,
    progress_path: Path,
    dry_run: bool,
) -> bool:
    phase_name = "evaluator_hydration"
    log_path = log_dir / f"{spec.sample_id}.evaluation_build.log"
    with tempfile.TemporaryDirectory(prefix="quanbench-eval-build-") as tmp:
        context_dir = Path(tmp)
        write_build_context(spec, context_dir)
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
        image_size = docker_image_size(spec.output_image)
        update_sample_docker_metadata(spec.sample_path, spec.output_image, image_id, image_size)
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
        error=f"evaluation image build failed; see {log_path}",
    )
    print(f"{spec.sample_id}: FAIL see {log_path}", flush=True)
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build benchmark-evaluation images from benchmark-base images.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS_JSON)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--filter", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-image", default=None, help="Override output image tag; only useful with --filter/--limit 1.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_image and not (args.filter or args.limit == 1):
        raise SystemExit("--output-image should only be used for a single selected sample")
    specs = load_specs(args.samples_dir, args.filter, args.limit, args.output_image)
    if not specs:
        raise SystemExit("No samples matched.")
    log_dir = args.log_dir or (ROOT / "benchmark" / "dataset" / "build_logs" / now_iso().replace(":", ""))
    log_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for spec in specs:
        if not build_one(spec, log_dir, args.progress_json, args.dry_run):
            failures += 1
    if not args.dry_run:
        refresh_sample_index(args.samples_dir)
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
