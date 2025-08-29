from __future__ import annotations

import argparse
import io
import os
import pathlib
from typing import List, Tuple, Type

import structlog
from minio import Minio
from tenacity import retry, stop_after_attempt, wait_fixed

from .adapters.base import Adapter, RawItem
from .adapters.bom import BOMAdapter
from .adapters.qfes import QFESAdapter
from .common import db as dbmod
from .common.schemas import NormalizedEvent

ADAPTERS: dict[str, Type[Adapter]] = {
    "bom": BOMAdapter,
    "qfes": QFESAdapter,
}


def _get_logger():
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    return structlog.get_logger()


logger = _get_logger()


def _store_raw(adapter_name: str, items: List[RawItem]) -> None:
    """Persist raw payloads to local disk or MinIO/S3."""

    endpoint = os.getenv("MINIO_ENDPOINT")
    if endpoint:
        client = Minio(
            endpoint,
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            secure=False,
        )
        bucket = os.getenv("RAW_BUCKET", "raw")
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        for idx, item in enumerate(items):
            data = item.json().encode("utf-8")
            name = f"{adapter_name}/{item.fetched_at.isoformat()}_{idx}.json"
            client.put_object(bucket, name, io.BytesIO(data), len(data))
    else:
        base = pathlib.Path(os.getenv("RAW_DIR", "raw")) / adapter_name
        base.mkdir(parents=True, exist_ok=True)
        for idx, item in enumerate(items):
            path = base / f"{item.fetched_at.isoformat()}_{idx}.json"
            path.write_text(item.json())


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def persist(
    events: List[NormalizedEvent],
    source_name: str,
    source_url: str | None,
    source_type: str | None,
) -> int:
    """Persist normalised events into the database."""

    count = 0
    with dbmod.get_conn() as conn:
        with conn.cursor() as cur:
            source_id = dbmod.ensure_source(cur, source_name, source_url, source_type)
            for ev in events:
                dbmod.insert_event(
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
                count += 1
        conn.commit()
    return count


def run_adapter(name: str) -> Tuple[List[NormalizedEvent], str, str, str]:
    adapter_cls = ADAPTERS.get(name)
    if not adapter_cls:
        raise SystemExit(f"Unknown adapter: {name}")
    adapter = adapter_cls()
    raw_items = adapter.fetch_raw()
    _store_raw(name, raw_items)
    events = adapter.parse(raw_items)
    # For our stubs we only know source name
    return events, adapter.source, None, "feed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("adapter", choices=ADAPTERS.keys())
    args = parser.parse_args()

    events, source_name, source_url, source_type = run_adapter(args.adapter)
    inserted = persist(events, source_name, source_url, source_type)
    logger.info("ingest_complete", adapter=args.adapter, events=len(events), inserted=inserted)


if __name__ == "__main__":
    main()
