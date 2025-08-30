"""Bureau of Meteorology Queensland warnings adapter.

This module exposes helper functions and a small CLI that fetches the BOM
Queensland RSS/Atom feed and inserts each warning as a normalised event.
The implementation mirrors the structure of the existing ACSC adapter so
that tests can patch the database layer easily.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from urllib import request
from xml.etree import ElementTree as ET

from . import common
FEED_URL = "http://www.bom.gov.au/fwo/IDZ00054.warnings_qld.xml"


@dataclass
class Event:
    type: str
    title: str
    time: Optional[datetime]
    source: Optional[str]
    raw: str
    entities: List[str] = field(default_factory=list)
    location: Optional[str] = None


def fetch(url: str = FEED_URL) -> str:
    """Return the warnings feed as a text string."""
    req = request.Request(url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - controlled URL
        return resp.read().decode("utf-8", errors="ignore")


def parse(xml_text: str) -> List[Event]:
    """Parse feed XML into a list of :class:`Event` objects.

    Each feed item is mapped to :class:`Event` capturing the title, issue
    time and link.  The complete XML snippet for the item is stored in the
    ``raw`` field so that no information is lost during ingestion.
    """
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//warning")
    events: List[Event] = []
    for item in items:
        title = (item.findtext("title") or "").strip()
        link = item.findtext("link")
        pub = item.findtext("pubDate") or item.findtext("issued")
        pub_dt: Optional[datetime] = None
        if pub:
            try:
                pub_dt = parsedate_to_datetime(pub)
            except Exception:
                try:
                    pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                except Exception:
                    pub_dt = None
        raw_xml = ET.tostring(item, encoding="unicode")
        events.append(Event("weather", title, pub_dt, link, raw_xml))
    return events


def insert_events(events: List[Event]) -> int:
    """Insert events into the database, skipping duplicates."""
    if not events:
        return 0
    inserted = 0
    with common.get_conn() as conn:
        with conn.cursor() as cur:
            source_id = common.ensure_source(cur, "BOM QLD Warnings", FEED_URL, "weather")
            for ev in events:
                if not ev.time:
                    continue
                if common.event_exists(cur, source_id, ev.title, ev.time):
                    continue
                res = common.insert_event(
                    cur,
                    source_id=source_id,
                    title=ev.title,
                    body=ev.source,  # store link as body for now
                    event_type=ev.type,
                    occurred_at=ev.time,
                )
                if res is not None:
                    inserted += 1
        conn.commit()
    return inserted


def run(since: str) -> int:
    """Fetch the feed and persist recent events.

    Parameters
    ----------
    since:
        Duration string such as ``"48h"`` used to filter out historical
        warnings.  Only items newer than this are inserted.
    """
    cutoff = common.parse_since(since)
    xml_text = fetch(FEED_URL)
    events = [ev for ev in parse(xml_text) if ev.time and ev.time >= cutoff]
    return insert_events(events)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest BOM QLD warnings RSS feed")
    parser.add_argument("--since", default="48h", help="Only ingest items newer than this (e.g. 7d, 12h)")
    args = parser.parse_args(argv)
    count = run(args.since)
    print(f"Inserted {count} events")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
