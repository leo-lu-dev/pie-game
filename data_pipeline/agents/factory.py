"""Select the configured candidate-review provider."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .gemini import GeminiCriticTransport
from .ollama import OllamaCriticTransport


def critic_transport_from_env(model: str | None = None):
    load_dotenv(".env.local")
    provider = os.getenv("CRITIC_PROVIDER", "gemini").strip().lower()
    if provider == "ollama":
        return OllamaCriticTransport.from_env(model)
    if provider == "gemini":
        return GeminiCriticTransport.from_env(model)
    raise RuntimeError(f"Unsupported CRITIC_PROVIDER: {provider}. Use 'ollama' or 'gemini'.")
