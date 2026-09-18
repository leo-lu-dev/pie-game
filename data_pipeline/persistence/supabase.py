from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ..models.candidate import CandidatePuzzle
from ..models.source import SourceDataset
from ..models.review import AgentReview
from ..validation import ValidationResult


def database_url() -> str:
    value = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not value:
        raise RuntimeError("Set DATABASE_URL or POSTGRES_URL before using pipeline persistence")
    return value


@contextmanager
def connect() -> Iterator[psycopg.Connection[Any]]:
    from dotenv import load_dotenv

    load_dotenv('.env.local')
    with psycopg.connect(database_url(), row_factory=dict_row) as connection:
        yield connection


def _json(value: Any) -> Jsonb:
    return Jsonb(value, dumps=lambda item: json.dumps(item, default=str))


def persist_candidate(candidate: CandidatePuzzle, source: SourceDataset, validation: ValidationResult, connection: psycopg.Connection[Any]) -> str:
    """Persist a candidate and its audit records atomically.

    This function only writes to candidate tables. Promotion into ``puzzles``
    is intentionally a separate later operation.
    """
    candidate_id = candidate.id or str(uuid4())
    status = "validated" if validation.valid else "ingested"
    diagnostics = validation.diagnostics.__dict__ if validation.diagnostics else None
    candidate_data = candidate.model_dump()
    source_key = {
        "entityDcid": source.source_metadata.get("entityDcid"),
        "variables": source.source_metadata.get("variables"),
        "facetId": source.facet_id,
        "observedDate": source.time_period,
    }
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("SELECT source_metadata_json FROM puzzle_candidates")
            for existing in cursor.fetchall():
                existing_metadata = existing["source_metadata_json"] or {}
                existing_key = {
                    "entityDcid": existing_metadata.get("entityDcid"),
                    "variables": existing_metadata.get("variables"),
                    "facetId": existing_metadata.get("facetId"),
                    "observedDate": existing_metadata.get("observedDate"),
                }
                if existing_key == source_key:
                    raise ValueError("Duplicate candidate: this Data Commons dataset, variables, facet, and date already exist")
            cursor.execute(
                """
                INSERT INTO puzzle_candidates (
                  id, source_name, source_dataset_id, source_url, topic, title,
                  context, geography, time_period, unit, population_universe,
                  transformation_type, transformation_metadata_json,
                  source_metadata_json, raw_payload_json, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    candidate_id, candidate_data["source_name"], candidate_data["source_dataset_id"], candidate_data["source_url"],
                    candidate_data["topic"], candidate_data["title"], candidate_data["context"], candidate_data["geography"],
                    candidate_data["time_period"], candidate_data["unit"], candidate_data["population_universe"], candidate_data["transformation_type"],
                    _json(candidate_data["transformation_metadata"]), _json(source.source_metadata), _json(source.raw_payload), status,
                ),
            )
            ordered_categories = sorted(enumerate(candidate.categories), key=lambda item: (-item[1].raw_value, item[0]))
            cursor.executemany(
                "INSERT INTO candidate_categories (id, candidate_id, category_key, label, raw_value, display_order) VALUES (%s, %s, %s, %s, %s, %s)",
                [(str(uuid4()), candidate_id, category.id, category.label, str(category.raw_value), index) for index, (_, category) in enumerate(ordered_categories)],
            )
            cursor.execute(
                "INSERT INTO candidate_validations (id, candidate_id, technical_valid, dimension_valid, transformation_valid, diagnostics_json, issues_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (str(uuid4()), candidate_id, validation.valid, validation.valid, validation.valid, _json(diagnostics or {}), _json(validation.issues)),
            )
    return candidate_id


def persist_agent_review(candidate_id: str, review: AgentReview, model: str, prompt_version: str, connection: psycopg.Connection[Any]) -> str:
    """Append an agent review without overwriting earlier reviews."""
    review_id = str(uuid4())
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO candidate_agent_reviews (id, candidate_id, model, prompt_version, verdict, review_json) VALUES (%s, %s, %s, %s, %s, %s)",
                (review_id, candidate_id, model, prompt_version, review.verdict, _json(review.model_dump())),
            )
            status = {'approve': 'agent_reviewed', 'review': 'needs_review', 'reject': 'rejected'}[review.verdict]
            cursor.execute("UPDATE puzzle_candidates SET status = %s, updated_at = now() WHERE id = %s AND status <> 'promoted'", (status, candidate_id))
            ai_gate_passed = (
                review.verdict == 'approve'
                and review.recommended_action == 'approve'
                and review.semantic_validity
                and review.denominator_clear
                and review.question_accurate
            )
            suggestions = review.suggested_category_labels
            if ai_gate_passed and suggestions:
                cursor.execute("SELECT category_key FROM candidate_categories WHERE candidate_id = %s", (candidate_id,))
                category_ids = {row['category_key'] for row in cursor.fetchall()}
                labels = {category_id: label.strip() for category_id, label in suggestions.items() if isinstance(label, str)}
                valid_labels = (
                    set(labels) == category_ids
                    and all(labels.values())
                    and len({label.casefold() for label in labels.values()}) == len(labels)
                    and ("other" not in labels or labels["other"] == "Other")
                )
                if valid_labels:
                    cursor.executemany(
                        "UPDATE candidate_categories SET label = %s WHERE candidate_id = %s AND category_key = %s",
                        [(label, candidate_id, category_id) for category_id, label in labels.items()],
                    )
    return review_id


def mark_candidate_needs_review(candidate_id: str, connection: psycopg.Connection[Any]) -> None:
    """Keep a valid candidate available when an agent review cannot complete."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("UPDATE puzzle_candidates SET status = 'needs_review', updated_at = now() WHERE id = %s AND status <> 'promoted'", (candidate_id,))
