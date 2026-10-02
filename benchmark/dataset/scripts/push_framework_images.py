#!/usr/bin/env python3
"""Push framework runtime images to a container registry."""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timedelta, timezone
import json
import subprocess
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOG = ROOT / "benchmark" / "dataset" / "build_logs" / "dockerhub_push_framework_images.log"
DEFAULT_PROGRESS = ROOT / "benchmark" / "dataset" / "build_logs" / "dockerhub_push_framework_images_progress.jsonl"
DEFAULT_STATE = ROOT / "benchmark" / "dataset" / "build_logs" / "dockerhub_push_framework_images_state.json"
DEFAULT_FRAMEWORK_PREFIXES = {
    "minisweagent": "benchmark-minisweagent-",
    "openhands": "benchmark-openhands-",
    "traeagent": "benchmark-traeagent-",
}
AGENT_BASE_FRAMEWORK = "agent-base"
AGENT_BASE_REPO = "benchmark-agent-base"
EVENT_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push benchmark framework images, skipping remote tags that already exist."
    )
    parser.add_argument("--repo", default="arthurshy/quanbench", help="Remote registry repo, e.g. arthurshy/quanbench.")
    parser.add_argument(
        "--framework",
        action="append",
        choices=sorted([*DEFAULT_FRAMEWORK_PREFIXES, AGENT_BASE_FRAMEWORK]),
        help="Framework to push. Can be repeated. Defaults to all three framework images.",
    )
    parser.add_argument("--tag", default="latest", help="Local image tag to push.")
    parser.add_argument("--filter", default=None, help="Substring filter over sample_id.")
    parser.add_argument("--progress-jsonl", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--reset-progress", action="store_true", help="Deprecated: progress JSONL is reset by default.")
    parser.add_argument("--append-progress", action="store_true", help="Append to progress JSONL instead of resetting it.")
    parser.add_argument("--reset-state", action="store_true", help="Ignore and overwrite existing resume state.")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip tags marked pushed in --state-json.")
    parser.add_argument(
        "--no-remote-precheck",
        action="store_true",
        help="Do not check remote tags for items missing from resume state before pushing.",
    )
    parser.add_argument("--no-final-check", action="store_true", help="Skip final remote manifest verification.")
    parser.add_argument("--retry-limit", type=int, default=6)
    parser.add_argument("--retry-delay", type=int, default=20, help="Base retry delay in seconds.")
    parser.add_argument("--push-timeout", type=int, default=900, help="Per-attempt docker push timeout in seconds.")
    parser.add_argument("--workers", type=int, default=1, help="Number of image tags to push concurrently.")
    parser.add_argument(
        "--exclude-tag",
        action="append",
        default=[],
        help="Remote tag name to skip, for example openhands-openfermion_752_753. Can be repeated.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, object]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + f".{time.time_ns()}.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def initial_state(path: Path, *, reset: bool) -> dict[str, object]:
    if reset:
        return {"schema_version": 1, "tags": {}}
    state = read_json(path)
    tags = state.get("tags")
    if not isinstance(tags, dict):
        state["tags"] = {}
    state.setdefault("schema_version", 1)
    return state


def state_tags(state: dict[str, object]) -> dict[str, dict[str, object]]:
    tags = state.setdefault("tags", {})
    if not isinstance(tags, dict):
        state["tags"] = {}
        tags = state["tags"]
    return tags  # type: ignore[return-value]


def item_state_key(item: dict[str, str]) -> str:
    return item["remote"]


def state_record_matches(record: object, item: dict[str, str]) -> bool:
    if not isinstance(record, dict):
        return False
    return (
        record.get("status") == "pushed"
        and record.get("image_id") == item.get("image_id")
        and record.get("local") == item.get("local")
    )


def update_state(
    state_path: Path,
    state: dict[str, object],
    item: dict[str, str],
    *,
    status: str,
    error: str | None = None,
    verified: bool | None = None,
) -> None:
    with STATE_LOCK:
        tags = state_tags(state)
        record = {
            "status": status,
            "framework": item["framework"],
            "sample_id": item["sample_id"],
            "local": item["local"],
            "remote": item["remote"],
            "image_id": item["image_id"],
            "size": item["size"],
            "updated_at": now_iso(),
        }
        if error:
            record["error"] = error
        if verified is not None:
            record["verified"] = verified
            record["verified_at"] = now_iso()
        tags[item_state_key(item)] = record
        write_json(state_path, state)


def docker_images() -> list[dict[str, str]]:
    output = subprocess.check_output(
        ["docker", "images", "--format", "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"],
        text=True,
    )
    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        rows.append({"repo": parts[0], "tag": parts[1], "image_id": parts[2], "size": parts[3]})
    return rows


def collect_items(remote_repo: str, frameworks: list[str], local_tag: str) -> list[dict[str, str]]:
    rows = docker_images()
    items = []
    seen = set()
    for row in rows:
        for framework in frameworks:
            if framework == AGENT_BASE_FRAMEWORK:
                if row["repo"] != AGENT_BASE_REPO or row["tag"] in {"<none>", ""}:
                    continue
                sample_id = row["tag"]
                key = (framework, sample_id)
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    {
                        "framework": framework,
                        "sample_id": sample_id,
                        "local": f'{row["repo"]}:{row["tag"]}',
                        "remote": f"{remote_repo}:{framework}-{sample_id}",
                        "image_id": row["image_id"],
                        "size": row["size"],
                    }
                )
                continue
            if row["tag"] != local_tag:
                continue
            prefix = DEFAULT_FRAMEWORK_PREFIXES[framework]
            if not row["repo"].startswith(prefix):
                continue
            sample_id = row["repo"][len(prefix) :]
            key = (framework, sample_id)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "framework": framework,
                    "sample_id": sample_id,
                    "local": f'{row["repo"]}:{local_tag}',
                    "remote": f"{remote_repo}:{framework}-{sample_id}",
                    "image_id": row["image_id"],
                    "size": row["size"],
                }
            )
    return sorted(items, key=lambda item: (item["framework"], item["sample_id"]))


