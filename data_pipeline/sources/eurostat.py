"""Adapter for Eurostat's JSON-stat 2 dissemination API."""

from __future__ import annotations

from typing import Any

import httpx

from ..models.source import SourceDataset, SourceValue


class EurostatError(RuntimeError):
    """Raised when a Eurostat cube cannot be reduced to one value per category."""


class EurostatAdapter:
    """Fetch a filtered Eurostat cube and normalize one dimension as categories."""

    def __init__(
        self,
        *,
        dataset_code: str,
        category_dimension: str,
        filters: dict[str, str] | None = None,
        exclude_category_ids: set[str] | None = None,
        category_groups: dict[str, list[str] | tuple[str, ...]] | None = None,
        category_group_labels: dict[str, str] | None = None,
        dataset_id: str | None = None,
        measure: str = "Eurostat statistic",
        unit: str | None = None,
        geography: str | None = None,
        population_universe: str | None = None,
        base_url: str = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data",
        client: httpx.Client | None = None,
    ) -> None:
        if not dataset_code.strip() or not category_dimension.strip():
            raise ValueError("Eurostat dataset_code and category_dimension are required")
        self.dataset_code = dataset_code.strip()
        self.category_dimension = category_dimension.strip()
        self.filters = filters or {}
        self.exclude_category_ids = exclude_category_ids or set()
        self.category_groups = category_groups
        self.category_group_labels = category_group_labels or {}
        self.dataset_id = dataset_id or f"eurostat-{self.dataset_code}"
        self.measure = measure
        self.unit = unit
        self.geography = geography
        self.population_universe = population_universe
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=45.0)
        self._owns_client = client is None

    def __enter__(self) -> EurostatAdapter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch(self) -> SourceDataset:
        url = f"{self.base_url}/{self.dataset_code}"
        params = {"format": "JSON", "lang": "en", **self.filters}
        response = self.client.get(url, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise EurostatError(f"Eurostat request failed with HTTP {response.status_code}") from error
        try:
            payload = response.json()
        except ValueError as error:
            raise EurostatError("Eurostat returned invalid JSON") from error
        values, labels, time_period = self._parse_values(payload)
        if len(values) < 5:
            raise EurostatError("Eurostat category dimension has fewer than five values")
        source_metadata = {
            "provider": "eurostat",
            "datasetCode": self.dataset_code,
            "categoryDimension": self.category_dimension,
            "filters": self.filters,
            "excludedCategoryIds": sorted(self.exclude_category_ids),
            "categoryGroups": self.category_groups,
            "dimensions": payload.get("id", []),
            "dimensionSizes": payload.get("size", []),
            "categoryLabels": labels,
            "dedupeKey": f"eurostat:{self.dataset_code}:{self.category_dimension}:{self.filters}",
            "requestUrl": str(response.url),
        }
        return SourceDataset(
            source_name="Eurostat",
            source_dataset_id=self.dataset_id,
            source_url=str(response.url),
            measure=self.measure,
            unit=self.unit or self._unit(payload),
            geography=self.geography or self.filters.get("geo"),
            time_period=time_period,
            population_universe=self.population_universe,
            values=[SourceValue(category_id=category_id, category_label=labels[category_id], value=value) for category_id, value in values.items()],
            source_metadata=source_metadata,
            raw_payload=payload,
        )

    def _parse_values(self, payload: dict[str, Any]) -> tuple[dict[str, float], dict[str, str], str | None]:
        dimensions = payload.get("id")
        sizes = payload.get("size")
        dimension_data = payload.get("dimension")
        raw_values = payload.get("value")
        if not isinstance(dimensions, list) or not isinstance(sizes, list) or not isinstance(dimension_data, dict):
            raise EurostatError("Eurostat response is missing JSON-stat dimensions")
        if self.category_dimension not in dimensions:
            raise EurostatError(f"Eurostat response has no category dimension {self.category_dimension}")
        if len(dimensions) != len(sizes):
            raise EurostatError("Eurostat response dimensions and sizes do not align")

        category_index = dimensions.index(self.category_dimension)
        category_categories = dimension_data[self.category_dimension].get("category", {})
        ordered_category_ids = [
            category_id
            for category_id in self._ordered_category_ids(category_categories)
            if category_id not in self.exclude_category_ids
        ]
        if not ordered_category_ids:
            raise EurostatError("Eurostat category dimension is empty")

        positions: list[dict[str, int]] = []
        for dimension, size in zip(dimensions, sizes):
            category = dimension_data.get(dimension, {}).get("category", {})
            ids = self._ordered_category_ids(category)
            if not ids or len(ids) != int(size):
                raise EurostatError(f"Eurostat dimension {dimension} has inconsistent category indexes")
            positions.append({value: index for index, value in enumerate(ids)})
            if dimension != self.category_dimension and int(size) != 1:
                raise EurostatError(f"Eurostat filter must reduce dimension {dimension} to one value")

        def value_at(coordinates: list[int]) -> float:
            offset = 0
            for index, coordinate in enumerate(coordinates):
                stride = 1
                for later_size in sizes[index + 1:]:
                    stride *= int(later_size)
                offset += coordinate * stride
            if isinstance(raw_values, list):
                raw_value = raw_values[offset] if offset < len(raw_values) else None
            elif isinstance(raw_values, dict):
                raw_value = raw_values.get(str(offset))
            else:
                raw_value = None
            if raw_value is None:
                raise EurostatError("Eurostat returned a missing value for a selected category")
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as error:
                raise EurostatError("Eurostat returned a non-numeric value") from error
            if value < 0:
                raise EurostatError("Eurostat returned a negative value")
            return value

        values: dict[str, float] = {}
        for category_id in ordered_category_ids:
            coordinates = [0] * len(dimensions)
            coordinates[category_index] = positions[category_index][category_id]
            values[category_id] = value_at(coordinates)
        labels = {
            category_id: str(category_categories.get("label", {}).get(category_id, category_id))
            for category_id in ordered_category_ids
        }
        if self.category_groups:
            grouped_values: dict[str, float] = {}
            grouped_labels: dict[str, str] = {}
            for group_id, source_ids in self.category_groups.items():
                missing = [source_id for source_id in source_ids if source_id not in values]
                if missing:
                    raise EurostatError(f"Eurostat category group {group_id} references missing categories: {missing}")
                grouped_values[group_id] = sum(values[source_id] for source_id in source_ids)
                grouped_labels[group_id] = self.category_group_labels.get(group_id, group_id)
            if set(self.category_groups) != set(grouped_values):
                raise EurostatError("Eurostat category groups could not be normalized")
            values, labels = grouped_values, grouped_labels
        time_period = self.filters.get("time")
        if time_period is None and "time" in dimensions:
            time_categories = dimension_data.get("time", {}).get("category", {})
            time_ids = self._ordered_category_ids(time_categories)
            if len(time_ids) == 1:
                time_period = time_ids[0]
        return values, labels, time_period

    @staticmethod
    def _ordered_category_ids(category: dict[str, Any]) -> list[str]:
        index = category.get("index", {}) if isinstance(category, dict) else {}
        if isinstance(index, list):
            return [str(value) for value in index]
        if isinstance(index, dict):
            return [str(value) for value, _ in sorted(index.items(), key=lambda item: item[1])]
        return [str(value) for value in category.get("label", {})] if isinstance(category, dict) else []

    @staticmethod
    def _unit(payload: dict[str, Any]) -> str | None:
        dimension = payload.get("dimension", {}).get("unit", {})
        category = dimension.get("category", {}) if isinstance(dimension, dict) else {}
        labels = category.get("label", {}) if isinstance(category, dict) else {}
        return next(iter(labels.values()), None) if len(labels) == 1 else None
