from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import List, Tuple, Any
from urllib import request
from ..common import store

from ..common.schemas import RawPayload, NormalizedEvent

logger = logging.getLogger(__name__)


def fetch_feed(url: str | None = None) -> RawPayload:
    """Fetch JSON/GeoJSON payload from the configured URL."""
    feed_url = url or os.getenv("FEED_URL")
    if not feed_url:
        raise SystemExit("FEED_URL not set")
    req = request.Request(feed_url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - feed url is env-provided
        data = json.load(resp)

    # store raw payload in MinIO
    key = f"{datetime.utcnow().isoformat()}_payload.json"
    try:
        store.put_raw("http-json-feed", key, json.dumps(data).encode("utf-8"), "application/json")
    except Exception as e:
        logger.warning("Failed to store raw payload: %s", e)
    return RawPayload(source_name=feed_url, fetched_at=datetime.utcnow(), url=feed_url, content=data)


def _extract_items(data: Any) -> List[Any]:
    if isinstance(data, dict):
        if data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list):
            return data["features"]
        for key in ("items", "incidents", "events"):
            val = data.get(key)
            if isinstance(val, list):
                return val
        return [data]
    if isinstance(data, list):
        return data
    return []


def normalize(raw: RawPayload) -> List[NormalizedEvent]:
    items = _extract_items(raw.content)
    events: List[NormalizedEvent] = []
    for it in items:
        try:
            props = it.get("properties", it) if isinstance(it, dict) else {}
            title = props.get("title") or props.get("name") or props.get("id") or "Event"
            body = props.get("description") or props.get("summary")
            occurred = props.get("occurred_at") or props.get("time")
            occurred_dt = None
            if occurred:
                try:
                    occurred_dt = datetime.fromisoformat(occurred)
                except Exception:
                    occurred_dt = None
            lat = props.get("lat")
            lon = props.get("lon")
            geom = it.get("geometry") if isinstance(it, dict) else None
            if (lat is None or lon is None) and isinstance(geom, dict) and geom.get("type") == "Point":
                coords = geom.get("coordinates")
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
            events.append(
                NormalizedEvent(
                    title=title,
                    body=body,
                    event_type=props.get("event_type") or "Other",
                    occurred_at=occurred_dt,
                    jurisdiction=props.get("jurisdiction"),
                    confidence=props.get("confidence"),
                    severity=props.get("severity"),
                    lat=lat,
                    lon=lon,
                    attrs={
                        k: v
                        for k, v in props.items()
                        if k
                        not in {
                            "title",
                            "name",
                            "id",
                            "description",
                            "summary",
                            "occurred_at",
                            "time",
                            "lat",
                            "lon",
                            "event_type",
                            "jurisdiction",
                            "confidence",
                            "severity",
                        }
                    },
                )
            )
        except Exception as exc:
            logger.warning("Skipping row: %s", exc)
    return events


def get_source_meta(url: str | None = None) -> Tuple[str, str, str]:
    feed_url = url or os.getenv("FEED_URL", "")
    return "HTTP JSON Feed", feed_url, "Other"

