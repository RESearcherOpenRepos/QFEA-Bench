#!/usr/bin/env python3
"""Delete DockerHub tags that are not part of the published agent-base layer."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REPO = "arthurshy/quanbench"
DEFAULT_KEEP_PREFIX = "agent-base-"
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROGRESS = (
    ROOT
    / "benchmark"
    / "dataset"
    / "build_logs"
    / "dockerhub_delete_non_agent_base_tags_progress.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--keep-prefix", default=DEFAULT_KEEP_PREFIX)
    parser.add_argument(
        "--from-samples",
        action="store_true",
        help=(
            "Build deletion targets from local sample IDs instead of listing all "
            "remote tags. This deletes minisweagent-<sample_id> tags."
        ),
    )
    parser.add_argument(
        "--extra-tag",
        action="append",
        default=[],
        help="Additional remote tag to delete. Can be repeated.",
    )
    parser.add_argument("--progress-jsonl", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--credential-helper", default="docker-credential-desktop")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete matching remote tags. Required unless --dry-run is set.",
    )
    return parser.parse_args()


def event(path: Path, **payload: object) -> None:
    payload.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: dict[str, str] | None = None,
) -> Any:
    raw = b""
    for attempt in range(1, 6):
        body = None
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url,
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
            break
        except (
            TimeoutError,
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
            socket.timeout,
            urllib.error.URLError,
        ):
            if attempt == 5:
                raise
            time.sleep(2 * attempt)
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def list_tags(repo: str) -> list[str]:
    namespace, name = repo.split("/", 1)
    url = (
        "https://hub.docker.com/v2/repositories/"
        f"{urllib.parse.quote(namespace)}/{urllib.parse.quote(name)}/tags?page_size=10"
    )
    tags: list[str] = []
    while url:
        payload = request_json(url)
        tags.extend(str(item["name"]) for item in payload.get("results", []))
        url = payload.get("next")
    return sorted(tags)


def sample_ids(samples_dir: Path) -> list[str]:
    index_path = samples_dir / "index.json"
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        return sorted(str(item["sample_id"]) for item in payload.get("samples", []))

    ids = []
    for sample_json in samples_dir.glob("*/*/sample.json"):
        payload = json.loads(sample_json.read_text(encoding="utf-8"))
        instance = payload.get("instance") or {}
        ids.append(str(instance.get("instance_id") or sample_json.parent.name))
    return sorted(set(ids))


def deletion_targets(args: argparse.Namespace) -> tuple[list[str], int | None]:
    if args.from_samples:
        targets = [f"minisweagent-{sample_id}" for sample_id in sample_ids(args.samples_dir)]
        targets.extend(args.extra_tag)
        return sorted(set(targets)), None

    tags = list_tags(args.repo)
    targets = [tag for tag in tags if not tag.startswith(args.keep_prefix)]
    targets.extend(args.extra_tag)
    return sorted(set(targets)), len(tags)


def docker_credential(helper: str, server_url: str) -> tuple[str, str] | None:
    try:
        completed = subprocess.run(
            [helper, "get"],
            input=server_url,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    payload = json.loads(completed.stdout)
    username = payload.get("Username")
    secret = payload.get("Secret")
    if not username or not secret:
        return None
    return str(username), str(secret)


def dockerhub_login(username: str, secret: str) -> str | None:
    try:
        payload = request_json(
            "https://hub.docker.com/v2/users/login/",
            method="POST",
            data={"username": username, "password": secret},
        )
    except urllib.error.HTTPError:
        return None
    token = payload.get("token") if isinstance(payload, dict) else None
    return str(token) if token else None


def auth_header_candidates(helper: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    username = os.environ.get("DOCKERHUB_USERNAME")
    secret = os.environ.get("DOCKERHUB_TOKEN") or os.environ.get("DOCKERHUB_PASSWORD")
    if username and secret:
        token = dockerhub_login(username, secret)
        if token:
            candidates.append({"Authorization": f"JWT {token}"})

    for server_url in (
        "https://index.docker.io/v1/",
        "https://index.docker.io/v1/access-token",
    ):
        credential = docker_credential(helper, server_url)
        if credential is None:
            continue
        helper_username, helper_secret = credential
        token = dockerhub_login(helper_username, helper_secret)
        if token:
            candidates.append({"Authorization": f"JWT {token}"})
        candidates.append({"Authorization": f"JWT {helper_secret}"})
        candidates.append({"Authorization": f"Bearer {helper_secret}"})
    return candidates


def validate_auth(headers: dict[str, str]) -> bool:
    try:
        request_json("https://hub.docker.com/v2/user/", headers=headers)
    except urllib.error.HTTPError:
        return False
    return True


def delete_tag(repo: str, tag: str, headers: dict[str, str]) -> int:
    namespace, name = repo.split("/", 1)
    url = (
        "https://hub.docker.com/v2/repositories/"
        f"{urllib.parse.quote(namespace)}/{urllib.parse.quote(name)}"
        f"/tags/{urllib.parse.quote(tag, safe='')}/"
    )
    for attempt in range(1, 6):
        request = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except (
            TimeoutError,
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
            socket.timeout,
            urllib.error.URLError,
        ):
            if attempt == 5:
                return 599
            time.sleep(2 * attempt)
    return 599


def main() -> None:
    args = parse_args()
    if not args.dry_run and not args.yes:
        raise SystemExit("Refusing to delete tags without --yes. Use --dry-run to preview.")

    delete_targets, total_tags = deletion_targets(args)
    if total_tags is not None:
        print(f"remote tags: {total_tags}")
        print(f"kept by prefix {args.keep_prefix!r}: {total_tags - len(delete_targets)}")
    else:
        print(f"remote tags: not listed (--from-samples)")
        print(f"kept by prefix {args.keep_prefix!r}: not listed")
    print(f"delete targets: {len(delete_targets)}")
    for tag in delete_targets:
        print(tag)
    event(
        args.progress_jsonl,
        event="planned",
        repo=args.repo,
        keep_prefix=args.keep_prefix,
        total_tags=total_tags,
        delete_targets=len(delete_targets),
        from_samples=args.from_samples,
        dry_run=args.dry_run,
    )

    if args.dry_run or not delete_targets:
        return

    auth_headers = None
    for candidate in auth_header_candidates(args.credential_helper):
        if validate_auth(candidate):
            auth_headers = candidate
            break
    if auth_headers is None:
        raise SystemExit(
            "Could not obtain DockerHub API credentials. Set DOCKERHUB_USERNAME "
            "and DOCKERHUB_TOKEN, or log in through Docker Desktop."
        )

    failures = 0
    for index, tag in enumerate(delete_targets, start=1):
        status = delete_tag(args.repo, tag, auth_headers)
        ok = status in {200, 202, 204, 404}
        failures += 0 if ok else 1
        print(f"[{index}/{len(delete_targets)}] delete {tag}: HTTP {status}")
        event(args.progress_jsonl, event="delete", tag=tag, status=status, ok=ok)

    remaining = [] if args.from_samples else [
        tag for tag in list_tags(args.repo) if not tag.startswith(args.keep_prefix)
    ]
    event(args.progress_jsonl, event="done", failures=failures, remaining=len(remaining))
    if remaining:
        print("remaining non-agent-base tags:")
        for tag in remaining:
            print(tag)
    if failures or remaining:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
