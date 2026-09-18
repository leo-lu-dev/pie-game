"""Ingest one explicitly configured five-category Data Commons dataset."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from ..models.candidate import CandidateCategory, CandidatePuzzle
from ..labels import concise_category_label
from ..persistence.supabase import connect, persist_candidate
from ..sources.datacommons import DataCommonsAdapter
from ..transforms import four_plus_other
from ..validation import validate_candidate_against_source, validate_source


class VariableSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    dcid: str = Field(min_length=1)


class IngestConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str = Field(min_length=1)
    entity_dcid: str = Field(min_length=1)
    geography: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    title: str = Field(min_length=1)
    context: str = Field(min_length=1)
    denominator: str = Field(min_length=1)
    measure: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    population_universe: str = Field(min_length=1)
    variables: list[VariableSpec] = Field(min_length=5)
    transformation_type: Literal['natural-five', 'four-plus-other'] = 'natural-five'
    selected_category_ids: list[str] | None = None
    selection_rule: str | None = None
    facet_id: str | None = None
    date: str = 'LATEST'


def ingest(config: IngestConfig) -> str:
    load_dotenv('.env.local')
    api_key = os.getenv('DATACOMMONS_API_KEY')
    if not api_key:
        raise RuntimeError('Set DATACOMMONS_API_KEY before ingestion')
    variable_dcids = {variable.id: variable.dcid for variable in config.variables}
    variable_labels = {variable.id: variable.label for variable in config.variables}
    ids = [variable.id for variable in config.variables]
    if len(set(ids)) != len(ids):
        raise ValueError('Variable category IDs must be unique')
    if config.transformation_type == 'natural-five' and len(ids) != 5:
        raise ValueError('natural-five requires exactly five source variables')
    if config.transformation_type == 'four-plus-other':
        selected_ids = config.selected_category_ids
        if selected_ids is None or len(selected_ids) != 4 or len(set(selected_ids)) != 4:
            raise ValueError('four-plus-other requires exactly four selected category IDs')
        if any(category_id not in ids for category_id in selected_ids):
            raise ValueError('four-plus-other selected category IDs must be source variables')
    with DataCommonsAdapter(
        entity_dcid=config.entity_dcid,
        variables=variable_dcids,
        labels=variable_labels,
        dataset_id=config.dataset_id,
        measure=config.measure,
        unit=config.unit,
        geography=config.geography,
        population_universe=config.population_universe,
        date=config.date,
        facet_id=config.facet_id,
        api_key=api_key,
    ) as adapter:
        source = adapter.fetch()
    source_validation = validate_source(source)
    if not source_validation.valid:
        raise ValueError('; '.join(source_validation.issues))
    source_categories = [CandidateCategory(
        id=value.category_id,
        label=concise_category_label(value.category_label, variable_dcids.get(value.category_id)),
        raw_value=value.value,
    ) for value in source.values]
    if config.transformation_type == 'four-plus-other':
        categories, transformation_metadata = four_plus_other(source_categories, config.selected_category_ids or [])
        if config.selection_rule:
            transformation_metadata['selectionRule'] = config.selection_rule
    else:
        categories = source_categories
        transformation_metadata = {'type': 'natural-five'}
    transformation_metadata['sourceVariables'] = {variable.id: variable.dcid for variable in config.variables}
    candidate = CandidatePuzzle(
        source_name=source.source_name,
        source_dataset_id=source.source_dataset_id,
        source_url=source.source_url,
        topic=config.topic,
        title=config.title,
        context=config.context,
        geography=source.geography,
        time_period=source.time_period,
        unit=source.unit,
        population_universe=source.population_universe,
        transformation_type=config.transformation_type,
        categories=categories,
        transformation_metadata=transformation_metadata,
        source_metadata={**source.source_metadata, 'facetId': source.facet_id, 'denominator': config.denominator},
    )
    validation = validate_candidate_against_source(candidate, source)
    if not validation.valid:
        raise ValueError('; '.join(validation.issues))
    source.source_metadata['denominator'] = config.denominator
    with connect() as connection:
        return persist_candidate(candidate, source, validation, connection)


def main() -> None:
    parser = argparse.ArgumentParser(description='Ingest one Data Commons candidate')
    parser.add_argument('config', type=Path, help='JSON file specifying one five-category dataset')
    args = parser.parse_args()
    config = IngestConfig.model_validate_json(args.config.read_text(encoding='utf-8'))
    try:
        print(f'Created candidate {ingest(config)}')
    except (RuntimeError, ValueError) as error:
        print(f'Ingestion skipped: {error}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
