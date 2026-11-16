"""Ollama local LLM client."""

import requests
from typing import List, Optional
from .base import BaseLLMClient, LLMMessage, LLMResponse


class OllamaClient(BaseLLMClient):
    """Client for local Ollama server running llama3.2, mistral, qwen, etc."""

    def __init__(self, model: str = "llama3.2:latest", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")

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
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "stop": stop_sequences or [],
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")
