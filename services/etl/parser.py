from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ParsedPayload:
    """Simple container for parsed raw payload text."""

    text: str


def parse_payload(raw: Dict[str, Any]) -> ParsedPayload:
    """Extract a text blob from a raw event payload.

    The ingestion adapters provide dictionaries with ``title`` and ``body``
    fields.  This helper concatenates them and normalises ``None`` values so
    later NLP steps receive a plain string.
    """

    title = raw.get("title") or ""
    body = raw.get("body") or ""
    text = f"{title}\n{body}".strip()
    return ParsedPayload(text=text)
