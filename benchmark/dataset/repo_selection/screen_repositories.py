#!/usr/bin/env python3
"""Fetch or replay GitHub screening evidence. Standard library + gh for live reads.

Examples (from this directory):
  python3 screen_repositories.py screen --snapshot snapshots/2026-09-30.json --output /tmp/repo-screen
  python3 screen_repositories.py fetch --snapshot /tmp/github-current.json
  python3 screen_repositories.py validate
"""
import argparse
import csv
import json
import re
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_csv(path, rows):
    if not rows:
        raise ValueError('No rows to write; refusing to produce an ambiguous empty audit')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def github(query):
    for attempt in range(5):
        try:
            result = subprocess.run(['gh', 'api', 'graphql', '-f', 'query=' + query],
                                    text=True, capture_output=True, timeout=90)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if not data.get('errors'):
                    return data['data']
            message = result.stderr[:300]
        except subprocess.TimeoutExpired:
            message = 'Request timeout'
        print(f'GitHub retry {attempt + 1}: {message}', flush=True)
        time.sleep(min(5 * (attempt + 1), 25))
    raise RuntimeError('Incomplete GitHub fetch; no complete snapshot will be written')


def search(query, with_counts):
    cursor, nodes, counts, raw_pages = None, [], [], []
    fields = 'databaseId nameWithOwner'
    if with_counts:
        fields += (' url description stargazerCount isFork isArchived primaryLanguage { name } '
                   'closedIssues: issues(states: CLOSED) { totalCount } '
                   'mergedPRs: pullRequests(states: MERGED) { totalCount }')
    while True:
        gql = ('query { search(type: REPOSITORY, query: ' + json.dumps(query) +
               ', first: 50, after: ' + json.dumps(cursor) + ') { repositoryCount '
               'pageInfo { hasNextPage endCursor } nodes { ... on Repository { ' + fields + ' } } } }')
        result = github(gql)['search']
        raw_pages.append({'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                          'query': gql, 'result': result})
        counts.append(result['repositoryCount'])
        if counts[-1] > 1000:
            raise RuntimeError('GitHub search exceeds 1000 results; partition the search before reporting a count')
        if any(node is None for node in result['nodes']):
            raise RuntimeError('GitHub returned an unavailable repository')
        nodes.extend(result['nodes'])
        print(f'{query}: {len(nodes)}/{counts[-1]}', flush=True)
        if not result['pageInfo']['hasNextPage']:
            break
        cursor = result['pageInfo']['endCursor']
    if len(set(counts)) != 1 or len(nodes) != counts[0] or len({n['databaseId'] for n in nodes}) != len(nodes):
        raise RuntimeError('Pagination duplicates or changing search count; retry the snapshot')
    return nodes, raw_pages


def fetch(criteria, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Choose a new snapshot path; preserving {output}')
    started = datetime.now(timezone.utc).isoformat()
    nodes, pages = search(criteria['primary_query'], True)
    repositories = [{
        'repo_id': n['databaseId'], 'repository': n['nameWithOwner'], 'url': n['url'],
        'description': n['description'] or '', 'stars': n['stargazerCount'],
        'fork': n['isFork'], 'archived': n['isArchived'],
        'language': (n['primaryLanguage'] or {}).get('name'),
        'closed_issues': n['closedIssues']['totalCount'], 'merged_prs': n['mergedPRs']['totalCount']
    } for n in nodes]
    keyword_results = []
    raw = {'primary': pages, 'keywords': []}
    for keyword in criteria['keywords_any']:
        query = f'"{keyword}" in:{criteria["keyword_search_fields"]} stars:>{criteria["stars_exclusive_min"]} fork:false'
        hits, pages = search(query, False)
        keyword_results.append({'keyword': keyword, 'query': query, 'total_count': len(hits),
                                'repository_ids': [n['databaseId'] for n in hits]})
        raw['keywords'].append({'keyword': keyword, 'pages': pages})
    snapshot = {'schema_version': 1, 'started_utc': started,
                'finished_utc': datetime.now(timezone.utc).isoformat(),
                'primary_query': criteria['primary_query'], 'repositories': repositories,
                'keyword_results': keyword_results,
                'provenance': 'Fresh GitHub GraphQL queries. Raw pages stored beside this snapshot.'}
    write_json(output.with_suffix('.raw.json'), raw)
    write_json(output, snapshot)


def select(snapshot, criteria):
    if snapshot['primary_query'] != criteria['primary_query']:
        raise ValueError('Snapshot primary query does not match criteria')
    rows = snapshot['repositories']
    if len(rows) != len({r['repo_id'] for r in rows}):
        raise ValueError('Duplicate repository IDs')
    searches = {s['keyword']: s for s in snapshot['keyword_results']}
    if set(searches) != set(criteria['keywords_any']):
        raise ValueError('Missing or unexpected keyword search')
    memberships = {}
    for keyword, entry in searches.items():
        expected_query = f'"{keyword}" in:{criteria["keyword_search_fields"]} stars:>{criteria["stars_exclusive_min"]} fork:false'
        if entry['query'] != expected_query or len(set(entry['repository_ids'])) != entry['total_count']:
            raise ValueError('Incomplete or mismatched keyword search')
        for repo_id in entry['repository_ids']:
            memberships.setdefault(repo_id, []).append(keyword)
    if criteria['language_filter'] is not None or criteria['archive_filter'] is not None or criteria['include_forks']:
        raise ValueError('This workflow implements the documented no-language/no-archive, non-fork criteria only')
    basic = [r for r in rows if not r['fork'] and r['stars'] > criteria['stars_exclusive_min']]
    closed = [r for r in basic if r['closed_issues'] > criteria['closed_issues_exclusive_min']]
    merged = [r for r in closed if r['merged_prs'] > criteria['merged_prs_exclusive_min']]
    selected = [{**r, 'matched_keywords': '; '.join(memberships[r['repo_id']])}
                for r in merged if r['repo_id'] in memberships]
    selected.sort(key=lambda r: (-r['stars'], r['repository'].lower()))
    summary = {'snapshot_started_utc': snapshot['started_utc'], 'snapshot_finished_utc': snapshot['finished_utc'],
               'primary_candidates': len(basic), 'after_closed_issues': len(closed),
               'after_merged_prs': len(merged), 'after_keywords': len(selected),
               'study_type': criteria['study_type'], 'language_filter': None, 'archive_filter': None}
    return selected, summary


def export(snapshot, criteria, output):
    rows, summary = select(snapshot, criteria)
    write_csv(Path(output) / 'candidates.csv', rows)
    write_json(Path(output) / 'screening_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def validate(snapshot, criteria):
    candidates, summary = select(snapshot, criteria)
    saved = read_csv(ROOT / 'candidates.csv')
    audit = read_csv(ROOT / 'manual_audit.csv')
    manifest = read_csv(ROOT / 'selected_repositories.csv')
    expected = {r['repository'] for r in candidates}
    for label, rows in [('candidates', saved), ('manual audit', audit)]:
        if len(rows) != len(expected) or {r['repository'] for r in rows} != expected:
            raise ValueError(f'{label} does not cover every automatic candidate exactly once')
    saved_by_id = {int(r['repo_id']): r for r in saved}
    for row in candidates:
        saved_row = saved_by_id[row['repo_id']]
        for key in ['stars', 'closed_issues', 'merged_prs']:
            if int(saved_row[key]) != row[key]:
                raise ValueError(f'Candidate count mismatch: {row["repository"]}/{key}')
    index = read_json(ROOT.parent / 'samples/index.json')
    cohorts = Counter(row['repo'] for row in index['samples'])
    existing_manifest = [r for r in manifest if r['selection_basis'] == 'existing_dataset_membership']
    new_manifest = [r for r in manifest if r['selection_basis'] == 'user_admitted_for_pair_screening']
    historical_repos = {r['repository'] for r in existing_manifest}
    new_executable = {r['repository'] for r in new_manifest if int(r['sample_count']) > 0}
    if historical_repos | new_executable != set(cohorts):
        raise ValueError('Existing manifest does not match executable dataset membership')
    if len(existing_manifest) + len(new_manifest) != len(manifest) or len({r['repository'] for r in manifest}) != len(manifest):
        raise ValueError('Invalid or duplicate selected repository entry')
    admitted = {r['repository'] for r in audit if r['scope_assessment'] == 'retain_for_pair_screening'}
    if admitted != {r['repository'] for r in new_manifest}:
        raise ValueError('New repository admission and manifest disagree')
    included = {r['repository'] for r in audit if r['current_cohort'] == 'include_existing'}
    if included != historical_repos or not included <= expected:
        raise ValueError('Audit inclusion and existing dataset membership disagree')
    for row in existing_manifest:
        if int(row['sample_count']) != cohorts[row['repository']]:
            raise ValueError('Incorrect sample count in final manifest')
        path = ROOT / row['example_sample_metadata']
        if not path.is_file():
            raise ValueError(f'Missing sample evidence: {path}')
    for row in new_manifest:
        count = cohorts[row['repository']]
        if int(row['sample_count']) != count:
            raise ValueError('New repository sample count disagrees with executable index')
        if count:
            path = ROOT / row['example_sample_metadata']
            if not path.is_file():
                raise ValueError('Missing runtime-validated sample evidence')
        elif row['example_sample_metadata'] or row['sample_ids']:
            raise ValueError('Repository without executable samples claims sample evidence')
    for row in audit:
        if not row['evidence_url'] or not row['scope_rationale']:
            raise ValueError('Every draft scope assessment needs evidence and a rationale')
        if row['scope_assessment'] not in {'retain_existing', 'retain_for_pair_screening', 'exclude_proposed', 'needs_exclusion_evidence'}:
            raise ValueError('Unknown scope assessment')
        if row['reason_code'] not in criteria['reason_codes']:
            raise ValueError('Unknown scope reason code')
        if row['human_review_status'] not in {'pending', 'completed'}:
            raise ValueError('Unknown human review status')
        if row['human_scope_decision'] not in {'', 'retain', 'exclude', 'needs_evidence'}:
            raise ValueError('Unknown human scope decision')
        if row['human_review_status'] == 'completed' and not (
                row['human_reviewer'] and re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['human_review_date'])
                and row['human_scope_decision'] and row['human_notes']):
            raise ValueError('Human audit marked complete without a decision, reviewer, date and notes')
        if row['repository'] not in included | admitted and row['instance_audit_status'] != 'not_audited':
            raise ValueError('Nonselected repositories must not claim unaudited sample feasibility')
        if row['repository'] in admitted and row['instance_audit_status'] not in {'pair_screening_in_progress', 'pair_screening_complete_not_runtime_validated', 'runtime_validation_in_progress', 'runtime_validation_complete'}:
            raise ValueError('Incorrect instance-validation status for newly admitted repository')
    summary_path = ROOT / 'audit_summary.json'
    if summary_path.exists():
        audit_summary = read_json(summary_path)
        actual_counts = dict(Counter(row['scope_assessment'] for row in audit))
        if audit_summary['draft_scope_assessments'] != actual_counts:
            raise ValueError('Audit summary does not match row decisions')
    unresolved = read_csv(ROOT / 'unresolved_scope.csv')
    if {r['repository'] for r in unresolved} != {
            r['repository'] for r in audit if r['scope_assessment'] == 'needs_exclusion_evidence'}:
        raise ValueError('Unresolved-scope list is stale')
    deep_path = ROOT / 'deep_review.csv'
    if deep_path.exists():
        details = read_csv(deep_path)
        evidence = read_json(ROOT / 'evidence/deep_review_evidence.json')['repositories']
        by_name = {row['repository']: row for row in audit}
        if len(details) != len({r['repository'] for r in details}) or set(evidence) != {r['repository'] for r in details}:
            raise ValueError('Deep-review coverage mismatch')
        for row in details:
            master = by_name[row['repository']]
            if (row['updated_scope_assessment'], row['reason_code']) != (master['scope_assessment'], master['reason_code']):
                raise ValueError('Deep-review decision differs from the audit master')
            if row['source_evidence'] != evidence[row['repository']]['primary_evidence']:
                raise ValueError('Deep-review evidence link mismatch')
    print(json.dumps({**summary, 'audit_rows': len(audit), 'selected_repositories': len(manifest),
                      'existing_dataset_repositories': len(existing_manifest),
                      'newly_admitted_repositories': len(new_manifest),
                      'existing_samples': sum(cohorts.values()),
                      'pending_human_reviews': sum(r['human_review_status'] == 'pending' for r in audit),
                      'validation': 'passed'}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fetch', 'screen', 'validate'])
    parser.add_argument('--criteria', type=Path, default=ROOT / 'criteria.json')
    parser.add_argument('--snapshot', type=Path, default=ROOT / 'snapshots/2026-09-30.json')
    parser.add_argument('--output', type=Path, help='Required for screen; use a new directory for a new snapshot')
    args = parser.parse_args()
    criteria = read_json(args.criteria)
    if args.command == 'fetch':
        fetch(criteria, args.snapshot)
    elif args.command == 'screen':
        if args.output is None:
            parser.error('screen requires --output to avoid accidentally replacing saved evidence')
        export(read_json(args.snapshot), criteria, args.output)
    else:
        validate(read_json(args.snapshot), criteria)


if __name__ == '__main__':
    main()
