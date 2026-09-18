"""Local Ollama transport for the candidate review critic."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from .critic import AgentCriticError, CriticTransport
from ..models.review import AgentReview


class OllamaCriticTransport(CriticTransport):
    """Call a local Ollama model with a JSON Schema-constrained response."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3:8b",
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("Ollama base URL is required")
        if not model.strip():
            raise ValueError("Ollama model is required")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.response_schema = AgentReview.model_json_schema()
        self._client = client or httpx.Client(timeout=180.0)
        self._owns_client = client is None

    @classmethod
    def from_env(cls, model: str | None = None) -> "OllamaCriticTransport":
        load_dotenv(".env.local")
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=model or os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        )

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": self.response_schema,
            "options": {"temperature": 0.1},
        }
        try:
            response = self._client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as error:
            detail = error.response.text[:500].replace("\n", " ")
            raise AgentCriticError(
                f"Ollama request failed with HTTP {error.response.status_code}: {detail}"
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise AgentCriticError(f"Ollama request failed for model {self.model}") from error

        try:
            text = body["message"]["content"].strip()
        except (KeyError, TypeError, AttributeError) as error:
            raise AgentCriticError("Ollama returned no candidate review text") from error
        if not text:
            raise AgentCriticError("Ollama returned an empty candidate review")
        return text

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OllamaCriticTransport":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
