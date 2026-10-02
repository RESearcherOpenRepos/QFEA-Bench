#!/usr/bin/env python3
"""Run AutoCodeRover on QuanBench local-issue instances."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.common.io_utils import (  # noqa: E402
    filter_by_instance_id,
    read_json,
    read_json_safely,
    read_jsonl,
)
from benchmark.evaluation.common.output_schema import (  # noqa: E402
    default_agent_metrics,
    normalize_agent_metrics,
    prediction_rows_from_payload,
    trajectory_path,
    write_prediction_files,
    write_trajectory,
)
from benchmark.evaluation.common.model_names import (  # noqa: E402
    prediction_model_name as artifact_model_name,
)
from benchmark.evaluation.common.model_pricing import estimated_cost_usd  # noqa: E402
from benchmark.evaluation.common.patch_candidates import patch_candidate_metadata  # noqa: E402
from benchmark.evaluation.common.run_io import (  # noqa: E402
    append_status_row,
    write_prediction_artifacts,
)
from benchmark.evaluation.common.run_status import row_run_completed  # noqa: E402


DEFAULT_ACR_ROOT = ROOT / "external" / "auto-code-rover"
DEFAULT_INSTANCES = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "autocoderover"
    / "data"
    / "instances"
    / "autocoderover.secure.jsonl"
)
DEFAULT_OUTPUT_DIR = ROOT / "benchmark" / "evaluation" / "autocoderover" / "runs" / "debug"
DEFAULT_CONFIG = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "autocoderover"
    / "config"
    / "deepseek_v4_flash_official.json"
)
RUNTIME_PATCH_DIR = Path(__file__).resolve().parent / "runtime_patch"
DEFAULT_SOURCE_REPO_PATH = "/workspace/repo"
DEFAULT_TIMEOUT_SECONDS = 600
PRED_LOCK = threading.Lock()
ENV_PLACEHOLDER_RE = re.compile(r"\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|(?P<named>[A-Za-z_][A-Za-z0-9_]*))")
ACR_USAGE_RE = re.compile(
    r"input_tokens=(?P<input>\d+),\s*output_tokens=(?P<output>\d+),\s*cost=(?P<cost>[0-9.eE+-]+)"
)


class CommandError(RuntimeError):
    """Raised when a subprocess command fails."""

    def __init__(self, command: list[str], completed: subprocess.CompletedProcess[str]) -> None:
        output = (completed.stdout or "") + (completed.stderr or "")
        super().__init__(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n{output}"
        )
        self.command = command
        self.completed = completed


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise CommandError(command, completed)
    return completed


def expand_env_placeholders(value: Any, *, strict: bool = True) -> Any:
    if isinstance(value, dict):
        return {key: expand_env_placeholders(item, strict=strict) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env_placeholders(item, strict=strict) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        name = match.group("braced") or match.group("named") or ""
        env_value = os.getenv(name)
        if env_value is None:
            env_value = read_zshrc_export(name)
            if env_value is not None:
                os.environ[name] = env_value
        if env_value is None:
            if strict:
                raise RuntimeError(f"Required environment variable {name} is not set.")
            return match.group(0)
        return env_value

    return ENV_PLACEHOLDER_RE.sub(replace, value)


def read_config(path: Path) -> dict[str, Any]:
    config = read_json(path)
    if not isinstance(config, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    return expand_env_placeholders(config, strict=True)


def read_zshrc_export(name: str) -> str | None:
    zshrc = Path.home() / ".zshrc"
    if not zshrc.exists():
        return None
    prefix = f"{name}="
    export_prefix = f"export {name}="
    for line in zshrc.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith(export_prefix):
            value = stripped[len(export_prefix) :]
        elif stripped.startswith(prefix):
            value = stripped[len(prefix) :]
        else:
            continue
        try:
            values = shlex.split(value, comments=True)
        except ValueError:
            return value.split("#", 1)[0].strip().strip("\"'")
        return values[0] if values else ""
    return None


def default_acr_python(acr_root: Path) -> Path:
    candidates = [
        acr_root / ".venv" / "bin" / "python",
        ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def acr_pythonpath(acr_root: Path, existing: str | None = None) -> str:
    entries = [str(RUNTIME_PATCH_DIR), str(acr_root)]
    if existing:
        entries.extend(item for item in existing.split(os.pathsep) if item)
    return os.pathsep.join(entries)


def check_acr_python(acr_python: Path, acr_root: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = acr_pythonpath(acr_root, env.get("PYTHONPATH"))
    check = run_command(
        [
            str(acr_python),
            "-c",
            "import loguru, litellm, natsort; import app.main; print('acr-runtime-ok')",
        ],
        cwd=acr_root,
        env=env,
        check=False,
    )
    if check.returncode != 0:
        output = (check.stdout or "") + (check.stderr or "")
        raise RuntimeError(
            "AutoCodeRover Python environment is not ready. "
            "Create an ACR environment from external/auto-code-rover/requirements.txt "
            "or pass --acr-python pointing to one.\n"
            f"{output}"
        )


def container_name(instance_id: str) -> str:
    digest = hashlib.sha1(f"{instance_id}-{time.time()}-{uuid.uuid4()}".encode()).hexdigest()[:8]
    return f"acr-{instance_id}-{digest}"


def copy_repo_from_image(
    *,
    instance: dict[str, Any],
    repo_dir: Path,
    platform: str,
) -> None:
    image_name = str(instance["image_name"])
    source_repo_path = str(instance.get("source_repo_path") or DEFAULT_SOURCE_REPO_PATH)
    name = container_name(str(instance["instance_id"]))
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--platform",
        str(instance.get("platform") or platform),
        "--entrypoint",
        "sleep",
        image_name,
        "infinity",
    ]
    run_command(command)
    try:
        parent = repo_dir.parent
        if parent.exists():
            shutil.rmtree(parent)
        parent.mkdir(parents=True, exist_ok=True)
        run_command(["docker", "cp", f"{name}:{source_repo_path}", str(parent)])
        copied = parent / Path(source_repo_path).name
        if not copied.exists():
            raise RuntimeError(f"docker cp did not produce expected repo directory: {copied}")
        if copied == repo_dir:
            return
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        copied.rename(repo_dir)
    finally:
        run_command(["docker", "rm", "-f", name], check=False)


def reset_repo(repo_dir: Path, base_commit: str) -> None:
    run_command(["git", "reset", "--hard", base_commit], cwd=repo_dir)
    run_command(["git", "clean", "-fdx"], cwd=repo_dir)
    run_command(["git", "checkout", base_commit], cwd=repo_dir)


def prune_workspace_git(repo_dir: Path) -> bool:
    git_path = repo_dir / ".git"
    if not git_path.exists():
        return False
    if git_path.is_dir() and not git_path.is_symlink():
        shutil.rmtree(git_path)
    else:
        git_path.unlink()
    return True


def write_task_spec(instance_dir: Path, instance: dict[str, Any]) -> Path:
    task_spec = str(instance.get("task_spec") or "").strip()
    if not task_spec:
        raise ValueError(f"Instance {instance.get('instance_id')} is missing task_spec")
    path = instance_dir / "task_spec.txt"
    path.write_text(task_spec + "\n", encoding="utf-8")
    return path


def acr_env(config: dict[str, Any], acr_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = acr_pythonpath(acr_root, env.get("PYTHONPATH"))
    env["ACR_OVERALL_RETRY_LIMIT"] = str(config.get("overall_retry_limit", 3))
    for key, value in (config.get("env") or {}).items():
        env[str(key)] = str(value)
    return env


def run_acr(
    *,
    acr_python: Path,
    acr_root: Path,
    config: dict[str, Any],
    instance: dict[str, Any],
    repo_dir: Path,
    task_spec_path: Path,
    acr_output_dir: Path,
    log_path: Path,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(acr_python),
        "app/main.py",
        "local-issue",
        "--output-dir",
        str(acr_output_dir.absolute()),
        "--model",
        str(config["model"]),
        "--model-temperature",
        str(config.get("model_temperature", 0.0)),
        "--conv-round-limit",
        str(config.get("conv_round_limit", 15)),
        "--num-processes",
        "1",
        "--task-id",
        str(instance["instance_id"]),
        "--local-repo",
        str(repo_dir.absolute()),
        "--issue-file",
        str(task_spec_path.absolute()),
        "--no-print",
    ]
    completed = run_command(
        command,
        cwd=acr_root,
        env=acr_env(config, acr_root),
        timeout=timeout,
        check=False,
    )
    log_path.write_text((completed.stdout or "") + (completed.stderr or ""), encoding="utf-8")
    return completed


def parse_acr_internal_error(log_text: str) -> str | None:
    """Return the ACR task-level exception even when ACR exits with status 0."""
    lines = log_text.splitlines()
    for index, line in enumerate(lines):
        if " failed with exception:" not in line:
            continue
        details = [line.strip()]
        for follow in lines[index + 1 : index + 4]:
            stripped = follow.strip()
            if not stripped:
                break
            details.append(stripped)
        return " ".join(details)
    return None


def latest_task_output_dir(acr_output_dir: Path, instance_id: str) -> Path | None:
    candidates = [
        path
        for path in acr_output_dir.glob(f"{instance_id}_*")
        if path.is_dir()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def selected_patch_path(task_output_dir: Path | None) -> Path | None:
    if task_output_dir is None:
        return None
    selection = task_output_dir / "selected_patch.json"
    if not selection.exists():
        return None
    data = read_json_safely(selection)
    if not isinstance(data, dict):
        return None
    selected = data.get("selected_patch")
    if not selected:
        return None
    path = task_output_dir / str(selected)
    return path if path.exists() else None


def read_patch(task_output_dir: Path | None) -> tuple[str, str | None]:
    path = selected_patch_path(task_output_dir)
    if path is None:
        return "", None
    return path.read_text(encoding="utf-8", errors="ignore"), str(path)


def count_conversation_steps(task_output_dir: Path | None) -> int:
    if task_output_dir is None:
        return 0
    count = 0
    for path in task_output_dir.glob("**/conv_*.json"):
        data = read_json_safely(path)
        if isinstance(data, list):
            count += sum(1 for item in data if isinstance(item, dict) and item.get("role") == "assistant")
        elif isinstance(data, dict):
            messages = data.get("messages") or data.get("thread") or []
            if isinstance(messages, list):
                count += sum(
                    1
                    for item in messages
                    if isinstance(item, dict) and item.get("role") in {"assistant", "model"}
                )
            else:
                count += 1
        else:
            count += 1
    return count


def parse_acr_usage(task_output_dir: Path | None) -> dict[str, int | float]:
    usage: dict[str, int | float] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "instance_cost": 0.0,
    }
    if task_output_dir is None:
        return usage
    info_log = task_output_dir / "info.log"
    if not info_log.exists():
        return usage
    for match in ACR_USAGE_RE.finditer(info_log.read_text(encoding="utf-8", errors="ignore")):
        usage["input_tokens"] = int(usage["input_tokens"]) + int(match.group("input"))
        usage["output_tokens"] = int(usage["output_tokens"]) + int(match.group("output"))
        usage["instance_cost"] = float(usage["instance_cost"]) + float(match.group("cost"))
    return usage


def parse_acr_extract_statuses(task_output_dir: Path | None) -> list[str]:
    if task_output_dir is None:
        return []
    statuses: list[str] = []
    for status_path in task_output_dir.glob("**/extract_status.json"):
        data = read_json_safely(status_path)
        if not isinstance(data, dict):
            continue
        statuses.extend(
            str(status)
            for status in data.get("extract_status", [])
            if isinstance(status, str)
        )
    return statuses


def extract_agent_metrics(
    *,
    task_output_dir: Path | None,
    patch: str,
    returncode: int | None,
    model_name: str | None = None,
) -> dict[str, Any]:
    agent = default_agent_metrics()
    cost = read_json_safely(task_output_dir / "cost.json") if task_output_dir else None
    if not isinstance(cost, dict):
        cost = {}
    usage = parse_acr_usage(task_output_dir)
    patch_candidate = patch_candidate_metadata(
        model_patch=patch,
        extraction_statuses=parse_acr_extract_statuses(task_output_dir),
    )
    submitted = bool(patch_candidate["patch_candidate_submitted"])
    input_tokens = int(cost.get("total_input_tokens") or usage["input_tokens"] or 0)
    output_tokens = int(cost.get("total_output_tokens") or usage["output_tokens"] or 0)
    instance_cost = cost.get("total_cost", usage["instance_cost"])
    estimated_instance_cost = estimated_cost_usd(
        model_name,
        {
            "input_tokens": input_tokens,
            "cached_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": output_tokens,
        },
    )
    if estimated_instance_cost is not None and estimated_instance_cost > 0:
        instance_cost = round(estimated_instance_cost, 6)
    agent.update(
        {
            "steps": count_conversation_steps(task_output_dir),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "instance_cost": instance_cost,
            "success": submitted,
            "run_completed": returncode == 0,
            "exit_status": "Submitted" if submitted else "NoPatch" if returncode == 0 else "error",
            "cached_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            **patch_candidate,
        }
    )
    return normalize_agent_metrics(agent)


def append_output_row(output_dir: Path, row: dict[str, Any]) -> None:
    path = output_dir / "output.jsonl"
    with PRED_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def completed_summary(instance_dir: Path, instance_id: str) -> bool:
    summary = read_json_safely(instance_dir / f"{instance_id}.summary.json")
    if not isinstance(summary, dict):
        return False
    agent = summary.get("agent")
    return isinstance(agent, dict) and bool(agent.get("run_completed"))


def pending_prediction_ids(output_dir: Path, selected_instance_ids: set[str]) -> set[str]:
    """Return selected ids that are missing from preds.json or not counted as success."""
    preds_path = output_dir / "preds.json"
    if not preds_path.exists():
        return set(selected_instance_ids)
    rows = enrich_prediction_rows_with_acr_status(output_dir)
    return {
        instance_id
        for instance_id in selected_instance_ids
        if instance_id not in rows or not row_run_completed(rows[instance_id])
    }


def existing_task_output_dir(output_dir: Path, instance_id: str) -> Path | None:
    traj = read_json_safely(trajectory_path(output_dir / instance_id, instance_id))
    if isinstance(traj, dict):
        raw_output = traj.get("raw_output")
        metrics = raw_output.get("metrics") if isinstance(raw_output, dict) else None
        task_output_dir = metrics.get("task_output_dir") if isinstance(metrics, dict) else None
        if task_output_dir and Path(task_output_dir).exists():
            return Path(task_output_dir)
    return latest_task_output_dir(output_dir / instance_id / "acr_output", instance_id)


def existing_acr_patch_candidate_metadata(output_dir: Path, instance_id: str) -> dict[str, Any]:
    task_output_dir = existing_task_output_dir(output_dir, instance_id)
    return patch_candidate_metadata(
        extraction_statuses=parse_acr_extract_statuses(task_output_dir),
    )


def sync_status_rows_with_predictions(output_dir: Path, rows: dict[str, dict[str, Any]]) -> None:
    """Keep status.jsonl aligned with preds.json after candidate-status enrichment."""
    status_path = output_dir / "status.jsonl"
    existing_rows: dict[str, dict[str, Any]] = {}
    if status_path.exists():
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            instance_id = row.get("instance_id")
            if instance_id:
                existing_rows[str(instance_id)] = row

    synced_rows: list[dict[str, Any]] = []
    for instance_id, prediction_row in rows.items():
        status_row = dict(existing_rows.get(instance_id) or {"instance_id": instance_id})
        completed = row_run_completed(prediction_row)
        status_row["success"] = bool(completed)
        status_row["run_completed"] = bool(completed)
        status_row.setdefault("error", None)
        status_row.setdefault("elapsed_seconds", None)
        synced_rows.append(status_row)

    if not synced_rows:
        return
    with PRED_LOCK:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in synced_rows),
            encoding="utf-8",
        )


def enrich_prediction_rows_with_acr_status(output_dir: Path) -> dict[str, dict[str, Any]]:
    preds_path = output_dir / "preds.json"
    rows = prediction_rows_from_payload(read_json(preds_path))
    changed = False
    for instance_id, row in rows.items():
        if str(row.get("model_patch") or "").strip() or row.get("patch_candidate_submitted"):
            continue
        metadata = existing_acr_patch_candidate_metadata(output_dir, instance_id)
        if not metadata.get("patch_candidate_submitted"):
            continue
        row["patch_candidate_submitted"] = True
        row["patch_extraction_status"] = metadata.get("patch_extraction_status")
        changed = True
    if changed:
        write_prediction_files(output_dir, list(rows.values()))
        rows = prediction_rows_from_payload(read_json(preds_path))
    sync_status_rows_with_predictions(output_dir, rows)
    return rows


def filter_pending_instances(
    instances: list[dict[str, Any]],
    pending_ids: set[str],
) -> list[dict[str, Any]]:
    return [
        instance
        for instance in instances
        if str(instance["instance_id"]) in pending_ids
    ]


def evaluate_instance(
    instance: dict[str, Any],
    *,
    acr_python: Path,
    acr_root: Path,
    config: dict[str, Any],
    output_dir: Path,
    platform: str,
    timeout: int,
    force: bool,
    keep_workspace_git: bool = False,
) -> dict[str, Any]:
    instance_id = str(instance["instance_id"])
    instance_dir = output_dir / instance_id
    instance_dir.mkdir(parents=True, exist_ok=True)
    if not force and completed_summary(instance_dir, instance_id):
        return {"instance_id": instance_id, "skipped": True}

    repo_dir = instance_dir / "workspace" / "repo"
    acr_output_dir = instance_dir / "acr_output"
    log_path = instance_dir / "autocoderover.log"
    task_spec_path = write_task_spec(instance_dir, instance)

    error: str | None = None
    completed: subprocess.CompletedProcess[str] | None = None
    task_output_dir: Path | None = None
    patch = ""
    patch_path: str | None = None
    timed_out = False
    started = time.time()
    try:
        copy_repo_from_image(instance=instance, repo_dir=repo_dir, platform=platform)
        reset_repo(repo_dir, str(instance["base_commit"]))
        if acr_output_dir.exists():
            shutil.rmtree(acr_output_dir)
        acr_output_dir.mkdir(parents=True, exist_ok=True)
        completed = run_acr(
            acr_python=acr_python,
            acr_root=acr_root,
            config=config,
            instance=instance,
            repo_dir=repo_dir,
            task_spec_path=task_spec_path,
            acr_output_dir=acr_output_dir,
            log_path=log_path,
            timeout=timeout,
        )
        task_output_dir = latest_task_output_dir(acr_output_dir, instance_id)
        patch, patch_path = read_patch(task_output_dir)
        if completed.returncode != 0:
            error = f"AutoCodeRover exited with code {completed.returncode}"
        elif not patch.strip():
            acr_internal_error = parse_acr_internal_error(log_path.read_text(encoding="utf-8"))
            if acr_internal_error:
                error = f"AutoCodeRover internal failure: {acr_internal_error}"
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        error = f"AutoCodeRover timed out after {timeout} seconds"
        stdout = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        log_text = "\n".join(part for part in [stdout, stderr, error] if part)
        log_path.write_text(log_text + "\n", encoding="utf-8")
    except Exception as exc:
        error = str(exc)
        log_path.write_text(error + "\n", encoding="utf-8")

    if task_output_dir is None:
        task_output_dir = latest_task_output_dir(acr_output_dir, instance_id)
    if not patch:
        patch, patch_path = read_patch(task_output_dir)

    elapsed = time.time() - started
    returncode = completed.returncode if completed is not None else None
    agent = extract_agent_metrics(
        task_output_dir=task_output_dir,
        patch=patch,
        returncode=returncode,
        model_name=str(config.get("prediction_model_name") or config.get("model") or ""),
    )
    agent["run_completed"] = bool(agent["run_completed"] and error is None)
    if timed_out and not patch.strip():
        agent["run_completed"] = True
        agent["success"] = False
        agent["timed_out"] = True
        agent["exit_status"] = "TimedOut"
        agent["error"] = error
    elif error is not None and not patch.strip():
        agent["success"] = False
        agent["exit_status"] = "error"
        agent["error"] = error

    row = {
        "instance_id": instance_id,
        "test_result": {
            "git_patch": patch,
            "selected_patch_path": patch_path,
            "patch_candidate_submitted": bool(agent.get("patch_candidate_submitted")),
            "patch_extraction_status": agent.get("patch_extraction_status"),
        },
        "error": error,
        "returncode": returncode,
        "elapsed_seconds": elapsed,
        "instance": instance,
        "metrics": {
            "task_output_dir": str(task_output_dir) if task_output_dir else None,
        },
    }
    append_output_row(output_dir, row)
    write_trajectory(
        trajectory_path(instance_dir, instance_id),
        {
            "schema_version": 1,
            "framework": "autocoderover",
            "instance_id": instance_id,
            "agent": agent,
            "raw_output": row,
        },
    )
    prediction = write_prediction_artifacts(
        output_dir,
        framework="autocoderover",
        instance_id=instance_id,
        model_name=artifact_model_name(config.get("prediction_model_name") or config["model"]),
        patch=patch,
        agent=agent,
        lock=PRED_LOCK,
    )
    append_status_row(
        output_dir,
        {
            "instance_id": instance_id,
            "success": bool(agent.get("success")),
            "run_completed": bool(agent.get("run_completed")),
            "error": error,
            "elapsed_seconds": elapsed,
        },
        lock=PRED_LOCK,
    )
    if not keep_workspace_git:
        try:
            prune_workspace_git(repo_dir)
        except OSError as exc:
            print(f"ACR_WORKSPACE_GIT_CLEANUP_FAILED instance={instance_id} error={exc}", flush=True)
    return prediction


def progress_status(result: dict[str, Any]) -> str:
    if result.get("skipped"):
        return "skipped"
    agent = result.get("_agent")
    if isinstance(agent, dict) and agent.get("exit_status"):
        return str(agent["exit_status"])
    if result.get("model_patch"):
        return "Submitted"
    return "unknown"


def apply_n_limit_selection(args: argparse.Namespace) -> None:
    if args.n_limit is not None and args.n_limit > 0:
        if args.slice:
            raise ValueError("Use either --slice or --n-limit, not both")
        args.slice = f"0:{args.n_limit}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AutoCodeRover on QuanBench instances.")
    parser.add_argument("--instances", type=Path, default=DEFAULT_INSTANCES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--config-file", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--acr-root", type=Path, default=DEFAULT_ACR_ROOT)
    parser.add_argument("--acr-python", type=Path, default=None)
    parser.add_argument("--num-workers", "--workers", dest="workers", type=int, default=1)
    parser.add_argument("--num-worksers", dest="workers", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--platform", default="linux/amd64")
    parser.add_argument("--select", default=None, help="Regex selecting instance ids.")
    parser.add_argument("--slice", default=None, help="Python slice syntax, e.g. 0:5.")
    parser.add_argument("--n-limit", type=int, default=None, help="Run the first N selected instances.")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Rerun instances with completed summaries.")
    parser.add_argument(
        "--keep-workspace-git",
        action="store_true",
        help="Keep per-instance workspace/repo/.git directories after writing run artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.instances = args.instances.absolute()
    args.config_file = args.config_file.absolute()
    args.output_dir = args.output_dir.absolute()
    apply_n_limit_selection(args)
    config = read_config(args.config_file)
    acr_python = (args.acr_python or default_acr_python(args.acr_root)).absolute()
    args.acr_root = args.acr_root.resolve()
    check_acr_python(acr_python, args.acr_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    instances = filter_by_instance_id(read_jsonl(args.instances), args.select, args.slice)
    resume_from_preds = not args.force and (args.output_dir / "preds.json").exists()
    resume_pending_ids: set[str] = set()
    if resume_from_preds:
        selected_ids = {str(instance["instance_id"]) for instance in instances}
        resume_pending_ids = pending_prediction_ids(args.output_dir, selected_ids)
        before_count = len(instances)
        instances = filter_pending_instances(instances, resume_pending_ids)
        matched_ids = {str(instance["instance_id"]) for instance in instances}
        skipped_by_selection_ids = sorted(resume_pending_ids - matched_ids)
        print(
            "ACR_RESUME_PENDING "
            f"pending={len(resume_pending_ids)} "
            f"selected_before={before_count} selected_after={len(instances)}",
            flush=True,
        )
        if skipped_by_selection_ids:
            print(
                "ACR_RESUME_PENDING_SKIPPED_BY_SELECTION "
                + ",".join(skipped_by_selection_ids),
                flush=True,
            )
    timeout = int(args.timeout or config.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)

    metadata = {
        "framework": "autocoderover",
        "instances": str(args.instances),
        "config_file": str(args.config_file),
        "acr_root": str(args.acr_root),
        "acr_python": str(acr_python),
        "workers": args.workers,
        "platform": args.platform,
        "timeout_seconds": timeout,
        "model": config.get("model"),
        "prediction_model_name": config.get("prediction_model_name"),
        "task_input_policy": "problem_statement+requirements+interface only",
        "resume_policy": (
            "force_all_selected"
            if args.force
            else "selected_minus_success"
            if resume_from_preds
            else "run_selected"
        ),
        "resume_pending_ids": sorted(resume_pending_ids),
        "workspace_git_policy": "keep" if args.keep_workspace_git else "remove_after_artifacts",
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Running {len(instances)} AutoCodeRover instances. Output: {args.output_dir}", flush=True)
    if args.workers <= 1:
        for instance in instances:
            print(f"ACR_START instance={instance['instance_id']}", flush=True)
            result = evaluate_instance(
                instance,
                acr_python=acr_python,
                acr_root=args.acr_root,
                config=config,
                output_dir=args.output_dir,
                platform=args.platform,
                timeout=timeout,
                force=bool(args.force or resume_from_preds),
                keep_workspace_git=args.keep_workspace_git,
            )
            print(
                f"ACR_PROGRESS instance={instance['instance_id']} result={progress_status(result)}",
                flush=True,
            )
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    evaluate_instance,
                    instance,
                    acr_python=acr_python,
                    acr_root=args.acr_root,
                    config=config,
                    output_dir=args.output_dir,
                    platform=args.platform,
                    timeout=timeout,
                    force=bool(args.force or resume_from_preds),
                    keep_workspace_git=args.keep_workspace_git,
                )
                for instance in instances
            ]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                print(
                    f"ACR_PROGRESS instance={result.get('instance_id')} result={progress_status(result)}",
                    flush=True,
                )

    print(
        json.dumps(
            {
                "output_json": str(args.output_dir / "output.jsonl"),
                "preds_json": str(args.output_dir / "preds.json"),
                "preds_jsonl": str(args.output_dir / "preds.jsonl"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
