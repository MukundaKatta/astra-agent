"""Provider registry — detect and instantiate the right LLM provider from model name."""

from __future__ import annotations

import os

from astra.providers.base import LLMProvider

# Model prefixes that map to providers
ANTHROPIC_PREFIXES = ("claude-", "claude")
OPENAI_PREFIXES = ("gpt-", "o1", "o3", "o4")
LOCAL_PREFIXES = ("ollama/", "local/", "lmstudio/")


def get_provider(model: str) -> tuple[LLMProvider, str]:
    """
    Get the appropriate provider for a model name.
    Returns (provider, clean_model_name).

    Examples:
        "claude-sonnet-4-20250514" -> (AnthropicProvider, "claude-sonnet-4-20250514")
        "gpt-4o" -> (OpenAIProvider, "gpt-4o")
        "ollama/llama3" -> (OpenAIProvider w/ localhost, "llama3")
        "local/codestral" -> (OpenAIProvider w/ localhost, "codestral")
    """
    # Check for local model prefixes
    for prefix in LOCAL_PREFIXES:
        if model.startswith(prefix):
            clean_name = model[len(prefix):]
            from astra.providers.openai_provider import OpenAIProvider

            if prefix == "ollama/":
                base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            elif prefix == "lmstudio/":
                base_url = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
            else:
                base_url = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")

            return OpenAIProvider(api_key="not-needed", base_url=base_url), clean_name

    # Check for OpenAI models
    if any(model.startswith(p) for p in OPENAI_PREFIXES):
        from astra.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(), model

    # Check if OPENAI_BASE_URL is set (custom provider)
    if os.environ.get("OPENAI_BASE_URL"):
        from astra.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(), model

    # Default to Anthropic
    from astra.providers.anthropic_provider import AnthropicProvider
    return AnthropicProvider(), model
