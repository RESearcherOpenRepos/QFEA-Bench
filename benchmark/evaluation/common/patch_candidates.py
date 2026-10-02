"""Shared patch-candidate semantics for benchmark agent outputs."""

from __future__ import annotations

from typing import Any


PATCH_EXTRACTION_STATUS_ORDER = [
    "NO_PATCH",
    "RAW_PATCH_BUT_UNPARSED",
    "RAW_PATCH_BUT_UNMATCHED",
    "MATCHED_BUT_EMPTY_DIFF",
    "MATCHED_BUT_EMPTY_ORIGIN",
    "APPLICABLE_PATCH",
]
PATCH_CANDIDATE_STATUSES = set(PATCH_EXTRACTION_STATUS_ORDER) - {"NO_PATCH"}


def best_patch_extraction_status(statuses: list[str]) -> str | None:
    ranked = [status for status in statuses if status in PATCH_EXTRACTION_STATUS_ORDER]
    if not ranked:
        return None
    return max(ranked, key=PATCH_EXTRACTION_STATUS_ORDER.index)


def patch_candidate_metadata(
    *,
    model_patch: str = "",
    extraction_statuses: list[str] | None = None,
) -> dict[str, Any]:
    statuses = list(extraction_statuses or [])
    return {
        "patch_candidate_submitted": bool(
            str(model_patch or "").strip()
            or any(status in PATCH_CANDIDATE_STATUSES for status in statuses)
        ),
        "patch_extraction_status": best_patch_extraction_status(statuses),
        "patch_extraction_statuses": statuses,
    }
