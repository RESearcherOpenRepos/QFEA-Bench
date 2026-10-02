"""Shared token-usage normalization for benchmark agent runners."""

from __future__ import annotations

from typing import Any, Iterable


INPUT_TOKEN_KEYS = ("input_tokens", "prompt_tokens", "tokens_sent")
OUTPUT_TOKEN_KEYS = ("output_tokens", "completion_tokens", "tokens_received")
CACHED_INPUT_TOKEN_KEYS = (
    "cached_input_tokens",
    "cache_read_tokens",
    "cache_read_input_tokens",
    "prompt_cache_hit_tokens",
)
CACHE_CREATION_INPUT_TOKEN_KEYS = (
    "cache_creation_input_tokens",
    "cache_write_tokens",
    "prompt_cache_creation_input_tokens",
)


def int_token_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def first_token_value(usage: dict[str, Any], keys: Iterable[str]) -> int:
    for key in keys:
        value = int_token_value(usage.get(key))
        if value:
            return value
    return 0


def token_counts_from_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    usage = usage or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    cached_input_tokens = first_token_value(usage, CACHED_INPUT_TOKEN_KEYS)
    if not cached_input_tokens and isinstance(prompt_details, dict):
        cached_input_tokens = int_token_value(prompt_details.get("cached_tokens"))
    return {
        "input_tokens": first_token_value(usage, INPUT_TOKEN_KEYS),
        "cached_input_tokens": cached_input_tokens,
        "cache_creation_input_tokens": first_token_value(
            usage,
            CACHE_CREATION_INPUT_TOKEN_KEYS,
        ),
        "output_tokens": first_token_value(usage, OUTPUT_TOKEN_KEYS),
    }


def token_record(
    step: int,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
) -> dict[str, int]:
    return {
        "step": step,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def token_record_from_usage(step: int, usage: dict[str, Any] | None) -> dict[str, int]:
    counts = token_counts_from_usage(usage)
    return token_record(
        step,
        counts["input_tokens"],
        counts["output_tokens"],
        counts["cached_input_tokens"],
        counts["cache_creation_input_tokens"],
    )


def cumulative_token_records(records: list[dict[str, int]]) -> list[dict[str, int]]:
    cumulative_input = 0
    cumulative_cached_input = 0
    cumulative_cache_creation_input = 0
    cumulative_output = 0
    cumulative: list[dict[str, int]] = []
    for record in records:
        cumulative_input += int_token_value(record.get("input_tokens") or record.get("tokens_sent"))
        cumulative_cached_input += int_token_value(
            record.get("cached_input_tokens") or record.get("cache_read_tokens")
        )
        cumulative_cache_creation_input += int_token_value(
            record.get("cache_creation_input_tokens") or record.get("cache_write_tokens")
        )
        cumulative_output += int_token_value(
            record.get("output_tokens") or record.get("tokens_received")
        )
        cumulative.append(
            token_record(
                int_token_value(record.get("step")) or len(cumulative) + 1,
                cumulative_input,
                cumulative_output,
                cumulative_cached_input,
                cumulative_cache_creation_input,
            )
        )
    return cumulative


def token_records_from_usages(
    usages: Iterable[dict[str, Any] | None],
    *,
    dedupe_response_ids: bool = False,
) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    records: list[dict[str, int]] = []
    seen_response_ids: set[str] = set()
    for usage in usages:
        usage = usage or {}
        if dedupe_response_ids:
            response_id = usage.get("response_id")
            if response_id:
                response_id = str(response_id)
                if response_id in seen_response_ids:
                    continue
                seen_response_ids.add(response_id)
        records.append(token_record_from_usage(len(records) + 1, usage))
    return records, cumulative_token_records(records)


def token_totals_from_records(records: list[dict[str, int]]) -> dict[str, int]:
    totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "output_tokens": 0,
    }
    for record in records:
        totals["input_tokens"] += int_token_value(record.get("input_tokens"))
        totals["cached_input_tokens"] += int_token_value(record.get("cached_input_tokens"))
        totals["cache_creation_input_tokens"] += int_token_value(
            record.get("cache_creation_input_tokens")
        )
        totals["output_tokens"] += int_token_value(record.get("output_tokens"))
    return totals
