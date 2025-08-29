"""core schema tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('url', sa.Text),
        sa.Column('type', sa.Text),
        sa.Column('legal_notes', sa.Text)
    )

    op.create_table(
        'events',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('source_id', sa.Integer, sa.ForeignKey('sources.id')),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('body', sa.Text),
        sa.Column('event_type', sa.Text),
        sa.Column('occurred_at', sa.DateTime(timezone=True)),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('geom', Geography(geometry_type='POINT', srid=4326)),
        sa.Column('jurisdiction', sa.Text),
        sa.Column('confidence', sa.Float),
        sa.Column('severity', sa.Integer),
        sa.Column('raw_ref', sa.Text)
    )

    op.create_table(
        'entities',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('type', sa.Text, nullable=False),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('canonical_key', sa.Text),
        sa.Column('attrs', postgresql.JSONB, server_default=sa.text("'{}'::jsonb"))
    )

    op.create_table(
        'event_entities',
        sa.Column('event_id', sa.BigInteger, sa.ForeignKey('events.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('entity_id', sa.BigInteger, sa.ForeignKey('entities.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('relation', sa.Text, primary_key=True),
        sa.Column('score', sa.Float)
    )

    op.create_table(
        'relations',
        sa.Column('src_entity', sa.BigInteger, sa.ForeignKey('entities.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('dst_entity', sa.BigInteger, sa.ForeignKey('entities.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('relation', sa.Text, primary_key=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('weight', sa.Float)
    )

    op.create_table(
        'event_embeddings',
        sa.Column('event_id', postgresql.UUID, primary_key=True),
        sa.Column('vector_ref', sa.Text)
    )

    op.create_table(
        'notebooks',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('owner', sa.Text, nullable=False),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('items', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )

    op.create_table(
        'audit',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user', sa.Text),
        sa.Column('action', sa.Text, nullable=False),
        sa.Column('payload', postgresql.JSONB),
        sa.Column('ts', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )

    op.create_index('idx_events_detected_at', 'events', ['detected_at'], postgresql_using='btree')
    op.create_index('idx_entities_type_name', 'entities', ['type', 'name'])
    op.create_index('idx_event_entities_event', 'event_entities', ['event_id'])
    op.create_index('idx_relations_src_dst', 'relations', ['src_entity', 'dst_entity'])
    op.create_index('idx_events_event_type_detected_at', 'events', ['event_type', 'detected_at'])
    op.create_index('idx_events_source_detected_at', 'events', ['source_id', 'detected_at'])
    op.create_index('idx_events_text_search', 'events', [sa.text("to_tsvector('simple', title || ' ' || coalesce(body,''))")], postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('idx_events_text_search', table_name='events')
    op.drop_index('idx_events_source_detected_at', table_name='events')
    op.drop_index('idx_events_event_type_detected_at', table_name='events')
    op.drop_index('idx_relations_src_dst', table_name='relations')
    op.drop_index('idx_event_entities_event', table_name='event_entities')
    op.drop_index('idx_entities_type_name', table_name='entities')
    op.drop_index('idx_events_detected_at', table_name='events')
    op.drop_table('audit')
    op.drop_table('notebooks')
    op.drop_table('event_embeddings')
    op.drop_table('relations')
    op.drop_table('event_entities')
    op.drop_table('entities')
    op.drop_table('events')
    op.drop_table('sources')
