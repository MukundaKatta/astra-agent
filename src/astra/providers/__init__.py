"""LLM provider abstraction — supports Anthropic, OpenAI, and local models."""

from __future__ import annotations

from astra.providers.base import LLMProvider
from astra.providers.registry import get_provider

__all__ = ["LLMProvider", "get_provider"]
