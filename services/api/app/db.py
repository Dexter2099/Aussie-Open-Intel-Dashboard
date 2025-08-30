try:  # pragma: no cover - compatibility for different import paths
    from ..db import get_conn, fetch_one, fetch_all
    from ..db.events import upsert_event
except ImportError:  # when ``app`` is imported as top-level package in tests
    from db import get_conn, fetch_one, fetch_all  # type: ignore
    from db.events import upsert_event  # type: ignore
