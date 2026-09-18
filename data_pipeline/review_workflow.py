"""Local candidate review and deliberate promotion into the game."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from .models.candidate import CandidatePuzzle

Decision = Literal['approved', 'rejected', 'needs_review']


def list_candidates(connection: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, title, source_name, status, created_at FROM puzzle_candidates ORDER BY created_at DESC')
        return list(cursor.fetchall())


def candidate_detail(connection: psycopg.Connection[Any], candidate_id: str) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM puzzle_candidates WHERE id = %s', (candidate_id,))
        candidate = cursor.fetchone()
        if candidate is None:
            raise ValueError('Candidate not found')
        cursor.execute('SELECT category_key, label, raw_value, display_order FROM candidate_categories WHERE candidate_id = %s ORDER BY display_order', (candidate_id,))
        categories = list(cursor.fetchall())
        cursor.execute('SELECT technical_valid, dimension_valid, transformation_valid, diagnostics_json, issues_json, created_at FROM candidate_validations WHERE candidate_id = %s ORDER BY created_at DESC', (candidate_id,))
        validations = list(cursor.fetchall())
        cursor.execute('SELECT model, prompt_version, verdict, review_json, created_at FROM candidate_agent_reviews WHERE candidate_id = %s ORDER BY created_at DESC', (candidate_id,))
        reviews = list(cursor.fetchall())
    return {'candidate': candidate, 'categories': categories, 'validations': validations, 'reviews': reviews}


def candidate_from_detail(detail: dict[str, Any]) -> CandidatePuzzle:
    """Reconstruct the review model from the persisted candidate records."""
    candidate = detail['candidate']
    return CandidatePuzzle.model_validate({
        'id': candidate['id'],
        'source_name': candidate['source_name'],
        'source_dataset_id': candidate['source_dataset_id'],
        'source_url': candidate['source_url'],
        'topic': candidate['topic'],
        'title': candidate['title'],
        'context': candidate['context'],
        'geography': candidate['geography'],
        'time_period': candidate['time_period'],
        'unit': candidate['unit'],
        'population_universe': candidate['population_universe'],
        'transformation_type': candidate['transformation_type'],
        'categories': [
            {'id': row['category_key'], 'label': row['label'], 'raw_value': row['raw_value']}
            for row in detail['categories']
        ],
        'transformation_metadata': candidate['transformation_metadata_json'] or {},
        'source_metadata': candidate['source_metadata_json'] or {},
    })


def record_decision(connection: psycopg.Connection[Any], candidate_id: str, decision: Decision, reviewer: str, notes: str | None = None) -> None:
    if decision not in ('approved', 'rejected', 'needs_review'):
        raise ValueError('Invalid decision')
    if not reviewer.strip():
        raise ValueError('Reviewer is required')
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute('SELECT status FROM puzzle_candidates WHERE id = %s FOR UPDATE', (candidate_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError('Candidate not found')
            if row['status'] == 'promoted':
                raise ValueError('A promoted candidate cannot be reviewed again')
            if decision == 'approved':
                cursor.execute('SELECT technical_valid, dimension_valid, transformation_valid FROM candidate_validations WHERE candidate_id = %s ORDER BY created_at DESC LIMIT 1', (candidate_id,))
                validation = cursor.fetchone()
                if validation is None or not all(validation.values()):
                    raise ValueError('Cannot approve a candidate without a passing validation')
            cursor.execute('UPDATE puzzle_candidates SET status = %s, human_status = %s, human_notes = %s, reviewed_by = %s, reviewed_at = now(), updated_at = now() WHERE id = %s', (decision, decision, notes, reviewer, candidate_id))


def promote_candidate(connection: psycopg.Connection[Any], candidate_id: str, publish_date: date) -> str:
    """Create a scheduled puzzle. Publishing remains a separate editorial action."""
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM puzzle_candidates WHERE id = %s FOR UPDATE', (candidate_id,))
            candidate = cursor.fetchone()
            if candidate is None:
                raise ValueError('Candidate not found')
            if candidate['status'] != 'approved' or candidate['human_status'] != 'approved':
                raise ValueError('Candidate requires human approval before promotion')
            cursor.execute('SELECT technical_valid, dimension_valid, transformation_valid FROM candidate_validations WHERE candidate_id = %s ORDER BY created_at DESC LIMIT 1', (candidate_id,))
            validation = cursor.fetchone()
            if validation is None or not all(validation.values()):
                raise ValueError('Candidate requires a passing validation before promotion')
            cursor.execute('SELECT category_key, label, raw_value, display_order FROM candidate_categories WHERE candidate_id = %s ORDER BY display_order', (candidate_id,))
            categories = list(cursor.fetchall())
            if len(categories) != 5 or len({row['category_key'] for row in categories}) != 5:
                raise ValueError('Promotion requires exactly five distinct categories')
            cursor.execute('SELECT id FROM puzzles WHERE candidate_id = %s', (candidate_id,))
            if cursor.fetchone() is not None:
                raise ValueError('Candidate has already been promoted')
            puzzle_id = str(uuid4())
            slug = f'real-{puzzle_id[:12]}'
            source_metadata = {
                'candidateId': candidate_id,
                'sourceDatasetId': candidate['source_dataset_id'],
                'transformationType': candidate['transformation_type'],
                'transformation': candidate['transformation_metadata_json'],
                'source': candidate['source_metadata_json'],
            }
            cursor.execute('INSERT INTO puzzles (id, slug, title, context, max_attempts, status, publish_date, source_name, source_url, source_metadata, candidate_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (puzzle_id, slug, candidate['title'], candidate['context'], 4, 'scheduled', publish_date, candidate['source_name'], candidate['source_url'], Jsonb(source_metadata), candidate_id))
            cursor.executemany('INSERT INTO puzzle_categories (id, puzzle_id, category_key, label, raw_value, slice_order) VALUES (%s, %s, %s, %s, %s, %s)', [(str(uuid4()), puzzle_id, row['category_key'], row['label'], row['raw_value'], row['display_order']) for row in categories])
            cursor.execute("UPDATE puzzle_candidates SET status = 'promoted', updated_at = now() WHERE id = %s", (candidate_id,))
    return slug
