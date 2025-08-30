from __future__ import annotations

import importlib
import hashlib
import os
from contextlib import contextmanager

from apscheduler.schedulers.blocking import BlockingScheduler
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ingest.ingest import run as run_mod
from ingest.common import db as dbmod

logger = structlog.get_logger(__name__)


@contextmanager
def _advisory_lock(name: str):
    """Try to obtain a PostgreSQL advisory lock for ``name``.

    Yields ``True`` if the lock was acquired, ``False`` otherwise. The lock is
    released when the context manager exits.
    """

    key = int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16) % (2 ** 31)
    with dbmod.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (key,))
            locked = cur.fetchone()[0]
            if not locked:
                yield False
                return
            try:
                yield True
            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (key,))
                conn.commit()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=60))
def _fetch_with_retry(mod):
    return mod.fetch_feed()


def _run_adapter(name: str, mod):
    raw = _fetch_with_retry(mod)
    events = mod.normalize(raw)
    meta = mod.get_source_meta()
    inserted = run_mod.persist(events, *meta)
    logger.info("ingest_complete", adapter=name, events=len(events), inserted=inserted)


def _job(name: str, mod):
    with _advisory_lock(name) as acquired:
        if not acquired:
            logger.info("skipping_locked", adapter=name)
            return
        try:
            _run_adapter(name, mod)
        except Exception as exc:  # pragma: no cover - logged
            logger.exception("adapter_failed", adapter=name, error=str(exc))


def _schedule_all(sched: BlockingScheduler) -> None:
    adapters = {
        "acsc": "ingest.adapters.acsc_adapter",
        "bom": "ingest.adapters.bom_warnings_adapter",
    }
    for name, mod_path in adapters.items():
        if os.getenv(f"ENABLE_{name.upper()}", "false").lower() != "true":
            continue
        interval = int(os.getenv(f"{name.upper()}_INTERVAL_MINUTES", "15"))
        mod = importlib.import_module(mod_path)
        sched.add_job(_job, "interval", minutes=interval, args=[name, mod], id=name)
        logger.info("scheduled", adapter=name, minutes=interval)


def main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    scheduler = BlockingScheduler()
    _schedule_all(scheduler)
    logger.info("runner_started")
    scheduler.start()


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
