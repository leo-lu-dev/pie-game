from __future__ import annotations

import json
from typing import Any

from ..models.candidate import CandidatePuzzle
from ..validation import CandidateDiagnostics

SYSTEM_PROMPT = """You are reviewing candidate Split Decision puzzles before publication. Your job is to identify reasons a puzzle may be misleading, invalid, boring, too obvious, too niche, or semantically incoherent. Do not try to rescue bad candidates. Numerical values are authoritative source data and must not be changed. Do not reinforce stereotypes or stigmatize demographic groups. Treat race/ethnicity cross-tabs involving crime, criminal justice, poverty, income, wealth, finances, debt, unemployment, or similarly stigmatizing outcomes as unsuitable for publication. Reject candidates whose categories overlap, contain totals alongside their component subsets, or do not form a meaningful partition. Evaluate the puzzle as presented and return only valid JSON matching the requested schema."""
PROMPT_VERSION = "v2"


def build_review_prompt(candidate: CandidatePuzzle, diagnostics: CandidateDiagnostics | None, existing_candidates: list[dict[str, Any]] | None = None) -> str:
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
            "metadata": {
                key: candidate.source_metadata.get(key)
                for key in ("entityDcid", "observedDate", "facetId", "variables", "labels", "denominator")
                if key in candidate.source_metadata
            },
        },
        "deterministicDiagnostics": diagnostic_data,
        "existingCandidates": existing_candidates or [],
    }
    return """Review this candidate as a skeptical editor. Assess semantic validity, denominator clarity, wording accuracy, general-audience fit, intuition potential, obviousness, niche risk, misleading risk, category quality, transformation quality, and similarity to existing candidates. Reject the candidate if it is materially the same puzzle as an existing candidate, even if its wording differs. Reject race/ethnicity cross-tabs involving sensitive or stigmatizing outcomes, including crime, criminal justice, poverty, income, wealth, finances, debt, and unemployment. Check that categories are mutually exclusive and collectively meaningful; a total population, gender split, or demographic subset must not be mixed into the same pie. If transformationMetadata contains an Other category, use otherIncludes together with source.labels to determine exactly what Other means. For ordered groups such as age bands, education levels, or household size, the named categories should begin at the lowest available band and proceed continuously; a middle band should not be hidden inside Other while later bands remain named. Do not alter numerical values or silently invent facts. Suggest concise category labels when the current labels are verbose, but preserve every category's meaning and return a label for every category ID. Keep the label "Other" exactly as "Other". Return JSON with exactly these fields: verdict, semantic_validity, denominator_clear, question_accurate, general_audience_fit (1-5), intuition_potential (1-5), obviousness_risk, niche_risk, misleading_risk, category_quality, issues (array of strings), suggested_title, suggested_context, suggested_category_labels (object mapping every category ID to a concise label, or null), recommended_action.\n\nCandidate and existing candidates:\n""" + json.dumps(review_input, indent=2, sort_keys=True)
