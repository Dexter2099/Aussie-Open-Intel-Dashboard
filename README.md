Open Intelligence Fusion Dashboard (Australia)

This monorepo scaffolds an OSINT ingestion, fusion, and analysis dashboard for Australia. It includes a FastAPI backend, Postgres + PostGIS, Redis, and placeholders for ingestion and a frontend.

Quick start
- Copy `.env.example` to `.env` and adjust as needed.
- Use Docker: `make up` (or `docker compose -f infra/docker-compose.yml up --build`)

Structure
- frontend/ — React app (placeholder)
- ingest/ — source adapters (placeholder)
- services/
  - api/ — FastAPI gateway
  - etl/ — ETL/fusion workers (placeholder)
- infra/ — Docker, database init, and ops

Status
- Phase 0 skeleton with basic API and infra configuration.

Authentication
--------------
The API uses a simple bearer token scheme. Provide an `Authorization: Bearer <token>`
header on requests. Tokens are not yet validated, but the value is attached to the
structured log context. Set `ALLOW_ANON=false` in the environment to require this
header; by default anonymous requests are permitted.

