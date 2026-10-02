"""Validate saved individual decisions and regenerate the offline audit report."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    raw = json.loads((ROOT / "all_pairs.json").read_text())
    mining = json.loads((ROOT / "mining_summary.json").read_text())
    rows = list(csv.DictReader((ROOT / "review_candidates.csv").open(encoding="utf-8-sig")))
    decisions = [json.loads(line) for line in (ROOT / "pair_decisions.jsonl").read_text().splitlines()]
    candidates = [r for r in raw if r["legacy_test_file_gate"]]
    assert len(rows) == len(decisions) == len(candidates)
    assert len({r["sample_id"] for r in raw}) == len(raw)
    assert [d["ordinal"] for d in decisions] == list(range(1, len(rows) + 1))
    retained = []
    for row, decision, source in zip(rows, decisions, candidates):
        assert row["sample_id"] == decision["sample_id"] == source["sample_id"]
        assert row["issue_label"] == decision["issue_label"]
        assert row["keep"] == decision["keep"]
        # Runtime fields may be populated by later construction; semantic decisions remain fixed.
        assert decision["runtime_validated"] is False
        assert decision["human_independent_annotation"] is False
        if row["issue_label"] != "feature":
            assert not row["keep"]
        else:
            assert row["keep"] in {"yes", "no"}
        if row["keep"] == "yes":
            assert decision["one_to_one"] and decision["quantum_specific"]
            assert decision["target_tests"] and source["test_files"]
            retained.append({**source, **decision})
    assert len({(r["repository"], r["pr_number"]) for r in retained}) == len(retained)
    totals = dict(raw_pairs=len(raw), test_path_gate_pass=len(rows),
                  test_path_gate_fail=len(raw) - len(rows),
                  feature_pairs=sum(d["issue_label"] == "feature" for d in decisions),
                  retained_pairs=len(retained), runtime_validated_new_instances=0)
    by_repo = {}
    for repo, counts in mining["repositories"].items():
        selected = [d for d in decisions if d["repository"] == repo]
        by_repo[repo] = {**counts, "labels": dict(Counter(d["issue_label"] for d in selected)),
                         "retained_pairs": sum(d["keep"] == "yes" for d in selected),
                         "excluded_feature_pairs": sum(d["keep"] == "no" for d in selected)}
    summary = {"snapshot_date": "2026-09-30", "reviewer": "Codex",
               "semantic_review_complete": True, "independent_human_review_complete": False,
               "runtime_validation_performed": False, "totals": totals, "repositories": by_repo,
               "retained_open_issue_pairs": [r["sample_id"] for r in retained if r["issue_state"] == "OPEN"],
               "closed_issue_only_retained_pairs": sum(r["issue_state"] == "CLOSED" for r in retained),
               "last_decision_utc": decisions[-1]["reviewed_utc"]}
    (ROOT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    fields = ["sample_id", "repository", "issue_url", "pr_url", "issue_title", "issue_state",
              "target_tests", "construction_risk", "reason"]
    with (ROOT / "retained_pairs.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(retained)
    report = ["# Issue–PR screening for four added repositories", "",
              "Historical static screening: **168 linked pairs -> 68 passing the test-path gate -> 24 feature pairs -> 14 construction candidates**. Closed-issue filtering retains 13 candidates. The released benchmark has 117 active tasks after construction and scope review.", "",
              "The pairwise review was performed with Codex assistance. Independent human review is not recorded as complete. This static stage did not run Docker or F2P/P2P tests; runtime evidence is maintained separately in [construction/](construction/README.md).", "",
              "| Repository | Closed issues | Merged PRs | Linked pairs | Test-path gate | Features | Retained |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for repo, c in by_repo.items():
        report.append(f"| {repo} | {c['closed_issues']} | {c['merged_prs']} | {c['raw_pairs']} | {c['pairs_with_added_or_modified_test_files']} | {c['labels'].get('feature', 0)} | {c['retained_pairs']} |")
    report.extend(["", "## Method and boundaries", "",
        "1. Combine and deduplicate closed-issue closing/timeline relations and references in merged PR titles/bodies; preserve the relationship source.",
        "2. Apply the historical added/modified test-path heuristic (`test/`, `tests/`, `/test_`, `_test.py`). The 100 rejected pairs were not semantically classified. CI paths can match this gate; a match does not establish a valid feature test.",
        "3. Read each remaining issue, PR, discussion, and changed file. Verify the relationship before assigning feature, bugfix, refactor, or other. Only feature pairs receive a keep decision.",
        "4. For features, check alignment with the issue, core quantum-domain scope, and actual test coverage. Multiple related issues are not automatically disqualifying; retain each implementation only once.",
        "5. Treat retained pairs as construction candidates. `target_tests` provides source locations, not runtime-validated pytest selectors.", "",
        "The PR-first path permits an open issue. OpenQAOA issue 207 / PR 302 is excluded by the subsequent closed-issue gate. Among the 68 reviewed pairs, 20 are bugfix, 6 refactor, and 18 other; 10 of the 24 features were excluded. Detailed original decisions remain in the structured evidence.", "",
        "OpenQAOA ZNE requires a specific caution: `test_expectation_zne` returns before its assertion and is not a valid oracle. A notebook execution test and wrapper-count assertions supported candidate retention, but did not establish a validated numerical mitigation-accuracy oracle.", "",
        "## Evidence and reproduction", "",
        "- [all_pairs.json](all_pairs.json): source relations, issue states, and test-path gate results.",
        "- [review_candidates.csv](review_candidates.csv): static labels and keep decisions, with subsequent construction status recorded separately.",
        "- [pair_decisions.jsonl](pair_decisions.jsonl): ordered original decisions, reasons, and evidence locations.",
        "- [retained_pairs.csv](retained_pairs.csv): candidate test locations and construction risks.",
        "- [evidence/](evidence/): cached public metadata, patches, discussions, and reviews.",
        "- [source_snapshots/](source_snapshots/): historical workflow text and code, retained independently of Git history.",
        "- `collect.py` reads GitHub and reuses the cache; collect a new snapshot in a separate directory.",
        "- `review.py show N` displays a candidate; `record` stores explicit review decisions rather than inferring labels from keywords.",
        "- `python3 benchmark/dataset/repo_selection/issue_pr_screening_20260930/summarize.py` validates saved decisions and regenerates this English README offline.", ""])
    (ROOT / "README.md").write_text("\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
