from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .models.candidate import CandidatePuzzle
from .models.source import SourceDataset


@dataclass(frozen=True)
class CandidateDiagnostics:
    raw_total: float
    normalized_values: list[float]
    largest_share: float
    smallest_share: float
    value_range: float
    adjacent_sorted_gaps: list[float]
    near_equal_value_count: int
    dominance_ratio: float


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: list[str]
    diagnostics: CandidateDiagnostics | None = None


def normalize_values(values: list[float]) -> list[float]:
    total = sum(values)
    if not isfinite(total) or total <= 0:
        raise ValueError("values must have a positive finite total")
    return [value / total * 100 for value in values]


def diagnostics_for(values: list[float], near_equal_tolerance: float = 1.0) -> CandidateDiagnostics:
    normalized = normalize_values(values)
    ordered = sorted(normalized)
    gaps = [right - left for left, right in zip(ordered, ordered[1:])]
    near_equal_count = sum(1 for gap in gaps if gap <= near_equal_tolerance)
    smallest = min(normalized)
    largest = max(normalized)
    return CandidateDiagnostics(
        raw_total=sum(values),
        normalized_values=normalized,
        largest_share=largest,
        smallest_share=smallest,
        value_range=largest - smallest,
        adjacent_sorted_gaps=gaps,
        near_equal_value_count=near_equal_count,
        dominance_ratio=largest / smallest if smallest else float("inf"),
    )


def validate_source(dataset: SourceDataset) -> ValidationResult:
    issues: list[str] = []
    ids = [value.category_id for value in dataset.values]
    if len(ids) != len(set(ids)):
        issues.append("source category IDs must be unique")
    if len(dataset.values) < 5:
        issues.append("source must contain at least five values")
    if sum(value.value for value in dataset.values) <= 0:
        issues.append("source values must have a positive total")
    return ValidationResult(valid=not issues, issues=issues)


def validate_candidate(candidate: CandidatePuzzle) -> ValidationResult:
    issues: list[str] = []
    values = [category.raw_value for category in candidate.categories]
    if len(candidate.categories) != 5:
        issues.append("candidate must contain exactly five categories")
    if not all(isfinite(value) and value >= 0 for value in values):
        issues.append("candidate values must be finite and non-negative")
    try:
        diagnostics = diagnostics_for(values)
    except ValueError as error:
        issues.append(str(error))
        diagnostics = None
    return ValidationResult(valid=not issues, issues=issues, diagnostics=diagnostics)

