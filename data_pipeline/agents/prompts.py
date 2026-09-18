from __future__ import annotations

import json
from typing import Any

from ..models.candidate import CandidatePuzzle
from ..validation import CandidateDiagnostics

SYSTEM_PROMPT = """You are reviewing candidate StatPie puzzles before publication. Your job is to identify reasons a puzzle may be misleading, invalid, boring, too obvious, too niche, or semantically incoherent. Do not try to rescue bad candidates. Numerical values are authoritative source data and must not be changed. Evaluate the puzzle as presented and return only valid JSON matching the requested schema."""
PROMPT_VERSION = "v1"


def build_review_prompt(candidate: CandidatePuzzle, diagnostics: CandidateDiagnostics | None) -> str:
    categories = [
        {"id": category.id, "label": category.label, "rawValue": category.raw_value}
        for category in candidate.categories
    ]
    diagnostic_data: dict[str, Any] = diagnostics.__dict__ if diagnostics else {}
    review_input = {
        "title": candidate.title,
        "context": candidate.context,
        "topic": candidate.topic,
        "categories": categories,
        "transformationType": candidate.transformation_type,
        "transformationMetadata": candidate.transformation_metadata,
        "geography": candidate.geography,
        "timePeriod": candidate.time_period,
        "unit": candidate.unit,
        "populationUniverse": candidate.population_universe,
        "source": {
            "name": candidate.source_name,
            "datasetId": candidate.source_dataset_id,
            "url": candidate.source_url,
            "metadata": candidate.source_metadata,
        },
        "deterministicDiagnostics": diagnostic_data,
    }
    return """Review this candidate as a skeptical editor. Assess semantic validity, denominator clarity, wording accuracy, general-audience fit, intuition potential, obviousness, niche risk, misleading risk, category quality, and transformation quality. Do not alter numerical values or silently invent facts. Return JSON with exactly these fields: verdict, semantic_validity, denominator_clear, question_accurate, general_audience_fit (1-5), intuition_potential (1-5), obviousness_risk, niche_risk, misleading_risk, category_quality, issues (array of strings), suggested_title, suggested_context, recommended_action.\n\nCandidate:\n""" + json.dumps(review_input, indent=2, sort_keys=True)
