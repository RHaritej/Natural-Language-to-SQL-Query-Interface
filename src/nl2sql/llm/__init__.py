"""LLM client interfaces and factory."""

from typing import Optional
from .base import BaseLLMClient, LLMMessage, LLMResponse
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from .mock_client import MockLLMClient
from ..config import SystemConfig, default_config


def get_llm_client(config: Optional[SystemConfig] = None) -> BaseLLMClient:
    """Instantiate the appropriate LLM client based on system configuration."""
    cfg = config or default_config
    provider = (cfg.provider or "ollama").lower()

    if provider == "ollama":
        return OllamaClient(model=cfg.ollama_model, host=cfg.ollama_host)
    elif provider in ("openai", "groq", "together"):
        return OpenAIClient(api_key=cfg.openai_api_key, model=cfg.openai_model)
    elif provider == "gemini":
        return GeminiClient(api_key=cfg.gemini_api_key, model=cfg.gemini_model)
    elif provider == "mock":
        return MockLLMClient()
    else:
        # Fallback to Ollama or Mock
        try:
            return OllamaClient(model=cfg.ollama_model, host=cfg.ollama_host)
        except Exception:
            return MockLLMClient()


__all__ = [
    "BaseLLMClient",
    "LLMMessage",
    "LLMResponse",
    "OllamaClient",
    "OpenAIClient",
    "GeminiClient",
    "MockLLMClient",
    "get_llm_client",
]
