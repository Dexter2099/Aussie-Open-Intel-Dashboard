Ingestion service placeholder

This folder will hold source adapters and cron/worker code for fetching AU-focused OSINT. Suggested structure:

- adapters/
  - bureau_weather.py
  - wildfire_state.py
  - seismic_geoscience.py
  - maritime_notices.py
  - gov_advisories.py
  - cyber_bulletins.py
- common/
  - client.py (retry/backoff)
  - schemas.py (raw + normalized event schema)
  - store.py (S3/MinIO and Postgres helpers)

Adapters should write raw payloads to object storage and normalized events to Postgres.

