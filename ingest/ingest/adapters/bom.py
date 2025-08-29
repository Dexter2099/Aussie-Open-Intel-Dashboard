from __future__ import annotations

from datetime import datetime
from typing import List

from structlog import get_logger

from .base import Adapter, RawItem
from ..common.schemas import NormalizedEvent

logger = get_logger(__name__)


class BOMAdapter(Adapter):
    """Minimal Bureau of Meteorology adapter."""

    source = "bom"

    def fetch_raw(self) -> List[RawItem]:
        logger.info("fetching", source=self.source)
        content = {"title": "BOM Weather Warning", "body": "Heavy rain expected"}
        item = RawItem(fetched_at=datetime.utcnow(), source=self.source, content=content)
        return [item]

    def parse(self, raw_items: List[RawItem]) -> List[NormalizedEvent]:
        events: List[NormalizedEvent] = []
        for item in raw_items:
            events.append(
                NormalizedEvent(
                    title=item.content.get("title", "BOM Event"),
                    body=item.content.get("body"),
                    event_type="Weather",
                )
            )
        return events
