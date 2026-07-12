"""DNC Execution Providers: Ollama, vLLM, OpenAI, Anthropic, Gemini.

Per Phase 5C-5E (mvp-roadmap.md): Reference providers for local and cloud inference.
Local providers (Ollama, vLLM) enable reproducible experiments without API keys.
Cloud providers (OpenAI, Anthropic, Gemini) enable broad compatibility.
"""

from __future__ import annotations

from dnc.providers.ollama import OllamaConfig, OllamaProvider
from dnc.providers.vllm import vLLMConfig, vLLMProvider
from dnc.providers.openai import OpenAIConfig, OpenAIProvider
from dnc.providers.anthropic import AnthropicConfig, AnthropicProvider
from dnc.providers.gemini import GeminiConfig, GeminiProvider

__all__ = [
    # Local providers (5C)
    "OllamaConfig",
    "OllamaProvider",
    "vLLMConfig",
    "vLLMProvider",
    # Cloud providers (5E)
    "OpenAIConfig",
    "OpenAIProvider",
    "AnthropicConfig",
    "AnthropicProvider",
    "GeminiConfig",
    "GeminiProvider",
]