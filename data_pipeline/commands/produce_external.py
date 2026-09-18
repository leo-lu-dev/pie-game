"""Produce candidates from the curated public-source provider catalog."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from dotenv import load_dotenv

from ..agents.critic import AgentCriticError, review_candidate
from ..agents.factory import critic_transport_from_env
from ..agents.prompts import PROMPT_VERSION
from ..external_catalog import ExternalRecipe, recipes
from ..labels import concise_category_label
from ..models.candidate import CandidateCategory, CandidatePuzzle
from ..persistence.supabase import connect, mark_candidate_needs_review, persist_agent_review, persist_candidate
from ..review_workflow import candidate_detail, candidate_from_detail, existing_candidate_summaries
from ..selection import candidate_values, largest_share, largest_share_limit, ordered_selection
from ..sources.eurostat import EurostatAdapter, EurostatError
from ..sources.owid import OwidAdapter, OwidError
from ..validation import CandidateDiagnostics, validate_candidate_against_source, validate_source

from .produce import GENERATED_DIR, STATE_PATH, _write_candidate_snapshot, passed


def _source_for(recipe: ExternalRecipe):
    if recipe.provider == "owid":
        return OwidAdapter(
            **recipe.adapter_args,
            dataset_id=f"owid-{recipe.key}",
            measure=recipe.measure,
            unit=recipe.unit,
            geography=recipe.geography,
            population_universe=recipe.population_universe,
        )
    return EurostatAdapter(
        **recipe.adapter_args,
        dataset_id=f"eurostat-{recipe.key}",
        measure=recipe.measure,
        unit=recipe.unit,
        geography=recipe.geography,
        population_universe=recipe.population_universe,
    )


def _candidate_for(recipe: ExternalRecipe, source) -> CandidatePuzzle:
    source_categories = [
        CandidateCategory(
            id=value.category_id,
            label=concise_category_label(value.category_label, value.category_id),
            raw_value=value.value,
        )
        for value in source.values
    ]
    selection_rule: str | None = None
    if len(source_categories) == 5:
        categories = source_categories
        transformation_type = "natural-five"
        transformation_metadata = {"type": "natural-five"}
    else:
        selected = ordered_selection(source.values)
        if selected is None:
            eligible = [value for value in source.values if value.category_label.casefold() != "other"]
            selected = [value.category_id for value in sorted(eligible, key=lambda value: (-value.value, value.category_id))[:4]]
            selection_rule = "largest-values"
        else:
            selection_rule = "ordered-lowest-first"
        categories = None
        from ..transforms import four_plus_other

        categories, transformation_metadata = four_plus_other(source_categories, selected)
        transformation_metadata["selectionRule"] = selection_rule
        transformation_type = "four-plus-other"

    largest = largest_share(candidate_values(source.values, None if transformation_type == "natural-five" else transformation_metadata["selected"]))
    if largest >= largest_share_limit():
        raise ValueError(f"largest final slice is {largest:.1f}%, at or above the configured limit")

    source_metadata = {
        **source.source_metadata,
        "denominator": recipe.denominator,
        "recipeKey": recipe.key,
        "provider": recipe.provider,
    }
    return CandidatePuzzle(
        source_name=source.source_name,
        source_dataset_id=source.source_dataset_id,
        source_url=source.source_url,
        topic=recipe.topic,
        title=recipe.title,
        context=recipe.context,
        geography=source.geography,
        time_period=source.time_period,
        unit=source.unit,
        population_universe=source.population_universe,
        transformation_type=transformation_type,
        categories=categories,
        transformation_metadata=transformation_metadata,
        source_metadata=source_metadata,
    )


def _read_state() -> dict:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    state.setdefault("externalRecipes", [])
    return state


def _write_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def produce_external(count: int, provider: str = "all") -> int:
    load_dotenv(".env.local")
    state = _read_state()
    completed = set(state.get("externalRecipes", []))
    available = [recipe for recipe in recipes(provider) if recipe.key not in completed]
    accepted = 0
    run_dir = GENERATED_DIR / f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    with critic_transport_from_env() as critic:
        for index, recipe in enumerate(available, start=1):
            if accepted >= count:
                break
            print(f"[pipeline] External source {index}/{len(available)}: {recipe.provider}/{recipe.key}", flush=True)
            try:
                with _source_for(recipe) as adapter:
                    source = adapter.fetch()
                source_validation = validate_source(source)
                if not source_validation.valid:
                    raise ValueError("; ".join(source_validation.issues))
                candidate = _candidate_for(recipe, source)
                validation = validate_candidate_against_source(candidate, source)
                if not validation.valid:
                    raise ValueError("; ".join(validation.issues))
                with connect() as connection:
                    try:
                        candidate_id = persist_candidate(candidate, source, validation, connection)
                    except ValueError as error:
                        print(f"[pipeline] Skipped {recipe.key}: {error}", flush=True)
                        completed.add(recipe.key)
                        _write_state({**state, "externalRecipes": sorted(completed)})
                        continue
                    detail = candidate_detail(connection, candidate_id)
                    _write_candidate_snapshot(GENERATED_DIR, candidate_id, detail)
                    persisted_candidate = candidate_from_detail(detail)
                    diagnostics = CandidateDiagnostics(**detail["validations"][0]["diagnostics_json"])
                    print(f"[pipeline] AI review: {candidate_id}", flush=True)
                    try:
                        review = review_candidate(
                            persisted_candidate,
                            diagnostics,
                            critic,
                            existing_candidate_summaries(connection, candidate_id),
                        )
                    except AgentCriticError:
                        mark_candidate_needs_review(candidate_id, connection)
                        _write_candidate_snapshot(GENERATED_DIR, candidate_id, candidate_detail(connection, candidate_id))
                        raise
                    persist_agent_review(candidate_id, review, critic.model, PROMPT_VERSION, connection)
                    _write_candidate_snapshot(GENERATED_DIR, candidate_id, candidate_detail(connection, candidate_id))
                print(f"[pipeline] {review.verdict}: {'; '.join(review.issues)}", flush=True)
                if passed(review):
                    accepted += 1
                    print(f"[pipeline] Accepted {accepted}/{count}: {candidate_id}", flush=True)
                else:
                    print(f"[pipeline] Rejected by AI review: {recipe.key}", flush=True)
            except (OwidError, EurostatError, ValueError) as error:
                print(f"[pipeline] Skipped {recipe.key}: {error}", flush=True)
            finally:
                completed.add(recipe.key)
                state["externalRecipes"] = sorted(completed)
                _write_state(state)

    print(f"[pipeline] External sources produced {accepted}/{count} AI-vetted candidates.", flush=True)
    return accepted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--provider", choices=["all", "owid", "eurostat"], default="all")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    try:
        accepted = produce_external(args.count, args.provider)
    except AgentCriticError as error:
        raise SystemExit(f"AI review unavailable after retries: {error}")
    except KeyboardInterrupt:
        raise SystemExit("Stopped by user; saved candidates and reviews are retained.")
    if accepted < args.count:
        raise SystemExit(f"Only {accepted}/{args.count} external candidates passed the full pipeline.")


if __name__ == "__main__":
    main()
