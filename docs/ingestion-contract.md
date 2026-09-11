# Puzzle ingestion boundary

Future data workers should hand the application normalized `CandidatePuzzle` values from `lib/ingestion.ts`.

The worker owns source-specific collection and any transformation needed to make a meaningful five-slice puzzle. The core game only needs the normalized title, categories, raw values, and optional source metadata. It does not depend on whether the worker used `natural-five`, `curated-five`, `meaningful-subset`, `four-plus-other`, or `merged-categories`.

Candidates should be reviewed and published into the `puzzles` and `puzzle_categories` tables separately. Source integrations, scoring, category merging, and editorial workflows are intentionally outside this boundary.
