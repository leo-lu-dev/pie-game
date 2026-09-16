from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models.candidate import CandidateCategory


def four_plus_other(
    source: Iterable[CandidateCategory],
    selected_ids: list[str],
    other_id: str = "other",
    other_label: str = "Other",
) -> tuple[list[CandidateCategory], dict[str, Any]]:
    categories = list(source)
    selected = {category.id for category in categories if category.id in selected_ids}
    if len(selected) != 4 or len(selected_ids) != 4:
        raise ValueError("four-plus-other requires exactly four selected categories")
    remaining = [category for category in categories if category.id not in selected]
    if not remaining:
        raise ValueError("four-plus-other requires at least one category for Other")
    if other_id in selected:
        raise ValueError("Other ID cannot overlap a selected category")
    result = [category for category in categories if category.id in selected_ids]
    result.append(CandidateCategory(id=other_id, label=other_label, raw_value=sum(c.raw_value for c in remaining)))
    metadata = {"type": "four-plus-other", "selected": selected_ids, "otherIncludes": [c.id for c in remaining]}
    return result, metadata


def meaningful_subset(source: Iterable[CandidateCategory], selected_ids: list[str], selection_rule: str) -> tuple[list[CandidateCategory], dict[str, Any]]:
    categories = list(source)
    if len(selected_ids) != 5 or len(set(selected_ids)) != 5:
        raise ValueError("meaningful subset requires exactly five unique selected IDs")
    by_id = {category.id: category for category in categories}
    if any(category_id not in by_id for category_id in selected_ids):
        raise ValueError("subset contains an unknown category ID")
    result = [by_id[category_id] for category_id in selected_ids]
    return result, {"type": "meaningful-subset", "selectionRule": selection_rule, "selected": selected_ids}

