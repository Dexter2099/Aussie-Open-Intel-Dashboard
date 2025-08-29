"""create core schema

Revision ID: 20250830_000001
Revises: 
Create Date: 2025-08-30 00:00:01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250830_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Enums
    event_type = postgresql.ENUM(
        "Weather",
        "Disaster",
        "Wildfire",
        "Earthquake",
        "Maritime",
        "Aviation",
        "GovLE",
        "Cyber",
        "Other",
        name="event_type",
    )
    event_type.create(op.get_bind(), checkfirst=True)

    entity_type = postgresql.ENUM(
        "Person",
        "Org",
        "Vessel",
        "Aircraft",
        "Location",
        "Asset",
        "EventType",
        name="entity_type",
    )
    entity_type.create(op.get_bind(), checkfirst=True)

    # sources
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("type", sa.Text()),
        sa.Column("legal_notes", sa.Text()),
    )

    # events
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("event_type", postgresql.ENUM(name="event_type"), server_default=sa.text("'Other'")),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("jurisdiction", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("severity", sa.Float()),
        sa.Column("entities", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw", postgresql.JSONB()),
    )

    # Add PostGIS geography Point column via SQL
    op.execute("ALTER TABLE events ADD COLUMN geom geography(POINT,4326)")

    # Unique constraint to avoid dupes
    op.create_unique_constraint("uq_events_source_title_occurred", "events", ["source_id", "title", "occurred_at"])

    # entities
    op.create_table(
        "entities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("type", sa.Enum(name="entity_type", native_enum=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text()),
        sa.Column("attrs", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
    )

    # event_entities
    op.create_table(
        "event_entities",
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("score", sa.Float()),
        sa.PrimaryKeyConstraint("event_id", "entity_id", "relation"),
    )

    # relations
    op.create_table(
        "relations",
        sa.Column("src_entity", sa.BigInteger(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dst_entity", sa.BigInteger(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("first_seen", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("weight", sa.Float()),
        sa.PrimaryKeyConstraint("src_entity", "dst_entity", "relation"),
    )

    # notebooks
    op.create_table(
        "notebooks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # event_embeddings placeholder
    op.create_table(
        "event_embeddings",
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("vector", postgresql.BYTEA()),
    )

    # audit
    op.create_table(
        "audit",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user", sa.Text()),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_detected_at ON events(detected_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_geom ON events USING GIST(geom)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_entities_type_name ON entities(type, name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_event_entities_event ON event_entities(event_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_relations_src_dst ON relations(src_entity, dst_entity)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_event_type_detected_at ON events(event_type, detected_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_source_detected_at ON events(source_id, detected_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_text_search ON events USING GIN (to_tsvector('simple', title || ' ' || coalesce(body,'')))")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_entities_gin ON events USING GIN (entities)")


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("audit")
    op.drop_table("event_embeddings")
    op.drop_table("notebooks")
    op.drop_table("relations")
    op.drop_table("event_entities")
    op.drop_table("entities")
    # drop indexes created via execute are dropped with table in PG, keep explicit cleanup
    op.drop_constraint("uq_events_source_title_occurred", "events", type_="unique")
    op.drop_table("events")
    op.drop_table("sources")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS entity_type")
    op.execute("DROP TYPE IF EXISTS event_type")
