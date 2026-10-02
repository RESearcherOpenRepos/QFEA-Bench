from __future__ import annotations

from benchmark.evaluation.common.model_names import prediction_model_name


def test_prediction_model_name_removes_known_provider_prefixes() -> None:
    assert prediction_model_name("openrouter/openai/gpt-5.5") == "gpt-5.5"
    assert prediction_model_name("litellm-generic-openrouter/openai/gpt-5.5") == "gpt-5.5"
    assert prediction_model_name("openrouter/z-ai/glm-5.2") == "glm-5.2"
    assert prediction_model_name("litellm-generic-openrouter/z-ai/glm-5.2") == "glm-5.2"
    assert prediction_model_name("dashscope/qwen3.6-35b-a3b") == "qwen3.6-35b-a3b"
    assert prediction_model_name("litellm-generic-dashscope/glm-5.2") == "glm-5.2"
    assert prediction_model_name("deepseek/deepseek-v4-pro") == "deepseek-v4-pro"
    assert prediction_model_name("vertex/gemini-3-flash-preview") == "gemini-3-flash-preview"
