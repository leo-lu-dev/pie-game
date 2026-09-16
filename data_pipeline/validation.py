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


def validate_candidate_against_source(candidate: CandidatePuzzle, source: SourceDataset) -> ValidationResult:
    """Validate provenance, dimensions, and transformation math together."""
    result = validate_candidate(candidate)
    issues = list(result.issues)
    source_by_id = {value.category_id: value for value in source.values}
    candidate_ids = {category.id for category in candidate.categories}
    source_ids = set(source_by_id)

    dimensions = {
        "unit": (source.unit, candidate.unit),
        "geography": (source.geography, candidate.geography),
        "time_period": (source.time_period, candidate.time_period),
        "population_universe": (source.population_universe, candidate.population_universe),
        "facet_id": (source.facet_id, candidate.source_metadata.get("facetId")),
    }
    for name, (source_value, candidate_value) in dimensions.items():
        if source_value is not None and candidate_value is not None and source_value != candidate_value:
            issues.append(f"source and candidate {name} do not match")
    if candidate.source_dataset_id != source.source_dataset_id:
        issues.append("candidate source dataset ID does not match source dataset")

    metadata = candidate.transformation_metadata
    transformation = candidate.transformation_type
    if transformation == "meaningful-subset":
        selected = metadata.get("selected")
        if selected != [category.id for category in candidate.categories]:
            issues.append("subset metadata must list candidate categories in order")
        if not isinstance(selected, list) or any(category_id not in source_ids for category_id in selected):
            issues.append("subset contains an unknown source category")
    elif transformation == "four-plus-other":
        selected = metadata.get("selected")
        included = metadata.get("otherIncludes")
        if not isinstance(selected, list) or len(selected) != 4 or len(set(selected)) != 4:
            issues.append("four-plus-other metadata must select exactly four categories")
        if not isinstance(included, list) or set(selected or []) | set(included) != source_ids or set(selected or []) & set(included or []):
            issues.append("four-plus-other metadata must partition the source categories")
        expected_other = sum(source_by_id[category_id].value for category_id in (included or []) if category_id in source_by_id)
        other = next((category for category in candidate.categories if category.id == "other"), None)
        if other is None or abs(other.raw_value - expected_other) > 1e-9:
            issues.append("Other does not equal the sum of its source categories")
        if set(category.id for category in candidate.categories if category.id != "other") != set(selected or []):
            issues.append("candidate categories do not match four-plus-other selection")
    elif transformation in {"natural-five", "curated-five", "merged-categories"}:
        source_total = sum(value.value for value in source.values)
        candidate_total = sum(category.raw_value for category in candidate.categories)
        if abs(source_total - candidate_total) > max(1e-9, abs(source_total) * 1e-9):
            issues.append("transformation does not preserve the source total")

    final = validate_candidate(candidate)
    return ValidationResult(valid=not issues, issues=issues, diagnostics=final.diagnostics)
