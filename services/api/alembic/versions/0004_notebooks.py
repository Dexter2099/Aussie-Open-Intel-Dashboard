from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notebooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('created_by', sa.Text, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_table(
        'notebook_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('notebook_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('notebooks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.Text, nullable=False),
        sa.CheckConstraint("kind IN ('event','entity')", name='ck_notebook_items_kind'),
        sa.Column('ref_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_notebook_items_notebook_id', 'notebook_items', ['notebook_id'])


def downgrade() -> None:
    op.drop_index('ix_notebook_items_notebook_id', table_name='notebook_items')
    op.drop_table('notebook_items')
    op.drop_table('notebooks')
