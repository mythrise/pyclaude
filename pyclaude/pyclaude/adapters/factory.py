"""Adapter factory."""

from __future__ import annotations

from pyclaude.config import Config

from .anthropic_adapter import AnthropicAdapter
from .base import BaseLLMAdapter
from .ollama_adapter import OllamaAdapter
from .openai_compat import OpenAICompatAdapter


def create_adapter(config: Config) -> BaseLLMAdapter:
    backend = config.llm.backend.lower()
    if backend == "anthropic":
        return AnthropicAdapter(model=config.llm.model, api_key=config.llm.api_key)
    if backend == "ollama":
        return OllamaAdapter(model=config.llm.model, base_url=config.llm.base_url)
    if backend == "openai_compat":
        return OpenAICompatAdapter(
            model=config.llm.model,
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
        )
    raise ValueError(f"Unsupported LLM backend: {config.llm.backend}")
