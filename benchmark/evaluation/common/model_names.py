"""Shared model-name normalization helpers for prediction artifacts."""

from __future__ import annotations


PROVIDER_PREFIXES = {
    "anthropic",
    "bytedance",
    "dashscope",
    "deepseek",
    "gemini",
    "google",
    "litellm-generic-dashscope",
    "litellm-generic-gemini",
    "litellm-generic-openai",
    "litellm-generic-openrouter",
    "openai",
    "openrouter",
    "vertex",
    "vertex_ai",
    "z-ai",
}


def prediction_model_name(model_name: object) -> str:
    """Return the model identity used in preds.json, without provider prefixes."""
    name = str(model_name or "").strip()
    while "/" in name:
        provider, _, bare_name = name.partition("/")
        if provider not in PROVIDER_PREFIXES or not bare_name:
            break
        name = bare_name
    return name
