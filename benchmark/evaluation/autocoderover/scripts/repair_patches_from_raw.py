#!/usr/bin/env python3
"""Re-extract AutoCodeRover patches from saved raw model responses.

This repairs post-processing artifacts without rerunning the model. It is useful
when runtime extraction compatibility changes, for example to include new files
from <original></original> edit blocks in the final git diff.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT_DIR = ROOT / "benchmark" / "evaluation" / "autocoderover" / "runs" / "gpt55_20260625"
DEFAULT_ACR_ROOT = ROOT / "external" / "auto-code-rover"
RUNTIME_PATCH_DIR = Path(__file__).resolve().parent / "runtime_patch"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_runtime_patch(acr_root: Path) -> None:
    for path in (RUNTIME_PATCH_DIR, acr_root):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    patch_path = RUNTIME_PATCH_DIR / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location("quanbench_acr_runtime_patch", patch_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load runtime patch from {patch_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def raw_patch_index(path: Path) -> int:
    match = re.search(r"patch_raw_(\d+)(?:\.md)?$", path.name)
    if match:
        return int(match.group(1))
    match = re.search(r"agent_patch_raw_(\d+)$", path.name)
    if match:
        return int(match.group(1))
    raise ValueError(f"Cannot parse raw patch index from {path}")


def raw_patch_files(output_subdir: Path) -> list[Path]:
    files = list(output_subdir.glob("patch_raw_*.md")) + list(output_subdir.glob("agent_patch_raw_*"))
    return sorted(files, key=raw_patch_index)


def latest_task_output_dir(instance_dir: Path, instance_id: str) -> Path | None:
    acr_output_dir = instance_dir / "acr_output"
    candidates = [path for path in acr_output_dir.glob(f"{instance_id}_*") if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def selected_patch_path(task_output_dir: Path | None) -> Path | None:
    if task_output_dir is None:
        return None
    selection_path = task_output_dir / "selected_patch.json"
    if not selection_path.exists():
        return None
    selection = read_json(selection_path)
    if not isinstance(selection, dict):
        return None
    selected = selection.get("selected_patch")
    if not selected:
        return None
    patch_path = task_output_dir / str(selected)
    return patch_path if patch_path.exists() else None


def read_patch(task_output_dir: Path | None) -> tuple[str, str | None]:
    path = selected_patch_path(task_output_dir)
    if path is None:
        return "", None
    return path.read_text(encoding="utf-8", errors="ignore"), str(path)


def load_metadata_model_name(output_dir: Path) -> str:
    metadata_path = output_dir / "metadata.json"
    if not metadata_path.exists():
        return ""
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        return ""
    return str(
        metadata.get("prediction_model_name")
        or metadata.get("model")
        or ""
    )


def reextract_task(task_output_dir: Path) -> dict[str, Any]:
    from app.post_process import convert_response_to_diff

    changed_files = 0
    statuses_by_output: dict[str, list[str]] = {}
    for output_subdir in sorted(task_output_dir.glob("output_*")):
        if not output_subdir.is_dir():
            continue
        statuses: list[str] = []
        for raw_path in raw_patch_files(output_subdir):
            index = raw_patch_index(raw_path)
            status, _message, diff = convert_response_to_diff(
                raw_path.read_text(encoding="utf-8", errors="ignore"),
                str(output_subdir),
                standalone_mode=True,
            )
            status_value = status.value if hasattr(status, "value") else str(status)
            statuses.append(status_value)
            extracted_path = output_subdir / f"extracted_patch_{index}.diff"
            old_diff = extracted_path.read_text(encoding="utf-8", errors="ignore") if extracted_path.exists() else ""
            if diff != old_diff:
                extracted_path.write_text(diff, encoding="utf-8")
                changed_files += 1
        if statuses:
            status_path = output_subdir / "extract_status.json"
            old_statuses = read_json(status_path).get("extract_status", []) if status_path.exists() else []
            if old_statuses != statuses:
                write_json(status_path, {"extract_status": statuses})
                changed_files += 1
            statuses_by_output[output_subdir.name] = statuses
    return {"changed_files": changed_files, "statuses_by_output": statuses_by_output}


def repair_meta_repo_paths(task_output_dir: Path, repo_dir: Path) -> int:
    """Point stale ACR meta repo_path values at this run's workspace repo."""
    if not repo_dir.exists():
        return 0

    changed = 0
    for meta_path in [task_output_dir / "meta.json", *task_output_dir.glob("output_*/meta.json")]:
        if not meta_path.exists():
            continue
        data = read_json(meta_path)
        if not isinstance(data, dict):
            continue
        setup_info = data.get("setup_info")
        if not isinstance(setup_info, dict):
            continue
        current = setup_info.get("repo_path")
        if current and Path(str(current)).exists():
            continue
        setup_info["repo_path"] = str(repo_dir.resolve())
        write_json(meta_path, data)
        changed += 1
    return changed


