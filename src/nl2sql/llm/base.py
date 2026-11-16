"""Base abstract interface for LLM client providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM completion providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Single turn text generation."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Multi-turn conversation chat."""
        pass
