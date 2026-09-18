from __future__ import annotations

from typing import Any

import httpx

from ..models.source import SourceDataset, SourceValue


class DataCommonsError(RuntimeError):
    """Raised when Data Commons cannot provide a consistent dataset."""


class DataCommonsAdapter:
    """Fetch one explicitly configured Data Commons observation dataset.

    The caller supplies five statistical variables that describe one comparable
    universe. The adapter does not discover or invent variables.
    """

    def __init__(
        self,
        *,
        entity_dcid: str,
        variables: dict[str, str],
        labels: dict[str, str] | None = None,
        dataset_id: str,
        measure: str,
        unit: str | None = None,
        geography: str | None = None,
        population_universe: str | None = None,
        date: str = "LATEST",
        facet_id: str | None = None,
        api_key: str | None = None,
        base_url: str = "https://api.datacommons.org/v2",
        client: httpx.Client | None = None,
    ) -> None:
        if len(variables) != 5:
            raise ValueError("Data Commons adapter requires exactly five variables")
        self.entity_dcid = entity_dcid
        self.variables = variables
        self.labels = labels or {category_id: category_id for category_id in variables}
        if set(self.labels) != set(variables):
            raise ValueError("labels must match the five variable category IDs")
        self.dataset_id = dataset_id
        self.measure = measure
        self.unit = unit
        self.geography = geography
        self.population_universe = population_universe
        self.date = date
        self.facet_id = facet_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None

    def __enter__(self) -> DataCommonsAdapter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch(self) -> SourceDataset:
        payload = {
            "date": self.date,
            "variable": {"dcids": list(self.variables)},
            "entity": {"dcids": [self.entity_dcid]},
            "select": ["date", "entity", "variable", "value", "facet"],
        }
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        response = self.client.post(f"{self.base_url}/observation", json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise DataCommonsError(f"Data Commons request failed with HTTP {response.status_code}") from error
        raw = response.json()
        values, facet_id, observed_date, facets = self._parse_observations(raw)
        facet_metadata = facets.get(facet_id, {})
        return SourceDataset(
            source_name="Data Commons",
            source_dataset_id=self.dataset_id,
            source_url=facet_metadata.get("provenanceUrl"),
            measure=self.measure,
            unit=self.unit or facet_metadata.get("unit"),
            geography=self.geography,
            time_period=observed_date,
            population_universe=self.population_universe,
            facet_id=facet_id,
            values=values,
            source_metadata={
                "entityDcid": self.entity_dcid,
                "dateRequested": self.date,
                "variables": self.variables,
                "labels": self.labels,
                "observedDate": observed_date,
                "facetId": facet_id,
                "requestEndpoint": f"{self.base_url}/observation",
                "facet": facet_metadata,
                "facets": facets,
                "request": payload,
            },
            raw_payload=raw,
        )

    def _parse_observations(self, raw: dict[str, Any]) -> tuple[list[SourceValue], str, str, dict[str, Any]]:
        by_variable = raw.get("byVariable", {})
        facets = raw.get("facets", {})
        if not isinstance(by_variable, dict) or not isinstance(facets, dict):
            raise DataCommonsError("Data Commons returned an invalid observation response")

        observation_sets: list[set[tuple[str, str]]] = []
        variable_entries: list[tuple[str, dict[str, Any]]] = []
        for variable_dcid, entry in self.variables.items():
            variable_result = by_variable.get(entry)
            entity_result = variable_result.get("byEntity", {}).get(self.entity_dcid) if isinstance(variable_result, dict) else None
            ordered_facets = entity_result.get("orderedFacets", []) if isinstance(entity_result, dict) else []
            available = {
                (str(facet["facetId"]), str(observation["date"]))
                for facet in ordered_facets if facet.get("facetId") is not None
                for observation in facet.get("observations", []) if observation.get("date") is not None
            }
            if not available:
                raise DataCommonsError(f"No dated observations found for variable {entry}")
            observation_sets.append(available)
            variable_entries.append((variable_dcid, entity_result))

        common = set.intersection(*observation_sets)
        if self.facet_id:
            common = {(facet, date) for facet, date in common if facet == self.facet_id}
        if not common:
            raise DataCommonsError("The five variables do not share a common facet and date")
        facet_ids = {facet for facet, _ in common}
        if len(facet_ids) != 1:
            raise DataCommonsError("Multiple common facets found; specify facet_id explicitly")
        facet_id = facet_ids.pop()
        observed_date = max(date for _, date in common)

        values: list[SourceValue] = []
        for category_id, entity_result in variable_entries:
            observations = next(
                (facet.get("observations", []) for facet in entity_result.get("orderedFacets", []) if str(facet.get("facetId")) == facet_id),
                [],
            )
            if not observations:
                raise DataCommonsError(f"No observation found for variable {self.variables[category_id]} in facet {facet_id}")
            latest = next((observation for observation in observations if str(observation.get("date")) == observed_date), None)
            if latest is None:
                raise DataCommonsError(f"No observation at {observed_date} for variable {self.variables[category_id]}")
            try:
                value = float(latest["value"])
            except (KeyError, TypeError, ValueError) as error:
                raise DataCommonsError(f"Invalid observation for variable {self.variables[category_id]}") from error
            values.append(SourceValue(category_id=category_id, category_label=self.labels[category_id], value=value))
        return values, facet_id, observed_date, facets