def load_existing_rows(output_dir: Path) -> dict[str, dict[str, Any]]:
    from benchmark.evaluation.common.output_schema import prediction_rows_from_payload

    preds_path = output_dir / "preds.json"
    if not preds_path.exists():
        return {}
    return prediction_rows_from_payload(read_json(preds_path))


def update_prediction_artifacts(
    *,
    output_dir: Path,
    instance_id: str,
    task_output_dir: Path | None,
    model_name: str,
    existing_row: dict[str, Any] | None,
) -> dict[str, Any]:
    from benchmark.evaluation.autocoderover.scripts.run_autocoderover import (
        artifact_model_name,
        extract_agent_metrics,
    )
    from benchmark.evaluation.common.output_schema import (
        prediction_row,
        trajectory_path,
        write_summary,
        write_trajectory,
    )

    instance_dir = output_dir / instance_id
    patch, patch_path = read_patch(task_output_dir)
    old_agent = {}
    summary_path = instance_dir / f"{instance_id}.summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        if isinstance(summary, dict) and isinstance(summary.get("agent"), dict):
            old_agent = summary["agent"]

    returncode = 0 if old_agent.get("run_completed") else None
    agent = extract_agent_metrics(
        task_output_dir=task_output_dir,
        patch=patch,
        returncode=returncode,
        model_name=model_name,
    )
    if old_agent:
        agent["run_completed"] = bool(old_agent.get("run_completed"))
        agent["timed_out"] = bool(old_agent.get("timed_out"))
        agent["repeated_command_loop"] = bool(old_agent.get("repeated_command_loop"))
        agent["step_budget_exhausted"] = bool(old_agent.get("step_budget_exhausted"))
        agent["error"] = old_agent.get("error")

    write_summary(
        summary_path,
        framework="autocoderover",
        instance_id=instance_id,
        agent=agent,
    )

    traj_path = trajectory_path(instance_dir, instance_id)
    if traj_path.exists():
        trajectory = read_json(traj_path)
        if isinstance(trajectory, dict):
            raw_output = trajectory.get("raw_output")
            if not isinstance(raw_output, dict):
                raw_output = {}
            test_result = raw_output.get("test_result")
            if not isinstance(test_result, dict):
                test_result = {}
            test_result.update(
                {
                    "git_patch": patch,
                    "selected_patch_path": patch_path,
                    "patch_candidate_submitted": bool(agent.get("patch_candidate_submitted")),
                    "patch_extraction_status": agent.get("patch_extraction_status"),
                }
            )
            raw_output["test_result"] = test_result
            metrics = raw_output.get("metrics")
            if not isinstance(metrics, dict):
                metrics = {}
            metrics["task_output_dir"] = str(task_output_dir) if task_output_dir else None
            raw_output["metrics"] = metrics
            trajectory["raw_output"] = raw_output
            trajectory["agent"] = agent
            write_trajectory(traj_path, trajectory)

    model_name_or_path = (
        str((existing_row or {}).get("model_name_or_path") or "")
        or artifact_model_name(model_name)
    )
    return prediction_row(
        model_name_or_path=model_name_or_path,
        instance_id=instance_id,
        model_patch=patch,
        agent=agent,
    )


