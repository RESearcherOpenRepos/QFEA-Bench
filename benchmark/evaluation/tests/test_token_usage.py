from __future__ import annotations

from benchmark.evaluation.common.redaction import REDACTED, redact_sensitive_values
from benchmark.evaluation.common.token_usage import (
    cumulative_token_records,
    token_counts_from_usage,
    token_records_from_usages,
    token_totals_from_records,
)


def test_token_counts_normalize_provider_aliases() -> None:
    assert token_counts_from_usage(
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "prompt_cache_hit_tokens": 70,
            "prompt_cache_creation_input_tokens": 5,
        }
    ) == {
        "input_tokens": 100,
        "cached_input_tokens": 70,
        "cache_creation_input_tokens": 5,
        "output_tokens": 20,
    }

    assert token_counts_from_usage(
        {
            "input_tokens": 80,
            "output_tokens": 12,
            "cache_read_tokens": 60,
            "cache_write_tokens": 3,
        }
    ) == {
        "input_tokens": 80,
        "cached_input_tokens": 60,
        "cache_creation_input_tokens": 3,
        "output_tokens": 12,
    }

    assert token_counts_from_usage(
        {
            "prompt_tokens": 40,
            "completion_tokens": 8,
            "prompt_tokens_details": {"cached_tokens": 22},
        }
    )["cached_input_tokens"] == 22


def test_token_records_dedupe_response_ids_and_cumulate_cache() -> None:
    records, cumulative = token_records_from_usages(
        [
            {
                "response_id": "a",
                "input_tokens": 10,
                "output_tokens": 1,
                "cached_input_tokens": 4,
            },
            {
                "response_id": "a",
                "input_tokens": 999,
                "output_tokens": 999,
            },
            {
                "response_id": "b",
                "input_tokens": 20,
                "output_tokens": 2,
                "cache_creation_input_tokens": 3,
            },
        ],
        dedupe_response_ids=True,
    )

    assert records == [
        {
            "step": 1,
            "input_tokens": 10,
            "cached_input_tokens": 4,
            "cache_creation_input_tokens": 0,
            "output_tokens": 1,
            "total_tokens": 11,
        },
        {
            "step": 2,
            "input_tokens": 20,
            "cached_input_tokens": 0,
            "cache_creation_input_tokens": 3,
            "output_tokens": 2,
            "total_tokens": 22,
        },
    ]
    assert cumulative == [
        {
            "step": 1,
            "input_tokens": 10,
            "cached_input_tokens": 4,
            "cache_creation_input_tokens": 0,
            "output_tokens": 1,
            "total_tokens": 11,
        },
        {
            "step": 2,
            "input_tokens": 30,
            "cached_input_tokens": 4,
            "cache_creation_input_tokens": 3,
            "output_tokens": 3,
            "total_tokens": 33,
        },
    ]
    assert token_totals_from_records(records) == {
        "input_tokens": 30,
        "cached_input_tokens": 4,
        "cache_creation_input_tokens": 3,
        "output_tokens": 3,
    }


def test_cumulative_token_records_accept_legacy_token_names() -> None:
    assert cumulative_token_records(
        [
            {
                "step": 1,
                "tokens_sent": 5,
                "tokens_received": 2,
                "cache_read_tokens": 1,
            },
            {
                "step": 2,
                "input_tokens": 7,
                "output_tokens": 3,
                "cache_write_tokens": 4,
            },
        ]
    )[-1] == {
        "step": 2,
        "input_tokens": 12,
        "cached_input_tokens": 1,
        "cache_creation_input_tokens": 4,
        "output_tokens": 5,
        "total_tokens": 17,
    }


def test_redact_sensitive_values_keeps_token_metrics() -> None:
    payload = {
        "model_kwargs": {
            "api_key": "sk-secret",
            "aws_session_token": "session-secret",
            "input_tokens": 123,
            "token_by_step": [{"step": 1, "output_tokens": 4}],
        }
    }

    redacted = redact_sensitive_values(payload)

    assert redacted["model_kwargs"]["api_key"] == REDACTED
    assert redacted["model_kwargs"]["aws_session_token"] == REDACTED
    assert redacted["model_kwargs"]["input_tokens"] == 123
    assert redacted["model_kwargs"]["token_by_step"] == [{"step": 1, "output_tokens": 4}]
