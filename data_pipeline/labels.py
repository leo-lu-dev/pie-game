"""Turn verbose statistical labels into concise game-facing labels."""

from __future__ import annotations

import re


_RACE_LABELS = (
    "american indian and alaska native",
    "native hawaiian and other pacific islander",
    "black or african american",
    "hispanic or latino",
    "white",
    "asian",
    "black",
)


def _title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split())


def concise_category_label(label: str, dcid: str | None = None) -> str:
    """Remove statistical-table boilerplate without changing category meaning."""
    original = re.sub(r"\s+", " ", label).strip()
    lowered = original.lower()

    # Race labels are usually wrapped in repeated universe/measurement text.
    # Keep an important exclusion such as "not Hispanic or Latino".
    for race_label in _RACE_LABELS:
        if race_label == "hispanic or latino" and "not hispanic or latino" in lowered:
            continue
        if race_label in lowered:
            concise = _title_case(race_label)
            if "not hispanic or latino" in lowered and race_label != "hispanic or latino":
                concise += " (not Hispanic or Latino)"
            return concise

    # Age-band labels are especially common in Census table names.
    age_range = re.search(r"years?\s+(\d+)\s+to\s+(\d+)", lowered)
    if age_range:
        return f"{age_range.group(1)}–{age_range.group(2)}"
    age_upper = re.search(r"years?\s+(?:up to|upto)\s+(\d+)", lowered)
    if age_upper:
        return f"{age_upper.group(1)} or younger"
    age_lower = re.search(r"years?\s+(\d+)\s+or\s+more", lowered)
    if age_lower:
        return f"{age_lower.group(1)}+"
    under_age = re.search(r"under\s+(\d+)\s+years?", lowered)
    if under_age:
        return f"Under {under_age.group(1)}"

    concise = original
    concise = re.sub(r"^population\s*:\s*", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r"^population\s+(?:of|with)\s+", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r"^count\s+of\s+", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r"^number\s+of\s+", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r"\byears?\s+(\d+)\s+onwards\s*,?\s*", r"\1+ ", concise, flags=re.IGNORECASE)
    concise = re.sub(r"\b(non[- ]?institutionalized|civilian)\b", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r"\b(monoracial/multiracial|alone)\b", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r",?\s*occupied housing units?\b", "", concise, flags=re.IGNORECASE)
    concise = re.sub(r"\bassociates degree\b", "Associate's degree", concise, flags=re.IGNORECASE)
    concise = re.sub(r"\s*,\s*", ", ", concise)
    concise = re.sub(r"\s+", " ", concise).strip(" ,")

    # If cleanup did not improve the label, retain the source wording.
    return concise or original
