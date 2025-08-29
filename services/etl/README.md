ETL/Fusion service placeholder

This service will implement parse → NER → enrich → fuse pipelines, writing to events/entities/relations tables and optional vector store.

Suggested modules:
- parser/: adapters to parse raw payloads into normalized events
- nlp/: spaCy pipelines and fuzzy matching utilities
- enrich/: geocoding, timezone, jurisdiction tagging
- fuse/: canonicalization and dedup logic