def update_output_jsonl(
    output_dir: Path,
    repaired_rows: dict[str, dict[str, Any]],
    task_dirs: dict[str, Path | None],
) -> None:
    output_path = output_dir / "output.jsonl"
    if not output_path.exists():
        return
    rows: list[dict[str, Any]] = []
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        instance_id = str(row.get("instance_id") or "")
        repaired = repaired_rows.get(instance_id)
        if repaired is not None:
            test_result = row.get("test_result")
            if not isinstance(test_result, dict):
                test_result = {}
            test_result.update(
                {
                    "git_patch": repaired.get("model_patch", ""),
                    "patch_candidate_submitted": bool(repaired.get("patch_candidate_submitted")),
                    "patch_extraction_status": repaired.get("patch_extraction_status"),
                }
            )
            patch_path = selected_patch_path(task_dirs.get(instance_id))
            test_result["selected_patch_path"] = str(patch_path) if patch_path else None
            row["test_result"] = test_result
            metrics = row.get("metrics")
            if not isinstance(metrics, dict):
                metrics = {}
            task_dir = task_dirs.get(instance_id)
            metrics["task_output_dir"] = str(task_dir) if task_dir else None
            row["metrics"] = metrics
        rows.append(row)
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def repair_run(output_dir: Path, acr_root: Path, selected_ids: set[str] | None = None) -> dict[str, Any]:
    from benchmark.evaluation.common.output_schema import write_prediction_files

    load_runtime_patch(acr_root)
    model_name = load_metadata_model_name(output_dir)
    existing_rows = load_existing_rows(output_dir)
    if selected_ids is None:
        selected_ids = set(existing_rows) if existing_rows else {
            path.name for path in output_dir.iterdir() if path.is_dir() and path.name != "logs"
        }

    repaired_rows: dict[str, dict[str, Any]] = {}
    task_dirs: dict[str, Path | None] = {}
    reextracted = 0
    changed_files = 0
    new_file_patches = 0
    for instance_id in sorted(selected_ids):
        instance_dir = output_dir / instance_id
        if not instance_dir.is_dir():
            continue
        task_output_dir = latest_task_output_dir(instance_dir, instance_id)
        task_dirs[instance_id] = task_output_dir
        if task_output_dir is not None:
            changed_files += repair_meta_repo_paths(task_output_dir, instance_dir / "workspace" / "repo")
            reextract_info = reextract_task(task_output_dir)
            reextracted += 1
            changed_files += int(reextract_info["changed_files"])
        repaired = update_prediction_artifacts(
            output_dir=output_dir,
            instance_id=instance_id,
            task_output_dir=task_output_dir,
            model_name=model_name,
            existing_row=existing_rows.get(instance_id),
        )
        if "new file mode" in repaired.get("model_patch", "") or "--- /dev/null" in repaired.get("model_patch", ""):
            new_file_patches += 1
        repaired_rows[instance_id] = repaired

    merged_rows = dict(existing_rows)
    merged_rows.update(repaired_rows)
    ordered_rows = [merged_rows[key] for key in merged_rows]
    write_prediction_files(output_dir, ordered_rows)
    update_output_jsonl(output_dir, repaired_rows, task_dirs)
    return {
        "instances_selected": len(selected_ids),
        "instances_repaired": len(repaired_rows),
        "task_outputs_reextracted": reextracted,
        "changed_files": changed_files,
        "new_file_patches": new_file_patches,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--acr-root", type=Path, default=DEFAULT_ACR_ROOT)
    parser.add_argument(
        "--instances",
        nargs="*",
        help="Optional instance ids to repair. Defaults to all predictions in the run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_ids = set(args.instances) if args.instances else None
    summary = repair_run(
        output_dir=args.output_dir,
        acr_root=args.acr_root,
        selected_ids=selected_ids,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
