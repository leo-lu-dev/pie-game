"""Curated public-source recipes used by automated candidate discovery.

These are provider-neutral instructions, not user-created candidate configs.
The adapters fetch the current data and metadata at run time, while this small
catalog records the semantic choices that cannot be safely inferred from an
API response alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ExternalRecipe:
    key: str
    provider: Literal["owid", "eurostat"]
    title: str
    topic: str
    context: str
    denominator: str
    measure: str
    unit: str | None
    population_universe: str
    geography: str
    adapter_args: dict[str, Any] = field(default_factory=dict)


RECIPES: tuple[ExternalRecipe, ...] = (
    ExternalRecipe(
        key="owid-energy-consumption-by-source-world",
        provider="owid",
        title="How is global energy consumption divided by source?",
        topic="Energy consumption by source",
        context="How is global energy consumption divided across energy sources?",
        denominator="global energy consumption",
        measure="Energy consumption by source",
        unit="terawatt-hours",
        population_universe="global energy consumption",
        geography="World",
        adapter_args={"slug": "energy-consumption-by-source-and-country", "entity": "World"},
    ),
    ExternalRecipe(
        key="owid-electricity-production-by-source-world",
        provider="owid",
        title="How is global electricity production divided by source?",
        topic="Electricity production by source",
        context="How is global electricity production divided across energy sources?",
        denominator="global electricity production",
        measure="Electricity production by source",
        unit="terawatt-hours",
        population_universe="global electricity production",
        geography="World",
        adapter_args={"slug": "electricity-prod-source-stacked", "entity": "World"},
    ),
    ExternalRecipe(
        key="owid-plastic-waste-by-sector-world",
        provider="owid",
        title="How is global plastic waste divided by sector?",
        topic="Plastic waste by sector",
        context="How is global plastic waste divided across the sectors that generate it?",
        denominator="global plastic waste",
        measure="Plastic waste by sector",
        unit="tonnes",
        population_universe="global plastic waste",
        geography="World",
        adapter_args={"slug": "plastic-waste-by-sector", "entity": "World"},
    ),
    ExternalRecipe(
        key="eurostat-population-age-groups-eu27",
        provider="eurostat",
        title="How is the EU population divided by age?",
        topic="Population by age group",
        context="How is the population of the European Union divided across age groups?",
        denominator="population of the European Union",
        measure="Population by age group",
        unit="people",
        population_universe="population of the European Union",
        geography="European Union (27 countries)",
        adapter_args={
            "dataset_code": "demo_pjangroup",
            "category_dimension": "age",
            "filters": {"freq": "A", "sex": "T", "geo": "EU27_2020", "lastTimePeriod": "1"},
            # Eurostat publishes overlapping totals and open-ended groups in
            # this cube. These exclusions leave a mutually exclusive partition:
            # under 5, five-year bands through 70-74, and 75+.
            "exclude_category_ids": {"TOTAL", "Y75-79", "Y_GE80", "Y_GE85", "UNK"},
            "category_groups": {
                "under-20": ["Y_LT5", "Y5-9", "Y10-14", "Y15-19"],
                "20-39": ["Y20-24", "Y25-29", "Y30-34", "Y35-39"],
                "40-59": ["Y40-44", "Y45-49", "Y50-54", "Y55-59"],
                "60-74": ["Y60-64", "Y65-69", "Y70-74"],
                "75-plus": ["Y_GE75"],
            },
            "category_group_labels": {
                "under-20": "Under 20",
                "20-39": "20 to 39",
                "40-59": "40 to 59",
                "60-74": "60 to 74",
                "75-plus": "75 and over",
            },
        },
    ),
)


def recipes(provider: str = "all") -> list[ExternalRecipe]:
    normalized = provider.strip().lower()
    if normalized not in {"all", "owid", "eurostat"}:
        raise ValueError("external provider must be all, owid, or eurostat")
    return [recipe for recipe in RECIPES if normalized == "all" or recipe.provider == normalized]