def write_event(progress_path: Path, **event: object) -> None:
    event.setdefault("ts", now_iso())
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOCK:
        with progress_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")


def remote_exists(remote: str) -> bool:
    completed = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", remote],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def run_push(remote: str, log_path: Path, timeout: int, index: int, total: int, attempt: int) -> tuple[bool, str | None]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n===== PUSH {index}/{total} attempt {attempt} {remote} =====\n")
        log_file.flush()
        try:
            completed = subprocess.run(
                ["docker", "push", remote],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            log_file.write(f"\nTIMEOUT after {timeout}s\n")
            return False, "timeout"
    if completed.returncode == 0:
        return True, None
    return False, f"exit_{completed.returncode}"


def push_one(index: int, total: int, item: dict[str, str], args: argparse.Namespace) -> dict[str, object]:
    print(f'[{index}/{total}] {item["remote"]} ({item["size"]})', flush=True)
    write_event(args.progress_jsonl, event="begin", index=index, total=total, **item)
    if args.dry_run:
        return {"status": "dry_run", "retried": 0}

    subprocess.run(["docker", "tag", item["local"], item["remote"]], check=True)

    last_error = None
    retried = 0
    for attempt in range(1, args.retry_limit + 1):
        if attempt > 1:
            retried += 1
            delay = min(120, args.retry_delay * attempt)
            print(f"[{index}/{total}] retry attempt {attempt} after {delay}s", flush=True)
            write_event(
                args.progress_jsonl,
                event="retry",
                index=index,
                total=total,
                attempt=attempt,
                delay_seconds=delay,
                last_error=last_error,
                **item,
            )
            time.sleep(delay)
        ok, last_error = run_push(item["remote"], args.log, args.push_timeout, index, total, attempt)
        if ok or remote_exists(item["remote"]):
            print(f"[{index}/{total}] pushed", flush=True)
            write_event(args.progress_jsonl, event="pushed", index=index, total=total, **item)
            update_state(args.state_json, args._state, item, status="pushed")
            return {"status": "pushed", "retried": retried}
        print(f"[{index}/{total}] attempt {attempt} failed: {last_error}", flush=True)

    print(f"[{index}/{total}] FAILED after retries: {last_error}", flush=True)
    write_event(
        args.progress_jsonl,
        event="failed",
        index=index,
        total=total,
        last_error=last_error,
        **item,
    )
    update_state(args.state_json, args._state, item, status="failed", error=last_error)
    return {"status": "failed", "retried": retried}


def process_one(index: int, total: int, item: dict[str, str], args: argparse.Namespace) -> dict[str, object]:
    if not args.no_resume:
        record = state_tags(args._state).get(item_state_key(item))
        if state_record_matches(record, item):
            print(f'[{index}/{total}] skip state pushed {item["remote"]}', flush=True)
            write_event(args.progress_jsonl, event="skip_state", index=index, total=total, **item)
            return {"status": "skipped", "retried": 0}
        if not args.dry_run and not args.no_remote_precheck and remote_exists(item["remote"]):
            print(f'[{index}/{total}] skip remote exists {item["remote"]}', flush=True)
            update_state(args.state_json, args._state, item, status="pushed", verified=True)
            write_event(args.progress_jsonl, event="skip_remote_exists", index=index, total=total, **item)
            return {"status": "skipped", "retried": 0}
    return push_one(index, total, item, args)


def verify_remote_tags(items: list[dict[str, str]], args: argparse.Namespace) -> dict[str, int]:
    summary = {"verified": 0, "missing": 0}
    for index, item in enumerate(items, 1):
        exists = remote_exists(item["remote"])
        if exists:
            summary["verified"] += 1
            update_state(args.state_json, args._state, item, status="pushed", verified=True)
            write_event(args.progress_jsonl, event="verified", index=index, total=len(items), **item)
        else:
            summary["missing"] += 1
            update_state(args.state_json, args._state, item, status="missing_remote", verified=False)
            write_event(args.progress_jsonl, event="missing_remote", index=index, total=len(items), **item)
            print(f'[verify {index}/{len(items)}] missing {item["remote"]}', flush=True)
    return summary


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")
    frameworks = args.framework or list(DEFAULT_FRAMEWORK_PREFIXES)
    if args.reset_progress or not args.append_progress:
        args.progress_jsonl.parent.mkdir(parents=True, exist_ok=True)
        args.progress_jsonl.write_text("", encoding="utf-8")
    args._state = initial_state(args.state_json, reset=args.reset_state)

    excluded_tags = set(args.exclude_tag)
    items = [
        item
        for item in collect_items(args.repo, frameworks, args.tag)
        if item["remote"].rsplit(":", 1)[-1] not in excluded_tags
        and (args.filter is None or args.filter in item["sample_id"])
    ]
    print(f"planned {len(items)} framework image pushes to {args.repo}", flush=True)
    write_event(
        args.progress_jsonl,
        event="start",
        total=len(items),
        repo=args.repo,
        frameworks=frameworks,
        retry_limit=args.retry_limit,
        push_timeout=args.push_timeout,
        workers=args.workers,
        state_json=str(args.state_json),
    )

    summary = {"pushed": 0, "skipped": 0, "failed": 0, "retried": 0}
    if args.workers == 1:
        results = [process_one(index, len(items), item, args) for index, item in enumerate(items, 1)]
    else:
        pending = []
        if not args.no_resume:
            for index, item in enumerate(items, 1):
                record = state_tags(args._state).get(item_state_key(item))
                if state_record_matches(record, item):
                    summary["skipped"] += 1
                    print(f'[{index}/{len(items)}] skip state pushed {item["remote"]}', flush=True)
                    write_event(args.progress_jsonl, event="skip_state", index=index, total=len(items), **item)
                else:
                    pending.append((index, item))
        else:
            pending = list(enumerate(items, 1))
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(process_one, index, len(items), item, args)
                for index, item in pending
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    for result in results:
        status = result.get("status")
        if status == "pushed":
            summary["pushed"] += 1
        elif status == "skipped":
            summary["skipped"] += 1
        elif status == "failed":
            summary["failed"] += 1
        summary["retried"] += int(result.get("retried") or 0)

    if not args.dry_run and not args.no_final_check:
        verify_summary = verify_remote_tags(items, args)
        summary.update({f"remote_{key}": value for key, value in verify_summary.items()})
        if verify_summary["missing"]:
            summary["failed"] += verify_summary["missing"]

    write_event(args.progress_jsonl, event="done", **summary)
    print("summary " + json.dumps(summary, sort_keys=True), flush=True)
    if summary["failed"]:
        raise SystemExit(summary["failed"])


if __name__ == "__main__":
    main()
