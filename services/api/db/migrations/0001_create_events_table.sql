-- Create events table
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT CHECK (type IN ('cyber','bushfire','maritime','weather','news')),
    title TEXT NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    location GEOGRAPHY(POINT,4326),
    entities JSONB NOT NULL DEFAULT '[]',
    source TEXT NOT NULL,
    raw JSONB NOT NULL,
    UNIQUE (source, title, time)
);

CREATE INDEX IF NOT EXISTS ix_events_time ON events USING btree (time);
CREATE INDEX IF NOT EXISTS ix_events_type ON events USING btree (type);
CREATE INDEX IF NOT EXISTS ix_events_entities ON events USING gin (entities);
CREATE INDEX IF NOT EXISTS ix_events_location ON events USING gist (location);
