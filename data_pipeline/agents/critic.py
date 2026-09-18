from __future__ import annotations

import json
from typing import Protocol

from pydantic import ValidationError

from ..models.candidate import CandidatePuzzle
from ..models.review import AgentReview
from ..validation import CandidateDiagnostics
from .prompts import SYSTEM_PROMPT, build_review_prompt


class CriticTransport(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return the model's response text."""


class AgentCriticError(RuntimeError):
    """Raised when the critic does not return a valid structured review."""


def parse_review(response_text: str) -> AgentReview:
    """Parse strict review JSON, accepting an optional markdown code fence."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    try:
        return AgentReview.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as error:
        raise AgentCriticError("critic returned invalid structured JSON") from error


def review_candidate(candidate: CandidatePuzzle, diagnostics: CandidateDiagnostics | None, transport: CriticTransport, existing_candidates: list[dict] | None = None) -> AgentReview:
    response = transport.complete(system_prompt=SYSTEM_PROMPT, user_prompt=build_review_prompt(candidate, diagnostics, existing_candidates))
    return parse_review(response)
