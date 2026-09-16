from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: str = Field(min_length=1)
    category_label: str = Field(min_length=1)
    value: float

    @field_validator("value")
    @classmethod
    def value_must_be_finite_and_nonnegative(cls, value: float) -> float:
        if not isfinite(value) or value < 0:
            raise ValueError("source values must be finite and non-negative")
        return value


class SourceDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_dataset_id: str = Field(min_length=1)
    source_url: str | None = None
    measure: str = Field(min_length=1)
    unit: str | None = None
    geography: str | None = None
    time_period: str | None = None
    population_universe: str | None = None
    facet_id: str | None = None
    values: list[SourceValue] = Field(min_length=1)
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] | list[Any] | str

