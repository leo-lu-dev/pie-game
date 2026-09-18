from __future__ import annotations

import argparse
from pathlib import Path

from ..discovery import discover_configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover Data Commons candidate configs")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--entities", default=None, help="Comma-separated entity DCIDs; defaults to DATACOMMONS_ENTITY_DCIDS")
    parser.add_argument("--allow-fewer", action="store_true")
    args = parser.parse_args()
    entities = [value.strip() for value in args.entities.split(',') if value.strip()] if args.entities else None
    for path in discover_configs(args.count, args.output_dir, entities, args.allow_fewer):
        print(f"Discovered {path}")


if __name__ == "__main__":
    main()
