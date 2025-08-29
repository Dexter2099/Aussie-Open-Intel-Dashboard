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
  severity REAL,
  entities JSONB DEFAULT '[]'::jsonb,
  raw JSONB,
  UNIQUE (source_id, title, occurred_at)
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
CREATE INDEX IF NOT EXISTS idx_events_event_type_detected_at ON events(event_type, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_source_detected_at ON events(source_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_text_search ON events USING GIN (to_tsvector('simple', title || ' ' || coalesce(body,'')));
CREATE INDEX IF NOT EXISTS idx_events_entities_gin ON events USING GIN (entities);

-- Seed minimal sample data so API returns non-empty results out-of-the-box
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM sources WHERE name = 'API Seed') THEN
    INSERT INTO sources(name, url, type) VALUES ('API Seed', 'fixture://seed', 'Other');
  END IF;

  -- Insert sample events if none exist for this seed source
  IF NOT EXISTS (SELECT 1 FROM events e JOIN sources s ON s.id=e.source_id WHERE s.name = 'API Seed') THEN
    -- Brisbane area
    INSERT INTO events (source_id, title, body, event_type, occurred_at, detected_at, geom, jurisdiction, confidence, severity)
    SELECT s.id,
           'Sample Event A',
           'Demonstration event near Brisbane (QLD).',
           'Other'::event_type,
           now() - interval '1 day',
           now(),
           ST_GeogFromText('POINT(153.0251 -27.4698)'),
           'QLD',
           0.7,
           0.3
    FROM sources s WHERE s.name='API Seed' LIMIT 1;

    -- Toowoomba area
    INSERT INTO events (source_id, title, body, event_type, occurred_at, detected_at, geom, jurisdiction, confidence, severity)
    SELECT s.id,
           'Sample Event B',
           'Demonstration event near Toowoomba (QLD).',
           'Other'::event_type,
           now() - interval '2 days',
           now(),
           ST_GeogFromText('POINT(151.9539 -27.5598)'),
           'QLD',
           0.8,
           0.5
    FROM sources s WHERE s.name='API Seed' LIMIT 1;
  END IF;
END $$;
