from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import json
import logging
import re
from pathlib import Path
from typing import Any

from preprocessing.config import TEST_PATH_HINTS
from preprocessing.github_api import GitHubApiClient


logger = logging.getLogger(__name__)

@dataclass
class IssuePrSample:
    repository: str
    issue_number: int
    issue_title: str
    issue_url: str
    issue_state: str
    pull_repository: str
    pull_number: int
    pull_title: str
    pull_url: str
    merged_at: str
    link_types: list[str]
    linked_issue_references: list[str]
    test_files: list[str]
    changed_files: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        repo_slug = self.repository.replace("qiskit-community/", "").replace("/", "_").replace("-", "_")
        return f"{repo_slug}_{self.issue_number}_{self.pull_number}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_issue_references(text: str) -> list[str]:
    patterns = [
        r"#\d+",
        r"\b(?:fixes|fixed|fix|closes|closed|close|resolves|resolved|resolve)\s+#\d+",
        r"\bissue\s+#\d+",
        r"\bgh-\d+\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text or "", flags=re.IGNORECASE))

    deduped: list[str] = []
    seen: set[str] = set()
    for match in matches:
        lowered = match.lower()
        if lowered not in seen:
            seen.add(lowered)
            deduped.append(match)
    return deduped


def extract_issue_numbers_from_references(text: str) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()
    for reference in extract_issue_references(text):
        match = re.search(r"\d+", reference)
        if not match:
            continue
        number = int(match.group())
        if number not in seen:
            seen.add(number)
            numbers.append(number)
    return numbers


def extract_pulls_from_closed_by_references(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pulls: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        number = node.get("number")
        repository = (node.get("repository") or {}).get("nameWithOwner")
        if isinstance(number, int) and isinstance(repository, str):
            key = (repository, number)
            if key not in seen:
                seen.add(key)
                pulls.append(
                    {
                        "repository": repository,
                        "number": number,
                        "title": node.get("title", ""),
                        "url": node.get("url", ""),
                        "mergedAt": node.get("mergedAt"),
                        "link_types": ["linked:graphql"],
                    }
                )
    return pulls


def extract_repo_full_name_from_api_url(url: str) -> str | None:
    match = re.search(r"/repos/([^/]+/[^/]+)$", url or "")
    if match:
        return match.group(1)
    return None


def extract_pulls_from_issue_timeline(
    timeline_items: list[dict[str, Any]],
    default_repo_full_name: str,
) -> list[dict[str, Any]]:
    pulls: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()

    for item in timeline_items:
        if not isinstance(item, dict):
            continue
        event = normalize_text(str(item.get("event", "")))
        if event not in {"cross-referenced", "connected", "referenced", "closed"}:
            continue

        source = item.get("source")
        if not isinstance(source, dict):
            continue
        source_issue = source.get("issue")
        if not isinstance(source_issue, dict):
            continue
        pull_request = source_issue.get("pull_request")
        if not isinstance(pull_request, dict):
            continue

        number = source_issue.get("number")
        if not isinstance(number, int):
            continue

        repository = extract_repo_full_name_from_api_url(source_issue.get("repository_url", "")) or default_repo_full_name
        key = (repository, number, event)
        if key in seen:
            continue
        seen.add(key)
        pulls.append(
            {
                "repository": repository,
                "number": number,
                "title": source_issue.get("title", ""),
                "url": source_issue.get("html_url", "") or pull_request.get("html_url", "") or pull_request.get("url", ""),
                "mergedAt": source_issue.get("closed_at"),
                "link_types": [f"timeline:{event}"],
            }
        )

    return pulls


def merge_linked_pull_candidates(*candidate_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, int], dict[str, Any]] = {}

    for group in candidate_groups:
        for candidate in group:
            if not isinstance(candidate, dict):
                continue
            repository = candidate.get("repository")
            number = candidate.get("number")
            if not isinstance(repository, str) or not isinstance(number, int):
                continue

            key = (repository, number)
            existing = merged.get(key)
            if existing is None:
                merged[key] = {
                    "repository": repository,
                    "number": number,
                    "title": candidate.get("title", ""),
                    "url": candidate.get("url", ""),
                    "mergedAt": candidate.get("mergedAt"),
                    "link_types": list(candidate.get("link_types", [])),
                }
                continue

            if not existing.get("title") and candidate.get("title"):
                existing["title"] = candidate["title"]
            if not existing.get("url") and candidate.get("url"):
                existing["url"] = candidate["url"]
            if not existing.get("mergedAt") and candidate.get("mergedAt"):
                existing["mergedAt"] = candidate["mergedAt"]

            seen_types = set(existing.get("link_types", []))
            for link_type in candidate.get("link_types", []):
                if link_type not in seen_types:
                    existing.setdefault("link_types", []).append(link_type)
                    seen_types.add(link_type)

    return list(merged.values())


def is_test_file(path: str) -> bool:
    lowered = path.lower()
    return any(hint in lowered for hint in TEST_PATH_HINTS)


def is_kept_test_file_change(file_record: dict[str, Any]) -> bool:
    filename = file_record.get("filename", "")
    status = normalize_text(str(file_record.get("status", "")))
    return is_test_file(filename) and status in {"added", "modified"}


class IssuePrMiner:
    def __init__(self, client: GitHubApiClient) -> None:
        self.client = client

    def _get_linked_pulls_graphql(self, repo_full_name: str, issue_number: int) -> list[dict[str, Any]]:
        owner, repo = repo_full_name.split("/", 1)
        query = """
        query($owner: String!, $repo: String!, $issueNumber: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $issueNumber) {
              closedByPullRequestsReferences(first: 20) {
                nodes {
                  number
                  title
                  url
                  mergedAt
                  repository {
                    nameWithOwner
                  }
                }
              }
            }
          }
        }
        """
        payload = self.client.graphql(
            query,
            variables={"owner": owner, "repo": repo, "issueNumber": issue_number},
        )
        nodes = (
            payload.get("data", {})
            .get("repository", {})
            .get("issue", {})
        )
        if not isinstance(nodes, dict):
            return []
        reference_nodes = (
            nodes.get("closedByPullRequestsReferences", {})
            .get("nodes", [])
        )
        return extract_pulls_from_closed_by_references(reference_nodes)

    def _get_linked_pulls_timeline(self, repo_full_name: str, issue_number: int) -> list[dict[str, Any]]:
        timeline_items = self.client.list_issue_timeline(repo_full_name, issue_number)
        return extract_pulls_from_issue_timeline(timeline_items, default_repo_full_name=repo_full_name)

    def _get_linked_pulls(self, repo_full_name: str, issue_number: int) -> list[dict[str, Any]]:
        graphql_pulls = self._get_linked_pulls_graphql(repo_full_name, issue_number)
        timeline_pulls = self._get_linked_pulls_timeline(repo_full_name, issue_number)
        return merge_linked_pull_candidates(graphql_pulls, timeline_pulls)

    def _search_closed_issues(
        self,
        repo_full_name: str,
        issue_limit: int | None,
        since: str | None,
    ) -> tuple[list[dict[str, Any]], int]:
        logger.info(
            "Using repository issues API for %s and collecting closed issues for link analysis.",
            repo_full_name,
        )
        issues = self.client.list_issues(
            repo_full_name,
            state="closed",
            limit=issue_limit,
            since=since,
        )
        pure_issues = [issue for issue in issues if "pull_request" not in issue]
        return pure_issues, len(pure_issues)

    def _collect_issue_samples(
        self,
        repo_full_name: str,
        issue: dict[str, Any],
        require_test_changes: bool = True,
    ) -> list[IssuePrSample]:
        issue_number = issue.get("number")
        if not isinstance(issue_number, int):
            return []
        linked_pulls = self._get_linked_pulls(repo_full_name, issue_number)
        if not linked_pulls:
            logger.debug(
                "Issue #%s had no linked PRs from explicit links or timeline inference.",
                issue_number,
            )
            return []

        samples: list[IssuePrSample] = []
        for linked_pull in linked_pulls:
            pull_repo = linked_pull["repository"]
            pull_number = linked_pull["number"]
            if pull_repo != repo_full_name:
                continue
            pull = self.client.get_pull_request(pull_repo, pull_number)
            merged_at = pull.get("merged_at")
            if not merged_at:
                continue
            files = self.client.list_pull_request_files(pull_repo, pull_number)
            changed_files = [file.get("filename", "") for file in files if file.get("filename")]
            test_files = [file.get("filename", "") for file in files if is_kept_test_file_change(file)]
            if require_test_changes and not test_files:
                continue
            linked_text = "\n".join([pull.get("title", "") or "", pull.get("body", "") or ""])
            samples.append(
                IssuePrSample(
                    repository=repo_full_name,
                    issue_number=issue_number,
                    issue_title=issue.get("title", ""),
                    issue_url=issue.get("html_url", ""),
                    issue_state=issue.get("state", ""),
                    pull_repository=pull_repo,
                    pull_number=pull_number,
                    pull_title=pull.get("title", ""),
                    pull_url=pull.get("html_url", ""),
                    merged_at=merged_at,
                    link_types=list(linked_pull.get("link_types", [])),
                    linked_issue_references=extract_issue_references(linked_text),
                    changed_files=changed_files,
                    test_files=test_files,
                )
            )
        return samples

    def _collect_pull_samples(
        self,
        repo_full_name: str,
        pull: dict[str, Any],
        require_test_changes: bool = True,
    ) -> list[IssuePrSample]:
        pull_number = pull.get("number")
        if not isinstance(pull_number, int):
            return []
        merged_at = pull.get("merged_at")
        if not merged_at:
            return []

        linked_text = "\n".join([pull.get("title", "") or "", pull.get("body", "") or ""])
        issue_numbers = extract_issue_numbers_from_references(linked_text)
        if not issue_numbers:
            return []

        try:
            files = self.client.list_pull_request_files(repo_full_name, pull_number)
        except Exception as exc:
            logger.warning("Skipping PR #%s because changed-file lookup failed: %s", pull_number, exc)
            return []
        changed_files = [file.get("filename", "") for file in files if file.get("filename")]
        test_files = [file.get("filename", "") for file in files if is_kept_test_file_change(file)]
        if require_test_changes and not test_files:
            return []

        samples: list[IssuePrSample] = []
        linked_issue_references = extract_issue_references(linked_text)
        for issue_number in issue_numbers:
            try:
                issue = self.client.get_issue(repo_full_name, issue_number)
            except Exception as exc:
                logger.debug(
                    "Skipping PR #%s reference to issue #%s because issue lookup failed: %s",
                    pull_number,
                    issue_number,
                    exc,
                )
                continue
            if "pull_request" in issue:
                continue
            samples.append(
                IssuePrSample(
                    repository=repo_full_name,
                    issue_number=issue_number,
                    issue_title=issue.get("title", ""),
                    issue_url=issue.get("html_url", ""),
                    issue_state=issue.get("state", ""),
                    pull_repository=repo_full_name,
                    pull_number=pull_number,
                    pull_title=pull.get("title", ""),
                    pull_url=pull.get("html_url", ""),
                    merged_at=merged_at,
                    link_types=["linked:pr_text"],
                    linked_issue_references=linked_issue_references,
                    changed_files=changed_files,
                    test_files=test_files,
                )
            )
        return samples

    def screen_repository_pr_first(
        self,
        repo_full_name: str,
        pull_limit: int | None = None,
        max_workers: int = 8,
        require_test_changes: bool = True,
    ) -> tuple[list[IssuePrSample], dict[str, Any]]:
        logger.info(
            "Searching closed PRs for %s and retaining merged PRs that reference issues in PR text.",
            repo_full_name,
        )
        pulls = self.client.list_pull_requests(repo_full_name, state="closed", limit=pull_limit)
        worker_count = max(1, min(max_workers, len(pulls) or 1))
        samples: list[IssuePrSample] = []
        merged_pull_requests = 0
        matched_pull_requests = 0

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_pull = {
                executor.submit(
                    self._collect_pull_samples,
                    repo_full_name,
                    pull,
                    require_test_changes,
                ): pull.get("number")
                for pull in pulls
            }
            for completed_count, future in enumerate(as_completed(future_to_pull), start=1):
                pull_number = future_to_pull[future]
                if completed_count == 1 or completed_count % 20 == 0 or completed_count == len(pulls):
                    logger.info("Processed PR-text scan %s/%s: #%s", completed_count, len(pulls), pull_number)
                try:
                    pull_samples = future.result()
                except Exception as exc:
                    logger.warning("Skipping PR #%s because PR-text scan failed: %s", pull_number, exc)
                    continue
                if pull_samples:
                    matched_pull_requests += 1
                    samples.extend(pull_samples)
                    logger.info(
                        "Matched PR #%s with %s referenced issue sample(s).",
                        pull_number,
                        len(pull_samples),
                    )

        merged_pull_requests = sum(1 for pull in pulls if pull.get("merged_at"))
        summary = {
            "total_screened_pull_requests": len(pulls),
            "merged_pull_requests": merged_pull_requests,
            "matched_pull_requests": matched_pull_requests,
            "selected_issue_pr_samples": len(samples),
            "selected_samples_with_test_file_changes": sum(1 for sample in samples if sample.test_files),
            "link_type_counts": {"linked:pr_text": len(samples)} if samples else {},
        }
        return samples, summary

    def screen_repository(
        self,
        repo_full_name: str,
        issue_limit: int | None = None,
        since: str | None = None,
        max_workers: int = 8,
        require_test_changes: bool = True,
    ) -> tuple[list[IssuePrSample], dict[str, Any]]:
        logger.info(
            "Searching closed issues for %s and retaining issues linked to PRs via explicit links or timeline inference.",
            repo_full_name,
        )
        pure_issues, total_screened_issues = self._search_closed_issues(repo_full_name, issue_limit, since)
        worker_count = max(1, min(max_workers, len(pure_issues) or 1))
        samples: list[IssuePrSample] = []
        issues_with_linked_pr = 0
        matched_pull_requests = 0
        link_type_counts: dict[str, int] = {}

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_issue = {
                executor.submit(
                    self._collect_issue_samples,
                    repo_full_name,
                    issue,
                    require_test_changes,
                ): issue.get("number")
                for issue in pure_issues
            }
            for completed_count, future in enumerate(as_completed(future_to_issue), start=1):
                issue_number = future_to_issue[future]
                if completed_count == 1 or completed_count % 20 == 0 or completed_count == len(pure_issues):
                    logger.info("Processed linked-issue scan %s/%s: #%s", completed_count, len(pure_issues), issue_number)
                try:
                    issue_samples = future.result()
                except Exception as exc:
                    logger.warning("Skipping issue #%s because linked-issue scan failed: %s", issue_number, exc)
                    continue
                if issue_samples:
                    issues_with_linked_pr += 1
                    matched_pull_requests += len({sample.pull_number for sample in issue_samples})
                    for sample in issue_samples:
                        for link_type in sample.link_types:
                            link_type_counts[link_type] = link_type_counts.get(link_type, 0) + 1
                    samples.extend(issue_samples)
                    logger.info(
                        "Matched linked issue #%s with %s merged PR sample(s).",
                        issue_number,
                        len(issue_samples),
                    )

        summary = {
            "total_screened_issues": total_screened_issues,
            "issues_with_linked_pr": issues_with_linked_pr,
            "matched_pull_requests": matched_pull_requests,
            "selected_issue_pr_samples": len(samples),
            "selected_samples_with_test_file_changes": sum(1 for sample in samples if sample.test_files),
            "link_type_counts": link_type_counts,
        }
        return samples, summary


def save_issue_pr_samples(samples: list[IssuePrSample], summary: dict[str, Any], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "results": [
            {
                "id": sample.id,
                "issue_url": sample.issue_url,
                "pr_url": sample.pull_url,
            }
            for sample in samples
        ],
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
