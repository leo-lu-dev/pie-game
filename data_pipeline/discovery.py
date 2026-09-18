"""Discover API-backed five-category candidate recipes from Data Commons."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .selection import (
    candidate_values as _candidate_values,
    largest_share as _largest_share,
    largest_share_limit as _largest_share_limit,
    ordered_selection as _ordered_selection,
)
from .sources.datacommons import DataCommonsAdapter, DataCommonsError


COUNT_FAMILIES = {
    "Count_Person": ("people", "people"),
    "Count_Household": ("households", "households"),
    "Count_HousingUnit": ("housing units", "housing units"),
}

RACE_TERMS = {
    "race", "racial", "ethnic", "ethnicity", "hispanic", "latino", "latina",
    "white", "black", "african", "asian", "indian", "native", "pacific islander",
}

SENSITIVE_CROSS_TAB_TERMS = {
    "crime", "criminal", "arrest", "incarceration", "prison", "jail", "offense",
    "offender", "victim", "poverty", "poor", "income", "earnings", "wealth",
    "finance", "financial", "debt", "unemployment", "jobless", "homeless", "welfare",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:50]


def _resolve_topics(client: httpx.Client, api_key: str, terms: list[str]) -> list[dict[str, Any]]:
    topics: list[dict[str, Any]] = []
    for index, term in enumerate(terms, start=1):
        print(f"[discovery] Searching Data Commons ({index}/{len(terms)}): {term}", flush=True)
        response = client.post(
            "https://api.datacommons.org/v2/resolve",
            headers={"X-API-Key": api_key},
            json={"nodes": [term], "resolver": "indicator"},
        )
        response.raise_for_status()
        entities = response.json().get("entities", [])
        candidates = entities[0].get("candidates", []) if entities else []
        topics.extend(candidate for candidate in candidates if "Topic" in candidate.get("typeOf", []))
    return topics


def topic_search_terms() -> list[str]:
    """Enumerate Data Commons topic names for long-lived discovery."""
    load_dotenv(".env.local")
    api_key = os.getenv("DATACOMMONS_API_KEY")
    if not api_key:
        raise RuntimeError("Set DATACOMMONS_API_KEY before topic discovery")
    terms: list[str] = []
    next_token: str | None = None
    with httpx.Client(timeout=30.0) as client:
        while True:
            payload: dict[str, Any] = {"nodes": ["Topic"], "property": "<-typeOf"}
            if next_token:
                payload["nextToken"] = next_token
            response = client.post(
                "https://api.datacommons.org/v2/node",
                headers={"X-API-Key": api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json().get("data", {}).get("Topic", {})
            nodes = data.get("arcs", {}).get("typeOf", {}).get("nodes", [])
            terms.extend(
                str(node["name"]).strip()
                for node in nodes
                if node.get("name") and len(str(node["name"]).strip()) >= 4
            )
            next_token = response.json().get("nextToken")
            if not next_token:
                break
    return list(dict.fromkeys(terms))


def _entity_label(entity_dcid: str) -> str:
    labels = {
        "country/USA": "the United States",
        "country/CAN": "Canada",
        "country/MEX": "Mexico",
        "country/GBR": "the United Kingdom",
        "country/AUS": "Australia",
        "country/IND": "India",
        "geoId/06": "California",
        "geoId/36": "New York",
        "geoId/48": "Texas",
        "geoId/12": "Florida",
        "geoId/17": "Illinois",
    }
    return labels.get(entity_dcid, entity_dcid)


def _count_family(dcid: str) -> tuple[str, str] | None:
    for prefix, profile in COUNT_FAMILIES.items():
        if dcid == prefix or dcid.startswith(f"{prefix}_"):
            return profile
    return None


def _configured_entities() -> list[str]:
    raw = os.getenv("DATACOMMONS_ENTITY_DCIDS", "country/USA")
    return [value.strip() for value in raw.split(",") if value.strip()]


def _topic_terms(topic: dict[str, Any], children: list[dict[str, Any]]) -> set[str]:
    text = " ".join([
        str(topic.get("name", "")),
        str(topic.get("dcid", "")),
        *(str(value) for child in children for value in (child.get("name", ""), child.get("dcid", ""))),
    ]).lower()
    return {
        term for term in RACE_TERMS | SENSITIVE_CROSS_TAB_TERMS
        if term in text
    }


def _sensitive_demographic_cross_tab(topic: dict[str, Any], children: list[dict[str, Any]]) -> bool:
    terms = _topic_terms(topic, children)
    return bool(terms & RACE_TERMS) and bool(terms & SENSITIVE_CROSS_TAB_TERMS)


def _race_related(topic: dict[str, Any], children: list[dict[str, Any]]) -> bool:
    return bool(_topic_terms(topic, children) & RACE_TERMS)


def _topic_sort_key(topic: dict[str, Any]) -> tuple[int, int]:
    children = [child for child in topic.get("children", []) if "StatisticalVariable" in child.get("typeOf", [])]
    # Non-race topics come first; within each group, native five-variable
    # topics come before larger groups that require an Other bucket.
    return (1 if _race_related(topic, children) else 0, 0 if len(children) == 5 else 1)


def discover_configs(count: int, output_dir: Path, entity_dcids: list[str] | None = None, allow_fewer: bool = False, search_terms: list[str] | None = None, seen: set[tuple[str, ...]] | None = None) -> list[Path]:
    """Find usable five-variable topic groups and write ingestion configs."""
    load_dotenv(".env.local")
    api_key = os.getenv("DATACOMMONS_API_KEY")
    if not api_key:
        raise RuntimeError("Set DATACOMMONS_API_KEY before candidate discovery")

    entities = entity_dcids or _configured_entities()
    terms = [
        "population by race",
        "age distribution",
        "employment status",
        "education attainment",
        "marital status",
        "household composition",
        "health conditions",
        "college education",
        "preventive health",
        "health behavior",
        "malnutrition",
        "fertility",
        "household size",
        "internet access",
        "housing tenure",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    seen_groups = seen if seen is not None else set()
    rejected = {
        "fewer-than-five": 0,
        "sensitive-demographic-cross-tab": 0,
        "duplicate": 0,
        "unsupported-or-mixed-count-family": 0,
        "observation-unavailable": 0,
        "dominant-largest-slice": 0,
    }
    largest_share_limit = _largest_share_limit()
    if search_terms is not None:
        terms = search_terms

    curated_topics = [
        {
            "dcid": "curated/MaritalStatus",
            "name": "Marital status",
            "children": [
                {"dcid": "Count_Person_NeverMarried", "typeOf": ["StatisticalVariable"], "name": "Never married"},
                {"dcid": "Count_Person_MarriedAndNotSeparated", "typeOf": ["StatisticalVariable"], "name": "Married, not separated"},
                {"dcid": "Count_Person_Separated", "typeOf": ["StatisticalVariable"], "name": "Separated"},
                {"dcid": "Count_Person_Divorced", "typeOf": ["StatisticalVariable"], "name": "Divorced"},
                {"dcid": "Count_Person_Widowed", "typeOf": ["StatisticalVariable"], "name": "Widowed"},
            ],
        },
        {
            "dcid": "curated/AgeDistribution",
            "name": "Broad age distribution",
            "children": [
                {"dcid": "Count_Person_Under18Years", "typeOf": ["StatisticalVariable"], "name": "Under 18 years"},
                {"dcid": "Count_Person_18To24Years", "typeOf": ["StatisticalVariable"], "name": "18 to 24 years"},
                {"dcid": "Count_Person_25To44Years", "typeOf": ["StatisticalVariable"], "name": "25 to 44 years"},
                {"dcid": "Count_Person_45To64Years", "typeOf": ["StatisticalVariable"], "name": "45 to 64 years"},
                {"dcid": "Count_Person_65OrMoreYears", "typeOf": ["StatisticalVariable"], "name": "65 years and over"},
            ],
        },
    ]

    with httpx.Client(timeout=30.0) as client:
        topics = curated_topics + _resolve_topics(client, api_key, terms)
        for entity_dcid in entities:
            geography = _entity_label(entity_dcid)
            # Prefer native five-variable topics. Larger groups are a fallback
            # and become four named categories plus Other.
            ordered_topics = sorted(
                topics,
                key=_topic_sort_key,
            )
            for topic in ordered_topics:
                children = [child for child in topic.get("children", []) if "StatisticalVariable" in child.get("typeOf", [])]
                if _sensitive_demographic_cross_tab(topic, children):
                    rejected["sensitive-demographic-cross-tab"] += 1
                    continue
                if len(children) < 5:
                    rejected["fewer-than-five"] += 1
                    continue
                print(f"[discovery] Testing {geography}: {topic.get('name', topic.get('dcid', 'unknown'))} ({len(children)} variables)", flush=True)
                selected = children
                dcids = tuple(child["dcid"] for child in selected)
                group_key = (entity_dcid, *sorted(dcids))
                if group_key in seen_groups:
                    rejected["duplicate"] += 1
                    continue
                seen_groups.add(group_key)
                profiles = {_count_family(dcid) for dcid in dcids}
                if len(profiles) != 1 or None in profiles:
                    rejected["unsupported-or-mixed-count-family"] += 1
                    continue
                unit, universe_noun = next(iter(profiles))
                variables = {f"category-{index + 1}": dcid for index, dcid in enumerate(dcids)}
                labels = {f"category-{index + 1}": child.get("name", dcid) for index, (dcid, child) in enumerate(zip(dcids, selected))}
                try:
                    with DataCommonsAdapter(
                        entity_dcid=entity_dcid,
                        variables=variables,
                        labels=labels,
                        dataset_id=f"discovered-{topic.get('dcid', 'topic')}",
                        measure="count",
                        unit=unit,
                        geography=geography,
                        population_universe=f"{universe_noun} in {geography}",
                        date="LATEST",
                        api_key=api_key,
                        client=client,
                    ) as adapter:
                        source = adapter.fetch()
                except (DataCommonsError, httpx.HTTPError, ValueError):
                    rejected["observation-unavailable"] += 1
                    continue
                transformation_type = "natural-five"
                selected_category_ids: list[str] | None = None
                selection_rule: str | None = None
                if len(source.values) > 5:
                    transformation_type = "four-plus-other"
                    selected_category_ids = _ordered_selection(source.values)
                    if selected_category_ids is None:
                        selection_rule = "largest-values"
                        selected_category_ids = [value.category_id for value in sorted(
                            source.values,
                            key=lambda value: (-value.value, value.category_id),
                        )[:4]]
                    else:
                        selection_rule = "ordered-lowest-first"
                candidate_values = _candidate_values(source.values, selected_category_ids)
                largest_share = _largest_share(candidate_values)
                if largest_share >= largest_share_limit:
                    rejected["dominant-largest-slice"] += 1
                    continue
                topic_name = topic.get("name", topic.get("dcid", "Data Commons topic"))
                config = {
                    "dataset_id": f"discovered-{_slug(topic.get('dcid', topic_name))}-{len(created) + 1}",
                    "entity_dcid": entity_dcid,
                    "geography": geography,
                    "topic": topic_name,
                    "title": f"How is {topic_name.lower()} distributed in {geography}?",
                    "context": f"How is {universe_noun} divided across five categories for {topic_name.lower()} in {geography}?",
                    "denominator": f"{universe_noun} in {geography}",
                    "measure": "count",
                    "unit": unit,
                    "population_universe": f"{universe_noun} in {geography}",
                    "facet_id": source.facet_id,
                    "date": "LATEST",
                    "transformation_type": transformation_type,
                    "variables": [
                        {"id": key, "label": labels[key], "dcid": variables[key]}
                        for key in variables
                    ],
                }
                if selected_category_ids is not None:
                    config["selected_category_ids"] = selected_category_ids
                    config["selection_rule"] = selection_rule
                path = output_dir / f"{len(created) + 1:02d}-{_slug(topic_name)}.json"
                path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
                created.append(path)
                print(
                    f"[discovery] Accepted candidate {len(created)}/{count}: {path.name} "
                    f"(largest slice {largest_share:.1f}%)",
                    flush=True,
                )
                if len(created) >= count:
                    break
            if len(created) >= count:
                break

    if len(created) < count and not allow_fewer:
        raise RuntimeError(f"Data Commons discovery found only {len(created)} usable candidate group(s); requested {count}")
    print(f"[discovery] Complete: found {len(created)} candidate recipe(s)", flush=True)
    print(
        "[discovery] Rejections: "
        + ", ".join(f"{reason}={amount}" for reason, amount in rejected.items()),
        flush=True,
    )
    return created
