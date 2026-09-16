from __future__ import annotations

from typing import Protocol

from ..models.source import SourceDataset


class SourceAdapter(Protocol):
    def fetch(self) -> SourceDataset:
        """Fetch and normalize one source dataset."""

