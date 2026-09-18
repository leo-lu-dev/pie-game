"""Gemini transport for the candidate review critic."""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from .critic import AgentCriticError, CriticTransport
from ..models.review import AgentReview


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
        self.response_schema = AgentReview.model_json_schema()
        self.minimum_interval = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "5"))
        self._last_request_at = 0.0
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
                "responseJsonSchema": self.response_schema,
                "temperature": 0.1,
                "maxOutputTokens": 1000,
            },
        }
        last_error: Exception | None = None
        for attempt in range(1, 5):
            try:
                wait = self.minimum_interval - (time.monotonic() - self._last_request_at)
                if wait > 0:
                    time.sleep(wait)
                self._last_request_at = time.monotonic()
                response = self._client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                break
            except httpx.HTTPStatusError as error:
                last_error = error
                if error.response.status_code not in (429, 500, 502, 503, 504) or attempt == 4:
                    detail = error.response.text[:500].replace("\n", " ")
                    raise AgentCriticError(f"Gemini request failed with HTTP {error.response.status_code}: {detail}") from error
                detail = error.response.text.lower()
                retry_after_header = error.response.headers.get("retry-after")
                # A project/day quota cannot be fixed by retrying. The generic
                # free-tier metric also covers per-minute limits, so only stop
                # immediately when the response identifies a day-long limit.
                daily_quota = any(marker in detail for marker in (
                    "generaterequestsperday",
                    "generatetokensperday",
                    "requests per day",
                    "tokens per day",
                    "per_day",
                    "perday",
                    "daily quota",
                ))
                if daily_quota:
                    raise AgentCriticError("Gemini daily quota is exhausted; retrying will not help until the quota resets") from error
                retry_after = retry_after_header
                retry_message = re.search(r"retry in\s+([\d.]+)s", detail)
                if not retry_after and retry_message:
                    retry_after = retry_message.group(1)
                try:
                    delay = max(5, float(retry_after)) if retry_after else 5 * (2 ** (attempt - 1))
                except ValueError:
                    delay = 5 * (2 ** (attempt - 1))
                if delay > 60:
                    raise AgentCriticError(f"Gemini requested a retry after {delay:.0f}s; stopping to avoid a long blocked run") from error
                print(f"Gemini temporary HTTP {error.response.status_code}; retrying in {delay}s ({attempt}/3)", file=sys.stderr, flush=True)
                time.sleep(delay)
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
                if attempt == 4:
                    raise AgentCriticError(f"Gemini request failed for model {self.model}") from error
                time.sleep(2 ** (attempt - 1))
        else:
            raise AgentCriticError(f"Gemini request failed for model {self.model}") from last_error

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
