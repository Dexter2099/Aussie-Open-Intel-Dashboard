from __future__ import annotations

import json
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
    """Fetch a news feed in RSS or JSON format."""
    feed_url = url or os.getenv("NEWS_FEED_URL")
    if not feed_url:
        raise SystemExit("NEWS_FEED_URL not set")
    req = request.Request(feed_url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - url from env
        content = resp.read()
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
    key = f"{datetime.utcnow().isoformat()}_payload"
    try:
        store.put_raw("news-feed", key, content, ctype)
    except Exception as exc:  # pragma: no cover - storage optional
        logger.warning("Failed to store raw payload: %s", exc)
    text = content.decode("utf-8", errors="ignore")
    try:
        data = json.loads(text)
    except Exception:
        data = text
    return RawPayload(source_name=feed_url, fetched_at=datetime.utcnow(), url=feed_url, content=data)


def normalize(raw: RawPayload) -> List[NormalizedEvent]:
    if isinstance(raw.content, str):
        try:
            root = ET.fromstring(raw.content)
        except Exception:
            return []
        items = root.findall(".//item")
        events: List[NormalizedEvent] = []
        for it in items:
            title = it.findtext("title") or "News"
            body = it.findtext("description")
            pub = it.findtext("pubDate")
            occurred_dt = None
            if pub:
                for fmt in ["%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ"]:
                    try:
                        occurred_dt = datetime.strptime(pub, fmt)
                        break
                    except Exception:
                        continue
            events.append(NormalizedEvent(title=title, body=body, event_type="News", occurred_at=occurred_dt))
        return events
    else:
        items = raw.content.get("items", []) if isinstance(raw.content, dict) else []
        events: List[NormalizedEvent] = []
        for it in items:
            occurred = it.get("published") or it.get("date")
            occurred_dt = None
            if occurred:
                try:
                    occurred_dt = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
                except Exception:
                    occurred_dt = None
            events.append(
                NormalizedEvent(
                    title=it.get("title") or "News",
                    body=it.get("summary"),
                    event_type="News",
                    occurred_at=occurred_dt,
                    attrs={k: v for k, v in it.items() if k not in {"title", "summary", "published", "date"}},
                )
            )
        return events


def get_source_meta(url: str | None = None) -> Tuple[str, str, str]:
    feed_url = url or os.getenv("NEWS_FEED_URL", "")
    return "News Feed", feed_url, "News"
