"""Basic enrichment helpers (geocoding and jurisdiction lookup)."""

from typing import Dict, List, Optional, Tuple

# Minimal in-memory gazetteer for tests/demo
_GAZETTEER: Dict[str, Tuple[float, float, str]] = {
    "Sydney": (-33.8688, 151.2093, "AU-NSW"),
    "Melbourne": (-37.8136, 144.9631, "AU-VIC"),
}


def geocode(name: str) -> Optional[Tuple[float, float, str]]:
    """Return ``(lat, lon, jurisdiction)`` for a known location name."""

    return _GAZETTEER.get(name)


def enrich_entities(entities: List[Dict[str, str]]) -> None:
    """Attach geocoding / jurisdiction data in-place when possible."""

    for ent in entities:
        if ent.get("type") == "Location":
            hit = geocode(ent["name"])
            if hit:
                lat, lon, juris = hit
                ent["lat"] = lat
                ent["lon"] = lon
                ent["jurisdiction"] = juris
