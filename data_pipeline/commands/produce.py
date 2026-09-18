"""Keep discovering new topics until the requested number passes review."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..agents.critic import AgentCriticError, review_candidate
from ..agents.factory import critic_transport_from_env
from ..agents.prompts import PROMPT_VERSION
from ..discovery import discover_configs, topic_search_terms
from ..persistence.supabase import connect, mark_candidate_needs_review, persist_agent_review
from ..review_workflow import candidate_detail, candidate_from_detail, existing_candidate_summaries
from ..validation import CandidateDiagnostics
from .ingest import IngestConfig, ingest

STATE_PATH = Path('.discovery-state.json')
GENERATED_DIR = Path('.generated-candidates')


def _write_candidate_snapshot(directory: Path, candidate_id: str, detail: dict) -> None:
    """Keep a durable JSON export of every candidate committed to the database."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{candidate_id}.json'
    temporary_path = path.with_suffix('.json.tmp')
    temporary_path.write_text(json.dumps(detail, indent=2, default=str) + '\n', encoding='utf-8')
    temporary_path.replace(path)


def _words(value: str) -> set[str]:
    return {word for word in re.findall(r'[a-z0-9]+', value.lower()) if len(word) > 3}


def _similar_area(term: str, areas: set[str]) -> bool:
    words = _words(term)
    return bool(words) and any(len(words & _words(area)) >= max(1, min(2, len(words))) for area in areas)


def passed(review):
    return (review.verdict == 'approve' and review.recommended_action == 'approve'
            and review.semantic_validity and review.denominator_clear and review.question_accurate)


def produce(count: int) -> None:
    accepted = 0
    state_path = STATE_PATH
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    searched: set[str] = set(state.get('searchedTerms', []))
    blocked_areas: set[str] = set(state.get('blockedAreas', []))
    catalog = topic_search_terms()
    seen: set[tuple[str, ...]] = set()
    # Database history survives separate invocations; compare variable IDs independently
    # of generated category keys, titles, source facet and recipe numbering.
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT topic, source_metadata_json FROM puzzle_candidates')
            for row in cursor.fetchall():
                if row['topic']:
                    blocked_areas.add(row['topic'])
                metadata = row['source_metadata_json'] or {}
                variables = metadata.get('variables', {})
                if variables:
                    seen.add((metadata.get('entityDcid'), *sorted(variables.values())))

    with critic_transport_from_env() as critic:
        run_dir = GENERATED_DIR / f'run-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}'
        run_dir.mkdir(parents=True, exist_ok=True)
        batch = 0
        while accepted < count:
            terms = [term for term in catalog if term not in searched and not _similar_area(term, blocked_areas)][:4]
            if not terms:
                raise RuntimeError(f'Only {accepted}/{count} candidates passed; the Data Commons topic catalogue is exhausted')
            batch += 1
            print(f'[pipeline] {accepted}/{count} vetted; searching batch {batch}: {", ".join(terms)}', flush=True)
            batch_dir = run_dir / f'batch-{batch:03d}'
            batch_dir.mkdir(parents=True, exist_ok=True)
            for term_index, term in enumerate(terms, start=1):
                if accepted >= count:
                    break
                # Mark only the topic currently being attempted. If the run is
                # interrupted, later topics in this batch remain available.
                searched.add(term)
                state_path.write_text(json.dumps({
                    'searchedTerms': sorted(searched),
                    'blockedAreas': sorted(blocked_areas),
                }, indent=2) + '\n', encoding='utf-8')
                # Discover exactly one recipe, then take it through ingestion,
                # validation and AI review before looking for another topic.
                term_dir = batch_dir / f'topic-{term_index:02d}'
                paths = discover_configs(1, term_dir, allow_fewer=True,
                                         search_terms=[term], seen=seen)
                if not paths:
                    continue
                path = paths[0]
                config = IngestConfig.model_validate_json(path.read_text(encoding='utf-8'))
                print(f'[pipeline] Validating and saving: {config.topic}', flush=True)
                try:
                    candidate_id = ingest(config)
                except ValueError as error:
                    print(f'[pipeline] Skipped: {error}', flush=True)
                    continue
                with connect() as connection:
                    detail = candidate_detail(connection, candidate_id)
                    _write_candidate_snapshot(GENERATED_DIR, candidate_id, detail)
                    candidate = candidate_from_detail(detail)
                    diagnostics = CandidateDiagnostics(**detail['validations'][0]['diagnostics_json'])
                    print(f'[pipeline] AI review: {candidate_id}', flush=True)
                    # Infrastructure failures propagate; do not consume more candidates
                    # while the review service is unavailable.
                    try:
                        review = review_candidate(candidate, diagnostics, critic,
                                                  existing_candidate_summaries(connection, candidate_id))
                    except AgentCriticError:
                        mark_candidate_needs_review(candidate_id, connection)
                        _write_candidate_snapshot(GENERATED_DIR, candidate_id,
                                                  candidate_detail(connection, candidate_id))
                        raise
                    persist_agent_review(candidate_id, review, critic.model, PROMPT_VERSION, connection)
                    _write_candidate_snapshot(GENERATED_DIR, candidate_id,
                                              candidate_detail(connection, candidate_id))
                print(f'[pipeline] {review.verdict}: {"; ".join(review.issues)}', flush=True)
                if passed(review):
                    accepted += 1
                    print(f'[pipeline] Accepted {accepted}/{count}: {candidate_id}', flush=True)
                else:
                    blocked_areas.add(config.topic)
                state_path.write_text(json.dumps({
                    'searchedTerms': sorted(searched),
                    'blockedAreas': sorted(blocked_areas),
                }, indent=2) + '\n', encoding='utf-8')
            if accepted < count:
                print('[pipeline] Target not reached; searching new subject areas.', flush=True)
    print(f'[pipeline] Complete: {accepted} new AI-vetted puzzles ready for human testing.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', required=True, type=int)
    args = parser.parse_args()
    if args.count < 1:
        parser.error('--count must be positive')
    try:
        produce(args.count)
    except AgentCriticError as error:
        raise SystemExit(f'AI review unavailable after retries: {error}')
    except KeyboardInterrupt:
        raise SystemExit('Stopped by user; saved candidates and reviews are retained.')


if __name__ == '__main__':
    main()
