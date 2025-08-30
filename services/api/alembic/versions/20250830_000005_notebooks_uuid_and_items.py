"""Convert notebooks to UUID + add notebook_items

Revision ID: 20250830_000005
Revises: 20250830_000001
Create Date: 2025-08-30 11:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250830_000005"
down_revision = "20250830_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop legacy notebooks table if it exists and recreate with UUID PK
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "notebooks" in tables:
        op.drop_table("notebooks")

    op.create_table(
        "notebooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "notebook_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("ref_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
    )
    # Add a check constraint for kind values
    op.create_check_constraint(
        "ck_notebook_items_kind",
        "notebook_items",
        "kind IN ('event','entity')",
    )
    op.create_index(
        "idx_notebook_items_notebook_created",
        "notebook_items",
        ["notebook_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_notebook_items_notebook_created", table_name="notebook_items")
    op.drop_constraint("ck_notebook_items_kind", "notebook_items")
    op.drop_table("notebook_items")
    op.drop_table("notebooks")

