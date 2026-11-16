"""Добавить время сдачи работы submissions.submitted_at

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch:
        batch.add_column(sa.Column("submitted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch:
        batch.drop_column("submitted_at")
