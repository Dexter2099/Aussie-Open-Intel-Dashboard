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


### Scheduled Runner

`python -m ingest.run_all` uses APScheduler to run enabled adapters on an interval.
Enable adapters and set their schedule via environment variables:

```
ENABLE_ACSC=true
ACSC_INTERVAL_MINUTES=15
ENABLE_BOM=true
BOM_INTERVAL_MINUTES=15
```

The runner logs progress in structured JSON and uses database advisory locks so
repeated executions do not insert duplicates.
