from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["approve", "review", "reject"]
    semantic_validity: bool
    denominator_clear: bool
    question_accurate: bool
    general_audience_fit: int = Field(ge=1, le=5)
    intuition_potential: int = Field(ge=1, le=5)
    obviousness_risk: Literal["low", "medium", "high"]
    niche_risk: Literal["low", "medium", "high"]
    misleading_risk: Literal["low", "medium", "high"]
    category_quality: Literal["poor", "acceptable", "good"]
    issues: list[str] = Field(default_factory=list)
    suggested_title: str | None = None
    suggested_context: str | None = None
    suggested_category_labels: dict[str, str] | None = None
    recommended_action: Literal["approve", "human_review", "reject"]
