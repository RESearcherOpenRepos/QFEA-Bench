# AutoCodeRover: supplementary experiment evidence

The current cohort contains **117 active tasks**. The authoritative evaluator files are the five `results_*.json` files in the [parent results directory](../); they retain 119 historical rows, filtered to 117 by the active dataset index. This migration does not change those files or the published outcomes.

## Contents and interpretation

This directory preserves 9 files from the former top-level provider-operation directories: 0 agent-specific files and 9 shared context files. Agent-specific predictions, evaluation snapshots, and diagnostics are under `agent/`. Cross-agent orchestration, recovery, cost, and completion records are under `shared_context/`, copied intact into each relevant agent archive. Shared copies describe the same experiments and must not be counted again.

- [Aliyun extension and recovery evidence](additions_20261001_aliyun/)
- [SiliconFlow / official-provider completion evidence](additions_20261002_siliconflow_pro/)
- [File manifest](manifest.json): original source path, archive destination, size, and SHA-256 for every preserved file.
- [Reconciliation](reconciliation.json): canonical file hashes, historical completion count checks, and field-level comparisons for archived evaluator snapshots.
- [Repository migration inventory](../../../../../docs/result-evidence-migration.json): coverage of both original directories, including the excluded caches and empty lock file.

Archived reports and runner sources retain their original bytes as `.md.txt` and `.py.txt`. Their original paths and commands document the historical environment; they are not live links or current execution instructions. Use the [review guide](../../../../../docs/README.md) for current verification commands.

## Relationship to final results

The historical completion audit agrees with the total row count and extension resolved count in all five canonical model files for this agent. The audit describes the former **106 + 13 = 119** cohort; it is not the current 117-task denominator. Reconciliation does not revalidate historical billing estimates or rerun model calls.

The migrated files for this agent contain shared completion and comparison evidence. No additional agent-specific evaluator snapshot was present in the two removed directories; the existing canonical results and comparison JSON remain unchanged.
