from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from typing import Any

from ..persistence.supabase import connect
from ..review_workflow import candidate_detail, list_candidates, promote_candidate, record_decision


def json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description='Review StatPie candidates locally')
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('list')
    show = actions.add_parser('show')
    show.add_argument('candidate_id')
    decide = actions.add_parser('decide')
    decide.add_argument('candidate_id')
    decide.add_argument('decision', choices=['approved', 'rejected', 'needs_review'])
    decide.add_argument('--reviewer', required=True)
    decide.add_argument('--notes')
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
        else:
            slug = promote_candidate(connection, args.candidate_id, args.date)
            print(f'Created scheduled puzzle {slug} for {args.date}; it is not published')


if __name__ == '__main__':
    main()
