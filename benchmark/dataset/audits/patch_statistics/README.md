# Dataset and comparison statistics

## Cross-benchmark patch statistics (Table 1)

QFEA-Bench covers all 117 active instances: the verified counts for the original 106 diffs are retained, and 11 retained extension base-to-patched diffs were extracted from the recorded Docker images using the same counting rule. SWE-bench Verified (500 tasks) and SWE-bench Pro **v1** (731 tasks) retain the recorded comparison statistics.

| Benchmark | Median files | Median added + deleted lines |
| --- | ---: | ---: |
| QFEA-Bench | 4 | 204 |
| SWE-bench Pro v1 | 4 | 94 |
| SWE-bench Verified | 1 | 7 |

### Definition

SWE-bench separates each PR diff into `patch` and `test_patch`. Its official `extract_patches` function assigns files whose paths contain `test`, `tests`, `e2e`, or `testing` to the test patch (case-sensitive); all remaining files belong to the gold patch. SWE-bench Pro likewise defines the gold patch as the diff excluding the test patch.

- Count all file entries in the non-test patch, including any non-test documentation or configuration files. Do not apply an additional source-extension filter.
- Count added plus deleted hunk lines, **including blank lines**, excluding diff headers and unchanged context. A replaced line contributes one deletion and one addition.
- Compute each measure per instance, then take the median over instances, without averaging repository medians.
- For SWE-bench and SWE-bench Pro, use their released `patch` fields directly. For QFEA-Bench, apply SWE-bench's path split to `git diff <base_commit> <patch>` from each sample's recorded image. No additional oracle-file filtering is applied.

This comparison differs intentionally from RQ2's task-specific patch-size measure, which counts designated `golden_patch.oracle_files` and nonempty changed lines. RQ2 statistics and group assignments are unchanged. The previous Table 1 values (3 files, 145.5 lines) did not use the unified scope and line-counting convention.

### Sources

