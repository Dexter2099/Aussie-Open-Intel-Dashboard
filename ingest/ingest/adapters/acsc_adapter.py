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
    """Fetch ACSC advisories RSS feed."""
    feed_url = url or os.getenv("ACSC_RSS_URL")
    if not feed_url:
        raise SystemExit("ACSC_RSS_URL not set")
    req = request.Request(feed_url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - URL from env
        content = resp.read()
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
    key = f"{datetime.utcnow().isoformat()}_payload.xml"
    try:
        store.put_raw("acsc-advisories", key, content, ctype)
    except Exception as exc:  # pragma: no cover - storage optional
        logger.warning("Failed to store raw payload: %s", exc)
    text = content.decode("utf-8", errors="ignore")
    return RawPayload(source_name=feed_url, fetched_at=datetime.utcnow(), url=feed_url, content=text)


def normalize(raw: RawPayload) -> List[NormalizedEvent]:
    try:
        root = ET.fromstring(raw.content)
    except Exception:
        return []
    events: List[NormalizedEvent] = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or "Advisory"
        body = item.findtext("description")
        pub = item.findtext("pubDate")
        occurred_dt = None
        if pub:
            for fmt in ["%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    occurred_dt = datetime.strptime(pub, fmt)
                    break
                except Exception:
                    continue
        # ACSC advisories represent cybersecurity incidents.  The project uses a
        # short ``Cyber`` event_type to categorise them consistently with other
        # feeds.
        events.append(
            NormalizedEvent(
                title=title,
                body=body,
                event_type="Cyber",
                occurred_at=occurred_dt,
            )
        )
    return events


def get_source_meta(url: str | None = None) -> Tuple[str, str, str]:
    feed_url = url or os.getenv("ACSC_RSS_URL", "")
    return "ACSC Advisories", feed_url, "Cybersecurity"
