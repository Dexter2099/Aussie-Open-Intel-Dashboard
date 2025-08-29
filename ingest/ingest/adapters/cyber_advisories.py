from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import List, Tuple
from urllib import request

from ..common import store
from ..common.schemas import RawPayload, NormalizedEvent

logger = logging.getLogger(__name__)


def fetch_feed(url: str | None = None) -> RawPayload:
    """Fetch cybersecurity advisories from the configured endpoint."""
    feed_url = url or os.getenv("CYBER_FEED_URL")
    if not feed_url:
        raise SystemExit("CYBER_FEED_URL not set")
    req = request.Request(feed_url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - url from env
        data = json.load(resp)
    key = f"{datetime.utcnow().isoformat()}_payload.json"
    try:
        store.put_raw("cyber-advisories", key, json.dumps(data).encode("utf-8"), "application/json")
    except Exception as exc:  # pragma: no cover - storage optional
        logger.warning("Failed to store raw payload: %s", exc)
    return RawPayload(source_name=feed_url, fetched_at=datetime.utcnow(), url=feed_url, content=data)


def normalize(raw: RawPayload) -> List[NormalizedEvent]:
    items = raw.content.get("advisories", []) if isinstance(raw.content, dict) else []
    events: List[NormalizedEvent] = []
    for it in items:
        try:
            occurred = it.get("published") or it.get("date")
            occurred_dt = None
            if occurred:
                try:
                    occurred_dt = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
                except Exception:
                    occurred_dt = None
            events.append(
                NormalizedEvent(
                    title=it.get("title") or "Advisory",
                    body=it.get("summary"),
                    event_type="Cybersecurity",
                    occurred_at=occurred_dt,
                    severity=it.get("severity"),
                    attrs={k: v for k, v in it.items() if k not in {"title", "summary", "published", "date", "severity"}},
                )
            )
        except Exception as exc:
            logger.warning("Skipping row: %s", exc)
    return events


def get_source_meta(url: str | None = None) -> Tuple[str, str, str]:
    feed_url = url or os.getenv("CYBER_FEED_URL", "")
    return "Cybersecurity Advisories", feed_url, "Cybersecurity"
