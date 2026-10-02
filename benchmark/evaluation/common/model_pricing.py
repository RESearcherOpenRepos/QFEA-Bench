"""Shared model pricing helpers for evaluation cost estimates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelPricing:
    model: str
    input_usd_per_million: float
    cached_input_usd_per_million: float
    output_usd_per_million: float
    source: str
    note: str = ""


MODEL_PRICING = {
    "deepseek-v4-flash": ModelPricing(
        model="deepseek-v4-flash",
        input_usd_per_million=0.14,
        cached_input_usd_per_million=0.0028,
        output_usd_per_million=0.28,
        source="https://api-docs.deepseek.com/quick_start/pricing",
        note="DeepSeek V4 Flash; cache miss input, cache hit input, output.",
    ),
    "deepseek-v4-pro": ModelPricing(
        model="deepseek-v4-pro",
        input_usd_per_million=0.435,
        cached_input_usd_per_million=0.003625,
        output_usd_per_million=0.87,
        source="https://api-docs.deepseek.com/quick_start/pricing",
        note="DeepSeek V4 Pro; cache miss input, cache hit input, output.",
    ),
    "gemini-3-flash-preview": ModelPricing(
        model="gemini-3-flash-preview",
        input_usd_per_million=0.50,
        cached_input_usd_per_million=0.05,
        output_usd_per_million=3.00,
        source="https://ai.google.dev/gemini-api/docs/pricing",
        note="Gemini 3 Flash Preview Standard tier for text/image/video input.",
    ),
    "gpt-5.5": ModelPricing(
        model="gpt-5.5",
        input_usd_per_million=5.00,
        cached_input_usd_per_million=0.50,
        output_usd_per_million=30.00,
        source="https://openai.com/api/pricing/",
        note="OpenAI GPT-5.5 Standard processing.",
    ),
    "qwen3.6-35b-a3b": ModelPricing(
        model="qwen3.6-35b-a3b",
        input_usd_per_million=0.264276,
        cached_input_usd_per_million=0.264276,
        output_usd_per_million=1.585656,
        source="user-provided DashScope pricing converted with Frankfurter/ECB CNY->USD 0.14682 from 2026-06-24",
        note="DashScope Qwen3.6-35B-A3B; user-provided CNY prices were input/cache input 1.8 and output 10.8 per 1M tokens.",
    ),
    "glm-5": ModelPricing(
        model="glm-5",
        input_usd_per_million=0.88092,
        cached_input_usd_per_million=0.176184,
        output_usd_per_million=3.23004,
        source="user-provided DashScope pricing converted with Frankfurter/ECB CNY->USD 0.14682 from 2026-06-24",
        note="DashScope GLM-5; user-provided CNY prices were input 6, cached input 1.2, and output 22 per 1M tokens.",
    ),
    "glm-5.2": ModelPricing(
        model="glm-5.2",
        input_usd_per_million=1.17456,
        cached_input_usd_per_million=0.29364,
        output_usd_per_million=4.11096,
        source="user-provided DashScope pricing converted with Frankfurter/ECB CNY->USD 0.14682 from 2026-06-24",
        note="DashScope GLM-5.2; user-provided CNY prices were input 8, cached input 2, and output 28 per 1M tokens.",
    ),
}


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_model_name(model_name: str | None) -> str:
    name = (model_name or "").lower()
    if "deepseek-v4-flash" in name:
        return "deepseek-v4-flash"
    if "deepseek-v4-pro" in name:
        return "deepseek-v4-pro"
    if "gemini-3-flash" in name:
        return "gemini-3-flash-preview"
    if "gpt-5.5" in name or "gpt55" in name:
        return "gpt-5.5"
    if "qwen3.6-35b-a3b" in name:
        return "qwen3.6-35b-a3b"
    if "glm-5.2" in name or "glm5.2" in name or "glm52" in name:
        return "glm-5.2"
    if "glm-5" in name or "glm5" in name:
        return "glm-5"
    return name


def pricing_for_model(model_name: str | None) -> ModelPricing | None:
    return MODEL_PRICING.get(normalize_model_name(model_name))


def estimated_cost_usd(model_name: str | None, metrics: dict[str, Any]) -> float | None:
    """Return estimated cost in USD."""
    pricing = pricing_for_model(model_name)
    if pricing is None:
        return None

    input_tokens = as_int(metrics.get("input_tokens"))
    cached_input_tokens = min(as_int(metrics.get("cached_input_tokens")), input_tokens)
    cache_creation_input_tokens = as_int(metrics.get("cache_creation_input_tokens"))
    output_tokens = as_int(metrics.get("output_tokens"))
    uncached_input_tokens = max(input_tokens - cached_input_tokens, 0)

    return (
        uncached_input_tokens * pricing.input_usd_per_million
        + cached_input_tokens * pricing.cached_input_usd_per_million
        + cache_creation_input_tokens * pricing.input_usd_per_million
        + output_tokens * pricing.output_usd_per_million
    ) / 1_000_000


def pricing_rows() -> list[dict[str, Any]]:
    return [
        {
            "model": pricing.model,
            "input_usd_per_million": pricing.input_usd_per_million,
            "cached_input_usd_per_million": pricing.cached_input_usd_per_million,
            "cache_creation_input_usd_per_million": pricing.input_usd_per_million,
            "output_usd_per_million": pricing.output_usd_per_million,
            "source": pricing.source,
            "note": pricing.note,
        }
        for pricing in MODEL_PRICING.values()
    ]
