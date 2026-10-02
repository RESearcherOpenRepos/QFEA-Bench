#!/usr/bin/env python3
"""Retag pulled QuanBench DockerHub images to the local names used by runners."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS = ROOT / "benchmark" / "dataset" / "build_logs" / "dockerhub_retag_published_images_progress.jsonl"
SUPPORTED_KINDS = ("agent-base", "minisweagent")
DEFAULT_KINDS = ("agent-base",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retag pulled QuanBench DockerHub images for local scripts.")
    parser.add_argument("--repo", default="arthurshy/quanbench", help="Remote image repo.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument(
        "--kind",
        action="append",
        choices=SUPPORTED_KINDS,
        help="Image kind to retag. Defaults to agent-base. Can be repeated.",
    )
    parser.add_argument("--filter", default=None, help="Substring filter over sample_id.")
    parser.add_argument("--missing-only", action="store_true", help="Skip local tags that already exist.")
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


def remote_tag(repo: str, kind: str, sample_id: str) -> str:
    return f"{repo}:{kind}-{sample_id}"


def local_tag(kind: str, sample_id: str) -> str:
    if kind == "agent-base":
        return f"benchmark-agent-base:{sample_id}"
    if kind == "minisweagent":
        return f"benchmark-minisweagent-{sample_id}:latest"
    raise ValueError(f"unsupported kind: {kind}")


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


def main() -> None:
    args = parse_args()
    kinds = args.kind or list(DEFAULT_KINDS)
    ids = sample_ids(args.samples_dir, args.filter)
    total = len(ids) * len(kinds)
    print(f"planned {total} image retags", flush=True)
    event(args.progress_jsonl, event="start", repo=args.repo, kinds=kinds, total=total)
    failures = 0
    index = 0
    for sample_id in ids:
        for kind in kinds:
            index += 1
            remote = remote_tag(args.repo, kind, sample_id)
            local = local_tag(kind, sample_id)
            event(args.progress_jsonl, event="begin", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
            if args.missing_only and image_exists(local):
                print(f"[{index}/{total}] skip existing {local}", flush=True)
                event(args.progress_jsonl, event="skip_existing", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            if args.dry_run:
                print(" ".join(["docker", "tag", remote, local]), flush=True)
                event(args.progress_jsonl, event="dry_run", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            if not image_exists(remote):
                failures += 1
                print(f"[{index}/{total}] missing pulled image {remote}", flush=True)
                event(args.progress_jsonl, event="missing_remote", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            command = ["docker", "tag", remote, local]
            print(" ".join(command), flush=True)
            if subprocess.run(command, check=False).returncode != 0:
                failures += 1
                print(f"[{index}/{total}] FAILED {remote} -> {local}", flush=True)
                event(args.progress_jsonl, event="failed", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
                continue
            print(f"[{index}/{total}] retagged {remote} -> {local}", flush=True)
            event(args.progress_jsonl, event="retagged", index=index, total=total, kind=kind, sample_id=sample_id, remote=remote, local=local)
    event(args.progress_jsonl, event="done", failures=failures)
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
