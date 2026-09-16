from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import psycopg

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
    with psycopg.connect(database_url()) as connection:
        yield connection


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def persist_candidate(candidate: CandidatePuzzle, source: SourceDataset, validation: ValidationResult, connection: psycopg.Connection[Any]) -> str:
    """Persist a candidate and its audit records atomically.

    This function only writes to candidate tables. Promotion into ``puzzles``
    is intentionally a separate later operation.
    """
    candidate_id = candidate.id or str(uuid4())
    status = "validated" if validation.valid else "ingested"
    diagnostics = validation.diagnostics.__dict__ if validation.diagnostics else None
    candidate_data = candidate.model_dump()
    with connection.transaction():
        with connection.cursor() as cursor:
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
            cursor.executemany(
                "INSERT INTO candidate_categories (id, candidate_id, category_key, label, raw_value, display_order) VALUES (%s, %s, %s, %s, %s, %s)",
                [(str(uuid4()), candidate_id, category.id, category.label, str(category.raw_value), index) for index, category in enumerate(candidate.categories)],
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
    return review_id
