Open Intelligence Fusion Dashboard — Cost efficient MVP
Objective
Build an end-to-end OSINT fusion dashboard while minimizing cloud and infra costs.
Constraint: keep ongoing cost under ~$25–50/month, using free tiers, open-source, and self-hosting where possible — but without compromising on completeness of features.

Core Features
1. Ingestion
•	Feeds (Initial 4):
o	Maritime AIS (free AIS APIs or demo CSVs).
o	Bushfire Alerts (Australian government APIs, free).
o	Cybersecurity Advisories (CISA/CERT RSS feeds, free).
o	News Feeds (RSS from ABC/Reuters/Guardian, free).
•	Implementation:
o	Python ingestion workers scheduled with cron or Celery (Redis broker).
o	Runs on a single small VM (Fly.io machine or Hetzner CX11 ~$5/mo).
•	Storage:
o	Postgres with PostGIS → host on Neon free tier (up to 3GB).
o	(Optional for caching) Redis via Upstash free tier.

2. Fusion & Entity Layer
•	Entity Extraction:
o	Use free/open NLP (spaCy, Hugging Face NER models).
o	No per-token API cost (avoid OpenAI, AWS Comprehend, etc.).
•	Graph Storage:
o	Store entity-event relationships in Postgres JSONB.
o	Build lightweight graph queries with SQL + PostGIS functions.
o	(Skip Neo4j paid cloud → too expensive).
•	Audit Trail:
o	Store raw source_url, timestamp, and original text for every record.

3. Frontend (Sense-Making Interfaces)
•	Framework: React (hosted free on Vercel/Netlify).
•	Map View: Leaflet.js + OpenStreetMap free tiles.
•	Timeline View: React timeline library.
•	Graph View: D3.js (fully client-side, no hosted graph DB required).
•	Event Detail: Raw description, entities, links, “Add to Notebook.”

4. Investigation Notebook
•	Notebook entries saved to Postgres.
•	Export supported:
o	Markdown / JSON (free).
o	PDF using ReportLab (runs locally, no API cost).
•	Share via link (simple token-based link sharing).

5. Security & Ops
•	Auth: Django allauth or FastAPI JWT → no paid identity provider.
•	Infra Hosting:
o	Backend: Fly.io (free credits, then ~$5/mo).
o	DB: Neon (free Postgres tier).
o	Cache: Upstash Redis (free tier).
o	Frontend: Vercel (free tier).
•	Monitoring: Free logging via Fly.io / Vercel dashboards, no Datadog.

Demo Narrative
1.	Analyst opens dashboard, filters Queensland region.
2.	Map shows a ship entering port, a bushfire alert, and a cyber advisory.
3.	Timeline orders them chronologically.
4.	Clicking the ship reveals an org → vessel → event link in the graph view.
5.	Analyst adds them into a notebook → exports to PDF with source citations.
6.	Demonstrates full cycle: Ingest → Fuse → Sense-Make → Action.
