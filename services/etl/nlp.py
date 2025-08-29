"""spaCy based entity and relation extraction helpers."""

from typing import Dict, List, Tuple

import spacy

_nlp = None


def _get_model():
    """Load a small English model, falling back to a blank pipeline."""

    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            # Minimal fallback; still allows tests without the model download
            _nlp = spacy.blank("en")
            _nlp.add_pipe("sentencizer")
    return _nlp


ENTITY_TYPE_MAP = {
    "PERSON": "Person",
    "ORG": "Org",
    "GPE": "Location",
}


def extract_entities(text: str) -> List[Dict[str, str]]:
    """Run NER over ``text`` and map spaCy labels to our schema."""

    doc = _get_model()(text)
    entities: List[Dict[str, str]] = []
    for ent in doc.ents:
        etype = ENTITY_TYPE_MAP.get(ent.label_)
        if etype:
            entities.append({"type": etype, "name": ent.text})
    return entities


def extract_relations(text: str, entities: List[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """Very small heuristic relation extractor.

    For the demo we only recognise the phrase ``works at/for`` linking the
    first ``Person`` to the first ``Org`` and emitting an ``EMPLOYED_BY``
    relation.  Real implementations would use a dedicated model.
    """

    lower = text.lower()
    relations: List[Tuple[str, str, str]] = []
    if "works for" in lower or "works at" in lower:
        person = next((e for e in entities if e["type"] == "Person"), None)
        org = next((e for e in entities if e["type"] == "Org"), None)
        if person and org:
            relations.append((person["name"], org["name"], "EMPLOYED_BY"))
    return relations
