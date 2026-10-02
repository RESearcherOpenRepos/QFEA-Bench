#!/usr/bin/env python3
"""Pull published QuanBench runtime images from DockerHub."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS = ROOT / "benchmark" / "dataset" / "build_logs" / "dockerhub_pull_published_images_progress.jsonl"
SUPPORTED_KINDS = ("agent-base", "minisweagent")
DEFAULT_KINDS = ("agent-base",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull QuanBench images published to DockerHub.")
    parser.add_argument("--repo", default="arthurshy/quanbench", help="Remote image repo.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument(
        "--kind",
        action="append",
        choices=SUPPORTED_KINDS,
        help="Image kind to pull. Defaults to agent-base. Can be repeated.",
    )
    parser.add_argument("--filter", default=None, help="Substring filter over sample_id.")
    parser.add_argument("--missing-only", action="store_true", help="Skip local tags that already exist.")
    parser.add_argument("--retry-limit", type=int, default=5)
    parser.add_argument("--retry-delay", type=int, default=10)
    parser.add_argument("--progress-jsonl", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sample_ids(samples_dir: Path, filter_text: str | None) -> list[str]:
    ids = []
    for sample_json in samples_dir.glob("*/*/sample.json"):
        try:
            data = json.loads(sample_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sample_id = str((data.get("instance") or {}).get("instance_id") or sample_json.parent.name)
        if filter_text and filter_text not in sample_id:
            continue
        ids.append(sample_id)
    return sorted(set(ids))


def local_tag(kind: str, sample_id: str) -> str:
    if kind == "agent-base":
        return f"benchmark-agent-base:{sample_id}"
    if kind == "minisweagent":
        return f"benchmark-minisweagent-{sample_id}:latest"
    raise ValueError(f"unsupported kind: {kind}")


def remote_tag(repo: str, kind: str, sample_id: str) -> str:
    return f"{repo}:{kind}-{sample_id}"


def image_exists(image: str) -> bool:
    return subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def event(path: Path, **payload: object) -> None:
    payload.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run(command: list[str], dry_run: bool) -> int:
    print(" ".join(command), flush=True)
    if dry_run:
        return 0
    return subprocess.run(command, check=False).returncode


def main() -> None:
    args = parse_args()
    kinds = args.kind or list(DEFAULT_KINDS)
    ids = sample_ids(args.samples_dir, args.filter)
    total = len(ids) * len(kinds)
    print(f"planned {total} image pulls from {args.repo}", flush=True)
    event(args.progress_jsonl, event="start", repo=args.repo, kinds=kinds, total=total)
    failures = 0
    index = 0
    for sample_id in ids:
        for kind in kinds:
            index += 1
            remote = remote_tag(args.repo, kind, sample_id)
            local = local_tag(kind, sample_id)
            event(args.progress_jsonl, event="begin", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
            if args.missing_only and image_exists(remote):
                print(f"[{index}/{total}] skip existing pulled tag {remote}", flush=True)
                event(args.progress_jsonl, event="skip_existing_remote", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            if args.missing_only and image_exists(local):
                print(f"[{index}/{total}] skip existing local tag {local}", flush=True)
                event(args.progress_jsonl, event="skip_existing_local", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            if args.dry_run:
                run(["docker", "pull", remote], args.dry_run)
                event(args.progress_jsonl, event="dry_run", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            ok = False
            for attempt in range(1, args.retry_limit + 1):
                if attempt > 1:
                    delay = min(90, args.retry_delay * attempt)
                    print(f"[{index}/{total}] retry {attempt} after {delay}s: {remote}", flush=True)
                    event(args.progress_jsonl, event="retry", index=index, total=total, attempt=attempt, delay_seconds=delay, kind=kind, sample_id=sample_id, remote=remote, local=local)
                    time.sleep(delay)
                if run(["docker", "pull", remote], args.dry_run) == 0:
                    ok = True
                    break
            if ok:
                print(f"[{index}/{total}] pulled {remote}", flush=True)
                event(args.progress_jsonl, event="pulled", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
            else:
                failures += 1
                print(f"[{index}/{total}] FAILED {remote}", flush=True)
                event(args.progress_jsonl, event="failed", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
    event(args.progress_jsonl, event="done", failures=failures)
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
