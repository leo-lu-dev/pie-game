from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from typing import Any

from ..agents.critic import AgentCriticError, review_candidate
from ..agents.factory import critic_transport_from_env
from ..agents.prompts import PROMPT_VERSION
from ..persistence.supabase import mark_candidate_needs_review, persist_agent_review
from ..persistence.supabase import connect
from ..review_workflow import candidate_detail, candidate_from_detail, existing_candidate_summaries, list_candidates, promote_candidate, record_decision
from ..validation import CandidateDiagnostics


def json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description='Review Split Decision candidates locally')
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('list')
    show = actions.add_parser('show')
    show.add_argument('candidate_id')
    decide = actions.add_parser('decide')
    decide.add_argument('candidate_id')
    decide.add_argument('decision', choices=['approved', 'rejected', 'needs_review'])
    decide.add_argument('--reviewer', required=True)
    decide.add_argument('--notes')
    agent = actions.add_parser('agent')
    agent.add_argument('candidate_id')
    agent.add_argument('--model')
    promote = actions.add_parser('promote')
    promote.add_argument('candidate_id')
    promote.add_argument('--date', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    with connect() as connection:
        if args.action == 'list':
            print(json.dumps(list_candidates(connection), indent=2, default=json_default))
        elif args.action == 'show':
            print(json.dumps(candidate_detail(connection, args.candidate_id), indent=2, default=json_default))
        elif args.action == 'decide':
            record_decision(connection, args.candidate_id, args.decision, args.reviewer, args.notes)
            print(f'Recorded {args.decision} for {args.candidate_id}')
        elif args.action == 'agent':
            detail = candidate_detail(connection, args.candidate_id)
            candidate = candidate_from_detail(detail)
            validation = detail['validations'][0] if detail['validations'] else None
            diagnostics = CandidateDiagnostics(**validation['diagnostics_json']) if validation and validation['diagnostics_json'] else None
            try:
                with critic_transport_from_env(args.model) as transport:
                    review = review_candidate(candidate, diagnostics, transport, existing_candidate_summaries(connection, args.candidate_id))
            except (AgentCriticError, RuntimeError) as error:
                mark_candidate_needs_review(args.candidate_id, connection)
                print(f'AI review failed: {error}', file=sys.stderr)
                raise SystemExit(1)
            review_id = persist_agent_review(args.candidate_id, review, transport.model, PROMPT_VERSION, connection)
            print(json.dumps({'reviewId': review_id, 'model': transport.model, 'review': review.model_dump()}, indent=2))
        else:
            slug = promote_candidate(connection, args.candidate_id, args.date)
            print(f'Created scheduled puzzle {slug} for {args.date}; it is not published')


if __name__ == '__main__':
    main()
