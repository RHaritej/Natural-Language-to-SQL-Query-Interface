"""OpenAI-compatible and remote API client."""

import os
import requests
from typing import List, Optional
from .base import BaseLLMClient, LLMMessage, LLMResponse


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI, Groq, or OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=prompt))
        return self.chat(messages, temperature=temperature, stop_sequences=stop_sequences)

    def chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        stop_sequences: Optional[List[str]] = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stop": stop_sequences or None,
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=tokens,
            finish_reason=choice.get("finish_reason"),
        )