- [SWE-bench patch extraction](https://github.com/SWE-bench/SWE-bench/blob/main/swebench/collect/utils.py), `extract_patches`.
- [SWE-bench Pro paper, Section 4.1](https://arxiv.org/html/2509.16941v2#S4.SS1).
- [SWE-bench Verified official test parquet](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet).
- [SWE-bench Pro official v1 test parquet](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/resolve/main/data/v1/test-00000-of-00001.parquet).

Input parquet SHA-256 checksums are recorded in `summary.json`. `instance_patch_stats.csv` contains per-instance counts for all three datasets.

### Reproduction

Save each QFEA full historical diff as `<instance_id>.patch` in one directory, using the base and patched commits and Docker image recorded in its `sample.json`:

```sh
docker run --rm --read-only --network none --platform linux/amd64 \
  --entrypoint git IMAGE -C /workspace/repo diff --no-ext-diff --no-color BASE PATCH
```

With `pandas`, `pyarrow`, and `unidiff` available, run from the repository root:

```sh
.venv/bin/python benchmark/dataset/scripts/summarize_patch_comparison.py \
  --qfea-patches /path/to/full-qfea-diffs \
  --swe-verified-test /path/to/swe-verified-test.parquet \
  --pro-v1-test /path/to/pro-v1-test.parquet \
  --output-dir benchmark/dataset/audits/patch_statistics
```

External datasets and full diff caches are not duplicated in this audit directory.

### QuanBench column

Uses the original 44-task version in [QuanBench44.jsonl](https://github.com/GuoXiaoYu1125/Quanbench/blob/main/QuanBench44.jsonl), matching the cited paper, rather than the expanded 117-task set. For each `complete_prompt`, parse the function named by `entry_point` with Python `ast`, extract its docstring with `ast.get_docstring`, and count whitespace-separated words (`len(docstring.split())`). This counts natural-language descriptions, excluding imports and function signatures. All 44 entries parse successfully; the median is 23 words. Per-task counts are in `quanbench_statement_stats.csv`.

The data has no separate requirements/interface-entry lists; an `entry_point` and function signature are provided within the prompt structure, so dashes do not imply absent interface information. Repository fix-patch and F2P/P2P metrics are not applicable to its standalone generation tasks. Complete canonical-solution size is reported separately from patch size under the common Solution heading, with this distinction stated in the table caption.

Input SHA-256: `1feb9d632c8a5cbb0a0f7802f544163a897800cd40af7c1d4ef8fe49ef1fe9cd`.

#### QuanBench reference program size

All 44 records provide one `canonical_solution` Python source unit. The official evaluator loads that string into one module (or falls back to a per-task `solution.py` file). Each source contains the specified top-level entry-point function. We count one source file per task and `len(canonical_solution.splitlines())` lines, including imports, signatures, comments, and blank lines. The median is **1 file and 14 lines**. These are complete program sizes, not edits to an existing repository.

Reproduce without executing any reference program:

```sh
python3 benchmark/dataset/scripts/summarize_quanbench_stats.py /path/to/QuanBench44.jsonl \
  --output-dir benchmark/dataset/audits/patch_statistics
```

`quanbench_solution_stats.csv` records all 44 tasks; `quanbench_summary.json` records the medians and input checksum. Source organization is verified against [the official evaluator](https://github.com/GuoXiaoYu1125/Quanbench/blob/main/Quanbench_eval/execution.py), function `build_check_program`.

### Verified task statistics and feature counts

The comparison now uses SWE-bench Verified (500 tasks), not the full SWE-bench split (2,294). Every statistic in that column was recomputed from the Verified release. Its medians are 1 non-test patch file, 7 added + deleted lines, 143 statement words, 1 F2P selector, and 50.5 P2P selectors. Per-instance task counts are saved in `external_task_stats.csv` alongside Pro v1 counts.

Statement length uses `len(problem_statement.split())`, the same whitespace-based word count used for QFEA-Bench and QuanBench's extracted task description. Under this rule, Pro v1 has a median of 165 words (replacing the previously displayed 167); the Verified median is 143. Test-list fields are parsed as JSON or, for Python-literal lists in Pro, with `ast.literal_eval`; selectors are counted as entries, not inferred from logs.

The feature numerators **68/500** for Verified and **316/731** for Pro come directly from [RealSWE, Table 7 and Appendix B.1](https://arxiv.org/html/2608.27831v1#A2.SS1). These are that study's GPT-5.4 task-type classifications based on problem statements, not task-type labels released by the original benchmark authors and not new labels produced in this repository. The paper also reports 432/500 and 413/731 bug tasks and 0/500 and 2/731 other tasks, respectively. This audit records the source independently of the manuscript citation list. No new full-SWE-bench classification is used.

### QFEA-Bench task statistics

The 117 active instances come from 11 repositories. Median task counts are 52 statement words, 6 requirements, 4 interfaces, 3 F2P tests, and 6 P2P tests; totals are 623 F2P and 994 P2P selectors. `qfea_task_stats.csv` records the per-instance counts, and `qfea_refresh_20261002.json` records the new diff provenance and a check that the previous 106 task medians reproduce the old table. Other benchmark columns are unchanged.

## Feature-instance counts: source verification

Table 1 now compares SWE-bench Pro v1, SWE-bench Verified, QuanBench, and QFEA-Bench.

| Benchmark | Features / Total | Source |
| --- | ---: | --- |
| SWE-bench Pro v1 | 316/731 | RealSWE Table 7, Appendix B.1 |
| SWE-bench Verified | 68/500 | RealSWE Table 7, Appendix B.1 |
| QuanBench | --/44 | Standalone function-generation tasks; repository feature-request count not applicable |
| QFEA-Bench | 117/117 | All retained instances passed feature-request screening |

[RealSWE](https://arxiv.org/html/2608.27831v1#A2.SS1) classifies problem statements using GPT-5.4 into bug, feature, or other. Pro's additional requirements and interfaces are excluded from classification. These figures are published counts from an independent study, not the original SWE-bench/Pro authors' labels or our own manual annotation. Its feature definition includes new or changed functionality. The paper reports 95% task-type classification accuracy against a human-annotated sample; this is not a guarantee that every label is correct.

The Verified total matches the [official 500-task release](https://openai.com/index/introducing-swe-bench-verified/). Pro uses the 731-task v1 public split, not the newer v2 split.

### Sources examined but not used as numerators

- Original [SWE-bench Table 13](https://arxiv.org/html/2310.06770v3) reports 167 Feature-category tag occurrences, not a verified distinct-instance count. It concerns the full dataset, which is no longer the Table 1 comparison set.
- The official Pro v1 parquet provides knowledge-domain `issue_categories`, not feature/bug labels. All 731 records in the official auxiliary `helper_code/sweap_eval_full_v2.jsonl` were checked and do not provide such a field. The official error-analysis CSV labels model failure modes, not task types.
- [FeatureBench](https://arxiv.org/html/2602.10975v1) gives an approximate 18–22% feature share without an exact count suitable for this table; [SWE-Bench++](https://arxiv.org/html/2512.17419v1) gives about 9%. Neither percentage is converted to an integer numerator.
- A public Marginlab browser exposes task-type tags, but its provenance was not established; it is not used.

The brief full-SWE-bench classification pilot was stopped when the comparison changed to Verified. No output from it contributes to the table.
