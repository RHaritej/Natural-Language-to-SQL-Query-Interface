"""Google Gemini API client using standard HTTP REST interface."""

import os
import requests
from typing import List, Optional
from .base import BaseLLMClient, LLMMessage, LLMResponse


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini REST API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model

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
            raise ValueError("GEMINI_API_KEY is not set.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = {"parts": [{"text": msg.content}]}
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "stopSequences": stop_sequences or [],
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        resp = requests.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        
        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(content="", model=self.model)

        part_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return LLMResponse(content=part_text, model=self.model)
