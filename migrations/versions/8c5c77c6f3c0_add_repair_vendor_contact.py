"""add repair vendor contact fields

Revision ID: 8c5c77c6f3c0
Revises: 5c3e7fd8d5b4
Create Date: 2025-12-14 01:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8c5c77c6f3c0"
down_revision = "5c3e7fd8d5b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assets", sa.Column("repair_vendor_phone", sa.String(length=100), nullable=True))
    op.add_column("assets", sa.Column("repair_vendor_address", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("assets", "repair_vendor_address")
    op.drop_column("assets", "repair_vendor_phone")
