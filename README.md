# Pie of the Day

Pie of the Day is a daily data guessing game. Match each category label to the correct slice of a pie chart. You have four guesses, with correct placements locking as you play.

## Local candidate pipeline

Install Python dependencies with `python -m pip install -r requirements.txt`. The local commands load `.env.local` for `POSTGRES_URL` (or `DATABASE_URL`). Ingestion also requires `DATACOMMONS_API_KEY`. Candidate review stays local; no admin web account is required.

Create a JSON file describing one verified Data Commons dataset with exactly five mutually exclusive variables:

```json
{
  "dataset_id": "documented-source-id",
  "entity_dcid": "country/USA",
  "geography": "United States",
  "topic": "Example topic",
  "title": "How is this total divided?",
  "context": "Describe the measured population and year.",
  "denominator": "All members of the specified population",
  "measure": "count",
  "unit": "people",
  "population_universe": "Specified population",
  "date": "LATEST",
  "facet_id": null,
  "variables": [
    {"id": "a", "label": "Category A", "dcid": "verified-variable-1"},
    {"id": "b", "label": "Category B", "dcid": "verified-variable-2"},
    {"id": "c", "label": "Category C", "dcid": "verified-variable-3"},
    {"id": "d", "label": "Category D", "dcid": "verified-variable-4"},
    {"id": "e", "label": "Category E", "dcid": "verified-variable-5"}
  ]
}
```

The five variable IDs above are placeholders; verify the real IDs and denominator in Data Commons before ingestion. If several source facets share all five variables, set `facet_id` to the one you want to use.

```powershell
python -m data_pipeline.commands.ingest path\to\dataset.json
python -m data_pipeline.commands.review list
python -m data_pipeline.commands.review show CANDIDATE_ID
python -m data_pipeline.commands.review decide CANDIDATE_ID approved --reviewer your-name
python -m data_pipeline.commands.review promote CANDIDATE_ID --date 2026-10-01
```

Promotion creates a **scheduled** puzzle and never publishes it automatically. The publish date must be unused by another puzzle.
