"""Add vendor code

Revision ID: 5c3e7fd8d5b4
Revises: 0c1f6cc0db24
Create Date: 2025-12-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c3e7fd8d5b4'
down_revision = '0c1f6cc0db24'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vendors') as batch_op:
        batch_op.add_column(sa.Column('code', sa.String(length=20), nullable=True))
        batch_op.create_unique_constraint('uq_vendor_code', ['code'])


def downgrade():
    with op.batch_alter_table('vendors') as batch_op:
        batch_op.drop_constraint('uq_vendor_code', type_='unique')
        batch_op.drop_column('code')
