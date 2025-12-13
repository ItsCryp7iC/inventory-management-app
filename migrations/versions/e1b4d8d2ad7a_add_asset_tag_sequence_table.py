"""Add asset tag sequence table

Revision ID: e1b4d8d2ad7a
Revises: caab36e76fa0
Create Date: 2025-12-13 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1b4d8d2ad7a'
down_revision = 'caab36e76fa0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset_tag_sequences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('office_code', sa.String(length=50), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('last_seq', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('office_code', 'year', name='uq_asset_tag_seq_office_year')
    )


def downgrade():
    op.drop_table('asset_tag_sequences')
