from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from preprocessing.config import LOG_DIR, RESULT_DIR, ensure_runtime_dirs
from preprocessing.github_api import GitHubApiClient
from preprocessing.issue_pr_mining import IssuePrMiner, IssuePrSample


DEFAULT_REPO_KEY = "openfermion"
KNOWN_REPOS = {
    "dimod": "dwavesystems/dimod",
    "mitiq": "unitaryfund/mitiq",
    "openqaoa": "OpenQuantumComputing/QAOA",
    "openfermion": "quantumlib/OpenFermion",
    "qiskit-finance": "qiskit-community/qiskit-finance",
    "qiskit-machine-learning": "qiskit-community/qiskit-machine-learning",
    "qiskit-nature": "qiskit-community/qiskit-nature",
    "qiskit-optimization": "qiskit-community/qiskit-optimization",
    "pennylane": "PennyLaneAI/pennylane",
}
FIELDNAMES = [
    "id",
    "sample_id",
    "repository",
    "issue_url",
    "pr_url",
    "issue_label",
    "keep",
    "benchmark_status",
    "benchmark_notes",
]


def repo_slug(repo_full_name: str) -> str:
    return repo_full_name.split("/")[-1].replace("-", "_").lower()


def default_output_path(repo_full_name: str, scan_mode: str) -> Path:
    return RESULT_DIR / f"{repo_slug(repo_full_name)}_{scan_mode}_review_candidates.csv"


def sample_id(sample: IssuePrSample) -> str:
    return f"{repo_slug(sample.repository)}_{sample.issue_number}_{sample.pull_number}"


def write_review_csv(samples: list[IssuePrSample], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, sample in enumerate(samples, start=1):
        rows.append(
            {
                "id": str(index),
                "sample_id": sample_id(sample),
                "repository": sample.repository,
                "issue_url": sample.issue_url,
                "pr_url": sample.pull_url,
                "issue_label": "",
                "keep": "",
                "benchmark_status": "",
                "benchmark_notes": "",
            }
        )

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def merge_samples(samples: list[IssuePrSample]) -> list[IssuePrSample]:
    merged: dict[tuple[int, int], IssuePrSample] = {}
    for sample in samples:
        key = (sample.issue_number, sample.pull_number)
        existing = merged.get(key)
        if existing is None:
            merged[key] = sample
            continue
        seen_link_types = set(existing.link_types)
        for link_type in sample.link_types:
            if link_type not in seen_link_types:
                existing.link_types.append(link_type)
                seen_link_types.add(link_type)
        seen_refs = set(existing.linked_issue_references)
        for reference in sample.linked_issue_references:
            if reference not in seen_refs:
                existing.linked_issue_references.append(reference)
                seen_refs.add(reference)
    return list(merged.values())


def screen_samples(
    *,
    repo: str,
    issue_limit: int | None,
    pull_limit: int | None,
    since: str | None,
    max_workers: int,
    scan_mode: str,
) -> tuple[list[IssuePrSample], list[tuple[str, dict]]]:
    miner = IssuePrMiner(GitHubApiClient())
    samples: list[IssuePrSample] = []
    summaries: list[tuple[str, dict]] = []

    if scan_mode in {"issue", "combined"}:
        issue_samples, issue_summary = miner.screen_repository(
            repo_full_name=repo,
            issue_limit=issue_limit,
            since=since,
            max_workers=max_workers,
        )
        samples.extend(issue_samples)
        summaries.append(("issue", issue_summary))

    if scan_mode in {"pr", "combined"}:
        pr_samples, pr_summary = miner.screen_repository_pr_first(
            repo_full_name=repo,
            pull_limit=pull_limit,
            max_workers=max_workers,
        )
        samples.extend(pr_samples)
        summaries.append(("pr", pr_summary))

    return merge_samples(samples), summaries


def configure_logging(log_name: str) -> None:
    ensure_runtime_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / log_name, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def run_export(
    *,
    repo: str,
    output: Path,
    issue_limit: int | None = None,
    pull_limit: int | None = None,
    since: str | None = None,
    max_workers: int = 8,
    scan_mode: str = "combined",
    log_name: str = "export_repo_review_csv.log",
    display_name: str | None = None,
) -> list[IssuePrSample]:
    configure_logging(log_name)
    name = display_name or repo
    logging.info(
        "Starting %s screening for repo=%s issue_limit=%s pull_limit=%s scan_mode=%s.",
        name,
        repo,
        issue_limit if issue_limit is not None else "None",
        pull_limit if pull_limit is not None else "None",
        scan_mode,
    )
    samples, summaries = screen_samples(
        repo=repo,
        issue_limit=issue_limit,
        pull_limit=pull_limit,
        since=since,
        max_workers=max_workers,
        scan_mode=scan_mode,
    )
    write_review_csv(samples, output)
    for label, summary in summaries:
        logging.info("%s scan summary: %s", label, summary)
    logging.info("Wrote %s de-duplicated issue-PR samples to %s.", len(samples), output)
    print(f"Wrote {len(samples)} {name} rows to {output}")
    return samples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export linked issue-PR samples with test changes to a review CSV."
    )
    parser.add_argument(
        "--repo-key",
        choices=sorted(KNOWN_REPOS),
        default=DEFAULT_REPO_KEY,
        help="Known repository shortcut. Ignored when --repo is provided.",
    )
    parser.add_argument("--repo", default=None, help="GitHub owner/repo name.")
    parser.add_argument("--issue-limit", type=int, default=None, help="Maximum number of closed issues to scan.")
    parser.add_argument("--pull-limit", type=int, default=None, help="Maximum number of closed pull requests to scan.")
    parser.add_argument("--since", default=None, help="Optional ISO-8601 lower time bound for issues.")
    parser.add_argument("--max-workers", type=int, default=8, help="Parallel workers for GitHub fetching.")
    parser.add_argument(
        "--scan-mode",
        choices=["issue", "pr", "combined"],
        default="combined",
        help="Scan closed issues, closed PRs, or both and de-duplicate issue/PR pairs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path. Defaults to preprocessing/result/<repo>_<scan-mode>_review_candidates.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = args.repo or KNOWN_REPOS[args.repo_key]
    output = args.output or default_output_path(repo, args.scan_mode)
    run_export(
        repo=repo,
        output=output,
        issue_limit=args.issue_limit,
        pull_limit=args.pull_limit,
        since=args.since,
        max_workers=args.max_workers,
        scan_mode=args.scan_mode,
        display_name=args.repo_key if args.repo is None else repo,
    )


if __name__ == "__main__":
    main()
