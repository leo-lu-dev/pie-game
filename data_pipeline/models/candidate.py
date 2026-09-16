from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TransformationType = Literal[
    "natural-five",
    "curated-five",
    "meaningful-subset",
    "four-plus-other",
    "merged-categories",
]


class CandidateCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    raw_value: float

    @field_validator("raw_value")
    @classmethod
    def raw_value_must_be_finite_and_nonnegative(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")) or value < 0:
            raise ValueError("candidate values must be finite and non-negative")
        return value


class CandidatePuzzle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    source_name: str = Field(min_length=1)
    source_dataset_id: str = Field(min_length=1)
    source_url: str | None = None
    topic: str = Field(min_length=1)
    title: str = Field(min_length=1)
    context: str | None = None
    geography: str | None = None
    time_period: str | None = None
    unit: str | None = None
    population_universe: str | None = None
    transformation_type: TransformationType
    categories: list[CandidateCategory] = Field(min_length=5, max_length=5)
    transformation_metadata: dict[str, Any] = Field(default_factory=dict)
    source_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("categories")
    @classmethod
    def categories_must_be_unique(cls, categories: list[CandidateCategory]) -> list[CandidateCategory]:
        ids = [category.id for category in categories]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate category IDs must be unique")
        return categories

