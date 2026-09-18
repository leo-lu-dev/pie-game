"""Shared deterministic rules for turning source values into five categories."""

from __future__ import annotations

import re
from typing import Any


def candidate_values(source_values: list[Any], selected_category_ids: list[str] | None) -> list[float]:
    if not selected_category_ids:
        return [float(value.value) for value in source_values]
    selected = set(selected_category_ids)
    return [
        *(float(value.value) for value in source_values if value.category_id in selected),
        sum(float(value.value) for value in source_values if value.category_id not in selected),
    ]


def age_start(text: str) -> int | None:
    lowered = text.lower()
    if re.search(r"\b(?:under|upto|up to)\s*\d+", lowered):
        return 0
    match = re.search(r"\b(\d+)\s*(?:to|-)\s*\d+\s*years?\b", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"\byears?\s*(\d+)\s*(?:to|-)\s*\d+\b", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d+)\s*(?:or more|plus)\s*years?\b", lowered)
    if match is None:
        match = re.search(r"\b(\d+)\s*years?\s*(?:or more|plus)\b", lowered)
    return int(match.group(1)) if match else None


def education_start(text: str) -> int | None:
    lowered = text.lower()
    terms = (
        ("less than high school", 0),
        ("no high school", 0),
        ("high school", 1),
        ("some college", 2),
        ("associate", 3),
        ("bachelor", 4),
        ("master", 5),
        ("professional", 6),
        ("doctorate", 7),
    )
    for term, order in terms:
        if term in lowered:
            return order
    return None


def household_size_start(text: str) -> int | None:
    lowered = text.lower()
    match = re.search(r"\b(\d+)\s*(?:person|people)\b", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"(?:household size|householdsize)[^0-9]{0,10}(\d+)", lowered)
    return int(match.group(1)) if match else None


def ordered_selection(source_values: list[Any]) -> list[str] | None:
    """Select the first four categories for a recognizable ordered group."""
    parsers = (age_start, education_start, household_size_start)
    for parser in parsers:
        ordered: list[tuple[int, int, str]] = []
        for index, value in enumerate(source_values):
            text = f"{value.category_label} {value.category_id}"
            start = parser(text)
            if start is None:
                break
            ordered.append((start, index, value.category_id))
        if len(ordered) == len(source_values) and len({start for start, _, _ in ordered}) == len(ordered):
            return [category_id for _, _, category_id in sorted(ordered)[:4]]
    return None


def largest_share(values: list[float]) -> float:
    total = sum(values)
    return max(values) / total * 100 if values and total > 0 else 100


def largest_share_limit() -> float:
    import os

    try:
        limit = float(os.getenv("DISCOVERY_MAX_LARGEST_SHARE_PERCENT", "45"))
    except ValueError as error:
        raise RuntimeError("DISCOVERY_MAX_LARGEST_SHARE_PERCENT must be a number between 1 and 100") from error
    if not 0 < limit <= 100:
        raise RuntimeError("DISCOVERY_MAX_LARGEST_SHARE_PERCENT must be a number between 1 and 100")
    return limit
