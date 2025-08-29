from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel

from ..common.schemas import NormalizedEvent


class RawItem(BaseModel):
    """Container for a fetched raw payload."""

    fetched_at: datetime
    source: str
    content: Any
    url: Optional[str] = None


class Adapter(ABC):
    """Adapter interface for ingestion sources."""

    source: str

    @abstractmethod
    def fetch_raw(self) -> List[RawItem]:
        """Retrieve raw items from the upstream source."""

    @abstractmethod
    def parse(self, raw_items: List[RawItem]) -> List[NormalizedEvent]:
        """Parse raw items into normalized events."""
