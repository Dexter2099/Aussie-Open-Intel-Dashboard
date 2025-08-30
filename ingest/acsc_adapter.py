"""Adapter for ingesting ACSC advisories RSS feed.

This module fetches the public Australian Cyber Security Centre RSS feed and
stores each entry as a normalised event in the database.  A very small CLI is
provided so it can be executed directly::

    python -m ingest.acsc_adapter --since 7d

The ``--since`` option filters items based on their publication date in order
to avoid re-ingesting historical entries.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional
from urllib import request
from xml.etree import ElementTree as ET

from . import common


# URL for the official ACSC advisories RSS feed
FEED_URL = "https://www.cyber.gov.au/acsc/view-all-content/alerts/rss.xml"


@dataclass
class Event:
    """Simple representation of a normalised event."""

    type: str
    title: str
    time: Optional[datetime]
    source: Optional[str]
    raw: str
    entities: List[str] = field(default_factory=list)
    location: Optional[str] = None


def fetch(url: str = FEED_URL) -> str:
    """Return the RSS feed located at ``url`` as a text string."""

    req = request.Request(url, headers={"User-Agent": "AOID-Ingest/1.0"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - controlled URL
        return resp.read().decode("utf-8", errors="ignore")


def parse(xml_text: str) -> List[Event]:
    """Parse RSS ``xml_text`` into a list of :class:`Event` objects."""

    root = ET.fromstring(xml_text)
    events: List[Event] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = item.findtext("link")
        pub = item.findtext("pubDate")
        try:
            pub_dt = parsedate_to_datetime(pub) if pub else None
            if pub_dt and pub_dt.tzinfo is not None:
                # Normalise to naive UTC for comparisons and storage
                pub_dt = pub_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            pub_dt = None
        raw_xml = ET.tostring(item, encoding="unicode")
        events.append(Event("cyber", title, pub_dt, link, raw_xml))
    return events


def insert_events(events: List[Event]) -> int:
    """Insert ``events`` into the database, skipping duplicates."""

    if not events:
        return 0

    inserted = 0
    with common.get_conn() as conn:
        with conn.cursor() as cur:
            source_id = common.ensure_source(cur, "ACSC Alerts", FEED_URL, "cyber")
            for ev in events:
                if not ev.time:
                    continue
                if common.event_exists(cur, source_id, ev.title, ev.time):
                    continue
                res = common.insert_event(
                    cur,
                    source_id=source_id,
                    title=ev.title,
                    body=ev.source,  # store advisory link as body for now
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
        Duration string passed to :func:`common.parse_since` describing how far
        back to ingest items (e.g. ``"7d"`` or ``"12h"``).
    """

    cutoff = common.parse_since(since)
    xml_text = fetch(FEED_URL)
    events = [ev for ev in parse(xml_text) if ev.time and ev.time >= cutoff]
    return insert_events(events)


def main(argv: Optional[List[str]] = None) -> None:  # pragma: no cover - CLI thin wrapper
    """Entry point for command line execution."""

    parser = argparse.ArgumentParser(description="Ingest ACSC advisories RSS feed")
    parser.add_argument(
        "--since",
        default="7d",
        help="Only ingest items newer than this (e.g. 7d, 12h)",
    )
    args = parser.parse_args(argv)
    count = run(args.since)
    print(f"Inserted {count} events")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()

