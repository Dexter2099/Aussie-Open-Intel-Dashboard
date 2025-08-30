from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import List, Tuple
from urllib import request
from xml.etree import ElementTree as ET

from ..common import store
from ..common.schemas import RawPayload, NormalizedEvent

logger = logging.getLogger(__name__)


def fetch_feed(url: str | None = None) -> RawPayload:
    """Fetch BOM Queensland warnings feed."""
    feed_url = url or os.getenv("BOM_QLD_WARNINGS_URL")
    if not feed_url:
        raise SystemExit("BOM_QLD_WARNINGS_URL not set")
    req = request.Request(feed_url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - URL from env
        content = resp.read()
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
    key = f"{datetime.utcnow().isoformat()}_payload.xml"
    try:
        store.put_raw("bom-warnings", key, content, ctype)
    except Exception as exc:  # pragma: no cover - optional
        logger.warning("Failed to store raw payload: %s", exc)
    text = content.decode("utf-8", errors="ignore")
    return RawPayload(source_name=feed_url, fetched_at=datetime.utcnow(), url=feed_url, content=text)


def normalize(raw: RawPayload) -> List[NormalizedEvent]:
    try:
        root = ET.fromstring(raw.content)
    except Exception:
        return []
    events: List[NormalizedEvent] = []
    for warn in root.findall(".//warning"):
        title = warn.findtext("title") or "BOM Warning"
        desc = warn.findtext("description")
        issued = warn.findtext("issued")
        area = warn.findtext("area")
        occurred_dt = None
        if issued:
            try:
                occurred_dt = datetime.fromisoformat(issued.replace("Z", "+00:00"))
            except Exception:
                pass
        events.append(
            NormalizedEvent(
                title=title,
                body=desc,
                event_type="weather",
                occurred_at=occurred_dt,
                jurisdiction=area,
            )
        )
    return events


def get_source_meta(url: str | None = None) -> Tuple[str, str, str]:
    feed_url = url or os.getenv("BOM_QLD_WARNINGS_URL", "")
    return "BOM Queensland Warnings", feed_url, "Weather"
