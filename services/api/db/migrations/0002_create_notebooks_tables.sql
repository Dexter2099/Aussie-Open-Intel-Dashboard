CREATE TABLE IF NOT EXISTS notebooks (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notebook_items (
    id UUID PRIMARY KEY,
    notebook_id UUID REFERENCES notebooks(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('event','entity')),
    ref_id UUID NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
