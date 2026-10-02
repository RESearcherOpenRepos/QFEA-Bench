from __future__ import annotations

from benchmark.evaluation.common.model_pricing import estimated_cost_usd
from benchmark.evaluation.common.model_pricing import normalize_model_name


def test_dashscope_qwen_pricing_converts_cny_to_usd_without_cache_discount() -> None:
    assert (
        estimated_cost_usd(
            "dashscope/qwen3.6-35b-a3b",
            {
                "input_tokens": 1_000_000,
                "cached_input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            },
        )
        == 1.849932
    )


def test_dashscope_glm5_pricing_converts_cny_to_usd_with_cache_discount() -> None:
    assert (
        estimated_cost_usd(
            "dashscope/glm-5",
            {
                "input_tokens": 1_000_000,
                "cached_input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            },
        )
        == 3.406224
    )


def test_dashscope_glm52_pricing_does_not_normalize_to_glm5() -> None:
    assert normalize_model_name("dashscope/glm-5.2") == "glm-5.2"
    assert (
        estimated_cost_usd(
            "dashscope/glm-5.2",
            {
                "input_tokens": 1_000_000,
                "cached_input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            },
        )
        == 4.4046
    )


def test_openrouter_zai_glm52_pricing_uses_shared_glm52_rate() -> None:
    assert normalize_model_name("openrouter/z-ai/glm-5.2") == "glm-5.2"
    assert (
        estimated_cost_usd(
            "openrouter/z-ai/glm-5.2",
            {
                "input_tokens": 1_000_000,
                "cached_input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
            },
        )
        == 4.4046
    )
