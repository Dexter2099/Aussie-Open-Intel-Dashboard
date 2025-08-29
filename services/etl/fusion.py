"""Entity fusion, deduplication and relation helpers."""

from typing import Dict, List, Tuple

from .parser import parse_payload
from .nlp import extract_entities, extract_relations
from .enrich import enrich_entities


def dedupe_entities(entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Deduplicate entities by type/name pair."""

    seen: Dict[Tuple[str, str], Dict[str, str]] = {}
    for ent in entities:
        key = (ent["type"], ent["name"].lower())
        if key not in seen:
            seen[key] = ent
    return list(seen.values())


def process_event(raw_event: Dict[str, str]) -> Tuple[List[Dict[str, str]], List[Tuple[str, str, str]]]:
    """Run full parse → NER → enrich → fuse pipeline for a raw event."""

    parsed = parse_payload(raw_event)
    entities = extract_entities(parsed.text)
    enrich_entities(entities)
    entities = dedupe_entities(entities)
    relations = extract_relations(parsed.text, entities)
    return entities, relations
