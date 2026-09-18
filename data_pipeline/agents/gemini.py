"""Gemini transport for the candidate review critic."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from .critic import AgentCriticError, CriticTransport


class GeminiCriticTransport(CriticTransport):
    """Call Gemini's generateContent endpoint with JSON-only output."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Gemini API key is required")
        if not model.strip():
            raise ValueError("Gemini model is required")
        self.api_key = api_key
        self.model = model
        self._client = client or httpx.Client(timeout=60.0)
        self._owns_client = client is None

    @classmethod
    def from_env(cls, model: str | None = None) -> "GeminiCriticTransport":
        load_dotenv(".env.local")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY before running the agent critic")
        return cls(api_key=api_key, model=model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }
        try:
            response = self._client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise AgentCriticError(f"Gemini request failed for model {self.model}") from error

        try:
            parts = body["candidates"][0]["content"]["parts"]
            text = "".join(part["text"] for part in parts if "text" in part).strip()
        except (KeyError, IndexError, TypeError) as error:
            raise AgentCriticError("Gemini returned no candidate review text") from error
        if not text:
            raise AgentCriticError("Gemini returned an empty candidate review")
        return text

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "GeminiCriticTransport":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
