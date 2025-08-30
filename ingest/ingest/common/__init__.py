"""Common utilities for ingest adapters.

This module exposes database helpers and small utilities that are shared
between adapter command line interfaces.  It wraps the lower level helper
functions from :mod:`ingest.common.db` with a couple of convenience
functions used by the ACSC adapter tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Optional

from . import db
from . import schemas  # re-export for backwards compatibility

__all__ = [
    "db",
    "schemas",
    "get_conn",
    "ensure_source",
    "insert_event",
    "event_exists",
    "parse_since",
]

# Re-export core database helpers -------------------------------------------------
get_conn = db.get_conn
ensure_source = db.ensure_source


def event_exists(cur, source_id: int, title: str, occurred_at: datetime) -> bool:
    """Return ``True`` if an event already exists in the database."""
    cur.execute(
        "SELECT 1 FROM events WHERE source_id=%s AND title=%s AND occurred_at=%s",
        (source_id, title, occurred_at.isoformat()),
    )
    return cur.fetchone() is not None


def insert_event(
    cur,
    source_id: int,
    title: str,
    body: Optional[str],
    event_type: str,
    occurred_at: datetime,
) -> Optional[int]:
    """Insert an event if it does not already exist.

    The underlying :func:`ingest.common.db.insert_event` helper does not
    perform any de-duplication, so this wrapper first checks whether an
    event with the same ``(source_id, title, occurred_at)`` triplet is
    already present.  If so, ``None`` is returned and no insert occurs.
    """

    if event_exists(cur, source_id, title, occurred_at):
        return None
    return db.insert_event(
        cur,
        source_id=source_id,
        title=title,
        body=body,
        event_type=event_type,
        occurred_at=occurred_at.isoformat() if occurred_at else None,
        lat=None,
        lon=None,
        jurisdiction=None,
        confidence=None,
        severity=None,
    )


_DURATION_RE = re.compile(r"^(\d+)([dh])$")


def parse_since(value: str) -> datetime:
    """Return a ``datetime`` representing ``value`` ago.

    ``value`` should be of the form ``"7d"`` for seven days or ``"12h"``
    for twelve hours.  A :class:`ValueError` is raised for unsupported
    formats.
    """

    match = _DURATION_RE.match(value.strip())
    if not match:
        raise ValueError("duration should be like '7d' or '12h'")
    amount, unit = match.groups()
    delta = timedelta(days=int(amount)) if unit == "d" else timedelta(hours=int(amount))
    return datetime.utcnow() - delta
