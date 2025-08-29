from __future__ import annotations

from datetime import datetime
from typing import List

from structlog import get_logger

from .base import Adapter, RawItem
from ..common.schemas import NormalizedEvent

logger = get_logger(__name__)


class QFESAdapter(Adapter):
    """Minimal Queensland Fire and Emergency Services adapter."""

    source = "qfes"

    def fetch_raw(self) -> List[RawItem]:
        logger.info("fetching", source=self.source)
        content = {"title": "QFES Incident", "body": "Small bushfire reported"}
        item = RawItem(fetched_at=datetime.utcnow(), source=self.source, content=content)
        return [item]

    def parse(self, raw_items: List[RawItem]) -> List[NormalizedEvent]:
        events: List[NormalizedEvent] = []
        for item in raw_items:
            events.append(
                NormalizedEvent(
                    title=item.content.get("title", "QFES Event"),
                    body=item.content.get("body"),
                    event_type="Fire",
                )
            )
        return events
