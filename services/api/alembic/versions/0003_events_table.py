"""create events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Drop any existing event-related tables to avoid conflicts
    conn.execute(sa.text("DROP TABLE IF EXISTS event_entities CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS event_embeddings CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS events CASCADE"))

    has_postgis = conn.execute(
        sa.text("SELECT COUNT(*) FROM pg_extension WHERE extname='postgis'")
    ).scalar() > 0

    cols = [
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.Text, nullable=False),
        sa.CheckConstraint(
            "type IN ('cyber','bushfire','maritime','weather','news')",
            name='ck_events_type',
        ),
        sa.Column('title', sa.Text),
        sa.Column('time', sa.TIMESTAMP(timezone=True)),
    ]

    if has_postgis:
        cols.append(sa.Column('location', Geography(geometry_type='POINT', srid=4326)))
    else:
        cols.extend([
            sa.Column('lon', sa.Numeric),
            sa.Column('lat', sa.Numeric),
        ])

    cols.extend([
        sa.Column('entities', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('source', sa.Text),
        sa.Column('raw', postgresql.JSONB, nullable=False),
    ])

    op.create_table('events', *cols)

    op.create_unique_constraint('uq_events_source_title_time', 'events', ['source', 'title', 'time'])
    op.create_index('ix_events_time', 'events', ['time'], postgresql_using='btree')
    op.create_index('ix_events_type', 'events', ['type'], postgresql_using='btree')
    op.create_index('ix_events_entities', 'events', ['entities'], postgresql_using='gin')
    if has_postgis:
        op.create_index('ix_events_location', 'events', ['location'], postgresql_using='gist')


def downgrade() -> None:
    conn = op.get_bind()
    has_postgis = conn.execute(
        sa.text("SELECT COUNT(*) FROM pg_extension WHERE extname='postgis'")
    ).scalar() > 0

    if has_postgis:
        op.drop_index('ix_events_location', table_name='events')
    op.drop_index('ix_events_entities', table_name='events')
    op.drop_index('ix_events_type', table_name='events')
    op.drop_index('ix_events_time', table_name='events')
    op.drop_constraint('uq_events_source_title_time', 'events', type_='unique')
    op.drop_table('events')
