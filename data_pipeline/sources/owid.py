"""Adapter for public Our World in Data Grapher charts."""

from __future__ import annotations

import csv
import io
from typing import Any

import httpx

from ..models.source import SourceDataset, SourceValue


class OwidError(RuntimeError):
    """Raised when an OWID chart cannot be normalized into one observation."""


class OwidAdapter:
    """Fetch one OWID Grapher chart for one entity and one time period.

    The chart slug and optional columns are supplied by the provider catalog,
    not by the user. This keeps discovery automated while making the selected
    measures explicit and auditable.
    """

    def __init__(
        self,
        *,
        slug: str,
        entity: str = "World",
        columns: dict[str, str] | None = None,
        dataset_id: str | None = None,
        measure: str | None = None,
        unit: str | None = None,
        geography: str | None = None,
        population_universe: str | None = None,
        year: str | int = "latest",
        base_url: str = "https://ourworldindata.org/grapher",
        client: httpx.Client | None = None,
    ) -> None:
        if not slug.strip():
            raise ValueError("OWID chart slug is required")
        self.slug = slug.strip()
        self.entity = entity
        self.columns = columns
        self.dataset_id = dataset_id or f"owid-grapher-{self.slug}"
        self.measure = measure
        self.unit = unit
        self.geography = geography or entity
        self.population_universe = population_universe
        self.year = year
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=30.0, follow_redirects=True)
        self._owns_client = client is None

    def __enter__(self) -> OwidAdapter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def fetch(self) -> SourceDataset:
        csv_url = f"{self.base_url}/{self.slug}.csv"
        metadata_url = f"{self.base_url}/{self.slug}.metadata.json"
        csv_response = self.client.get(csv_url)
        try:
            csv_response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise OwidError(f"OWID chart request failed with HTTP {csv_response.status_code}") from error
        metadata_response = self.client.get(metadata_url)
        try:
            metadata_response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise OwidError(f"OWID metadata request failed with HTTP {metadata_response.status_code}") from error

        try:
            metadata = metadata_response.json()
        except ValueError as error:
            raise OwidError("OWID returned invalid chart metadata JSON") from error
        rows = list(csv.DictReader(io.StringIO(csv_response.text)))
        row, time_period = self._select_row(rows)
        selected_columns = self.columns or self._numeric_columns(rows, row)
        if len(selected_columns) < 5:
            raise OwidError("OWID chart has fewer than five usable data columns")

        values: list[SourceValue] = []
        for category_id, column in selected_columns.items():
            if column not in row:
                raise OwidError(f"OWID column is not present in chart data: {column}")
            raw_value = row[column].strip()
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as error:
                raise OwidError(f"OWID column {column} is not numeric for {self.entity} in {time_period}") from error
            if value < 0:
                raise OwidError(f"OWID column {column} is negative for {self.entity} in {time_period}")
            column_metadata = metadata.get("columns", {}).get(column, {}) if isinstance(metadata, dict) else {}
            label = (
                column_metadata.get("titleShort")
                or column_metadata.get("titleLong")
                or column
            )
            values.append(SourceValue(category_id=category_id, category_label=str(label), value=value))

        chart = metadata.get("chart", {}) if isinstance(metadata, dict) else {}
        chart_title = chart.get("title") if isinstance(chart, dict) else None
        chart_url = chart.get("originalChartUrl") if isinstance(chart, dict) else None
        source_url = chart_url or f"https://ourworldindata.org/grapher/{self.slug}"
        resolved_unit = self.unit or self._common_unit(metadata, selected_columns)
        source_metadata = {
            "provider": "owid",
            "slug": self.slug,
            "entity": self.entity,
            "columns": selected_columns,
            "chartTitle": chart_title,
            "chart": chart,
            "columnsMetadata": {
                column: metadata.get("columns", {}).get(column, {})
                for column in selected_columns.values()
            },
            "csvUrl": csv_url,
            "metadataUrl": metadata_url,
            "dedupeKey": f"owid:{self.slug}:{self.entity}:{time_period}",
        }
        return SourceDataset(
            source_name="Our World in Data",
            source_dataset_id=self.dataset_id,
            source_url=source_url,
            measure=self.measure or str(chart_title or self.slug),
            unit=resolved_unit,
            geography=self.geography,
            time_period=time_period,
            population_universe=self.population_universe,
            values=values,
            source_metadata=source_metadata,
            raw_payload={"csv": csv_response.text, "metadata": metadata},
        )

    def _select_row(self, rows: list[dict[str, str]]) -> tuple[dict[str, str], str]:
        matching = [row for row in rows if row.get("Entity", "").casefold() == self.entity.casefold()]
        if not matching:
            raise OwidError(f"OWID chart has no rows for entity {self.entity}")
        time_column = "Year" if "Year" in matching[0] else "Day" if "Day" in matching[0] else None
        if time_column is None:
            raise OwidError("OWID chart has no Year or Day column")
        if self.year != "latest":
            requested = str(self.year)
            matching = [row for row in matching if row.get(time_column) == requested]
            if not matching:
                raise OwidError(f"OWID chart has no {time_column}={requested} row for {self.entity}")
        else:
            matching.sort(key=lambda row: row.get(time_column, ""))
        row = matching[-1]
        return row, row[time_column]

    @staticmethod
    def _numeric_columns(rows: list[dict[str, str]], row: dict[str, str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for column in row:
            if column in {"Entity", "Code", "Year", "Day"}:
                continue
            try:
                value = float(row[column])
            except (TypeError, ValueError):
                continue
            if value >= 0:
                result[f"category-{len(result) + 1}"] = column
        return result

    @staticmethod
    def _common_unit(metadata: dict[str, Any], columns: dict[str, str]) -> str | None:
        units = {
            str(metadata.get("columns", {}).get(column, {}).get("unit"))
            for column in columns.values()
            if metadata.get("columns", {}).get(column, {}).get("unit")
        }
        return units.pop() if len(units) == 1 else None
