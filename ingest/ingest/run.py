import argparse
import os
import time
from datetime import datetime
from typing import List, Tuple

from .common.schemas import NormalizedEvent
from .common import db as dbmod


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
    count = 0
    with dbmod.get_conn() as conn:
        with conn.cursor() as cur:
            source_id = dbmod.ensure_source(cur, source_name, source_url, source_type)
            for ev in events:
                geom_wkt = None
                if ev.lat is not None and ev.lon is not None:
                    geom_wkt = f"POINT({ev.lon} {ev.lat})"
                if geom_wkt:
                    cur.execute(
                        """
                        INSERT INTO events
                          (source_id, title, body, event_type, occurred_at, detected_at, geom, jurisdiction, confidence, severity)
                        VALUES
                          (%s,%s,%s,%s::event_type,%s, now(), ST_GeogFromText(%s), %s, %s, %s)
                        ON CONFLICT (source_id, title, occurred_at) DO NOTHING
                        RETURNING id
                        """,
                        (
                            source_id,
                            ev.title,
                            ev.body,
                            ev.event_type,
                            ev.occurred_at.isoformat() if ev.occurred_at else None,
                            geom_wkt,
                            ev.jurisdiction,
                            ev.confidence,
                            ev.severity,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO events
                          (source_id, title, body, event_type, occurred_at, detected_at, jurisdiction, confidence, severity)
                        VALUES
                          (%s,%s,%s,%s::event_type,%s, now(), %s, %s, %s)
                        ON CONFLICT (source_id, title, occurred_at) DO NOTHING
                        RETURNING id
                        """,
                        (
                            source_id,
                            ev.title,
                            ev.body,
                            ev.event_type,
                            ev.occurred_at.isoformat() if ev.occurred_at else None,
                            ev.jurisdiction,
                            ev.confidence,
                            ev.severity,
                        ),
                    )
                if cur.fetchone():
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

    interval = int(os.getenv("INGEST_INTERVAL_SECONDS", "300"))

    def run_once() -> None:
        events, source_name, source_url, source_type = run_adapter(args.adapter, args.feed_url)
        inserted = persist(events, source_name, source_url, source_type)
        print(
            {
                "adapter": args.adapter,
                "fetched_at": datetime.utcnow().isoformat(),
                "events_normalized": len(events),
                "events_inserted": inserted,
            }
        )

    if args.loop:
        while True:
            started = datetime.utcnow()
            run_once()
            duration = (datetime.utcnow() - started).total_seconds()
            print({"cycle_complete": datetime.utcnow().isoformat(), "duration_seconds": duration})
            time.sleep(interval)
    else:
        run_once()


if __name__ == "__main__":
    main()

