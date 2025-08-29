-- Initial schema for MVP (events, entities, relations, notebooks, audit)
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS sources (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT,
  type TEXT,
  legal_notes TEXT
);

CREATE TYPE event_type AS ENUM (
  'Weather','Disaster','Wildfire','Earthquake','Maritime','Aviation','GovLE','Cyber','Other'
);

CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  source_id INT REFERENCES sources(id),
  title TEXT NOT NULL,
  body TEXT,
  event_type event_type DEFAULT 'Other',
  occurred_at TIMESTAMPTZ,
  detected_at TIMESTAMPTZ DEFAULT now(),
  geom geography,
  jurisdiction TEXT,
  confidence REAL,
  severity REAL
);

CREATE TYPE entity_type AS ENUM (
  'Person','Org','Vessel','Aircraft','Location','Asset','EventType'
);

CREATE TABLE IF NOT EXISTS entities (
  id BIGSERIAL PRIMARY KEY,
  type entity_type NOT NULL,
  name TEXT NOT NULL,
  canonical_key TEXT,
  attrs JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS event_entities (
  event_id BIGINT REFERENCES events(id) ON DELETE CASCADE,
  entity_id BIGINT REFERENCES entities(id) ON DELETE CASCADE,
  relation TEXT NOT NULL,
  score REAL,
  PRIMARY KEY (event_id, entity_id, relation)
);

CREATE TABLE IF NOT EXISTS relations (
  src_entity BIGINT REFERENCES entities(id) ON DELETE CASCADE,
  dst_entity BIGINT REFERENCES entities(id) ON DELETE CASCADE,
  relation TEXT NOT NULL,
  first_seen TIMESTAMPTZ DEFAULT now(),
  last_seen TIMESTAMPTZ DEFAULT now(),
  weight REAL,
  PRIMARY KEY (src_entity, dst_entity, relation)
);

-- Placeholder for vector embeddings table; integrate Qdrant later
CREATE TABLE IF NOT EXISTS event_embeddings (
  event_id BIGINT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  vector BYTEA
);

CREATE TABLE IF NOT EXISTS notebooks (
  id BIGSERIAL PRIMARY KEY,
  owner TEXT NOT NULL,
  title TEXT NOT NULL,
  items JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit (
  id BIGSERIAL PRIMARY KEY,
  "user" TEXT,
  action TEXT NOT NULL,
  payload JSONB,
  ts TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_detected_at ON events(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_geom ON events USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_entities_type_name ON entities(type, name);
CREATE INDEX IF NOT EXISTS idx_event_entities_event ON event_entities(event_id);
CREATE INDEX IF NOT EXISTS idx_relations_src_dst ON relations(src_entity, dst_entity);

