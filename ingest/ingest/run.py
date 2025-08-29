import argparse
import logging
import os
import time
from datetime import datetime
from typing import List, Tuple

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from .common.schemas import NormalizedEvent
from .common import db as dbmod
from services.etl import fusion


def run_adapter(name: str, feed_url: str | None = None) -> Tuple[List[NormalizedEvent], str, str, str]:
    if name == "au_wildfire_fixture":
        from .adapters import au_wildfire_fixture as adapter
        raw = adapter.load_fixture()
        source_name, source_url, source_type = adapter.get_source_meta()
    elif name == "http_json_feed":
        from .adapters import http_json_feed as adapter
        raw = adapter.fetch_feed(feed_url)
        source_name, source_url, source_type = adapter.get_source_meta(feed_url)
    else:
        raise SystemExit(f"Unknown adapter: {name}")

    events = adapter.normalize(raw)
    return events, source_name, source_url, source_type


def persist(events: List[NormalizedEvent], source_name: str, source_url: str, source_type: str) -> int:
    """Persist normalised events and derived entities/relations."""

    count = 0
    with dbmod.get_conn() as conn:
        with conn.cursor() as cur:
            source_id = dbmod.ensure_source(cur, source_name, source_url, source_type)
            for ev in events:
                event_id = dbmod.insert_event(
                    cur,
                    source_id=source_id,
                    title=ev.title,
                    body=ev.body,
                    event_type=ev.event_type,
                    occurred_at=ev.occurred_at.isoformat() if ev.occurred_at else None,
                    lat=ev.lat,
                    lon=ev.lon,
                    jurisdiction=ev.jurisdiction,
                    confidence=ev.confidence,
                    severity=ev.severity,
                )

                # Run ETL pipeline for entity/relationship extraction
                entities, relations = fusion.process_event({"title": ev.title, "body": ev.body or ""})
                ent_ids = {}
                for ent in entities:
                    attrs = {}
                    if "lat" in ent and "lon" in ent:
                        attrs.update({"lat": ent["lat"], "lon": ent["lon"]})
                    if "jurisdiction" in ent:
                        attrs["jurisdiction"] = ent["jurisdiction"]
                    ent_id = dbmod.ensure_entity(cur, ent["type"], ent["name"], attrs)
                    ent_ids[ent["name"]] = ent_id
                    dbmod.link_event_entity(cur, event_id, ent_id, "MENTIONS")

                for src_name, dst_name, rel in relations:
                    src_id = ent_ids.get(src_name)
                    dst_id = ent_ids.get(dst_name)
                    if src_id and dst_id:
                        dbmod.upsert_relation(cur, src_id, dst_id, rel)

                count += 1
        conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description="Run an ingestion adapter")
    parser.add_argument(
        "--adapter",
        default=os.getenv("INGEST_ADAPTER", "au_wildfire_fixture"),
        help="Adapter name",
    )
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--feed-url", default=os.getenv("FEED_URL"), help="Override feed URL")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    logger = structlog.get_logger()

    interval = int(os.getenv("INGEST_INTERVAL_SECONDS", "300"))

    clear_contextvars()
    bind_contextvars(source="ingest", adapter=args.adapter)

    def run_once() -> None:
        started = time.monotonic()
        events, source_name, source_url, source_type = run_adapter(args.adapter, args.feed_url)
        inserted = persist(events, source_name, source_url, source_type)
        duration = time.monotonic() - started
        bind_contextvars(
            events_normalized=len(events),
            events_inserted=inserted,
            duration_seconds=duration,
        )
        logger.info("cycle")

    if args.loop:
        while True:
            run_once()
            time.sleep(interval)
    else:
        run_once()


if __name__ == "__main__":
    main()

