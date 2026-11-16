"""Начальная схема: группы, пользователи, дисциплины, работы, сдачи

Revision ID: 0001
Revises:
Create Date: 2026-11-10 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("role IN ('student', 'teacher')", name="ck_users_role"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_group_id", "users", ["group_id"])
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subjects_teacher_id", "subjects", ["teacher_id"])
    op.create_index("ix_subjects_group_id", "subjects", ["group_id"])
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assignments_subject_id", "assignments", ["subject_id"])
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="not_started", nullable=False),
        sa.Column("comment", sa.Text(), server_default="", nullable=False),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'submitted', 'rework', 'accepted')",
            name="ck_submissions_status"),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "student_id",
                            name="uq_submission_assignment_student"),
    )
    op.create_index("ix_submissions_student_id", "submissions", ["student_id"])
    op.create_index("ix_submissions_assignment_id", "submissions", ["assignment_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_assignment_id", table_name="submissions")
    op.drop_index("ix_submissions_student_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_assignments_subject_id", table_name="assignments")
    op.drop_table("assignments")
    op.drop_index("ix_subjects_group_id", table_name="subjects")
    op.drop_index("ix_subjects_teacher_id", table_name="subjects")
    op.drop_table("subjects")
    op.drop_index("ix_users_group_id", table_name="users")
    op.drop_table("users")
    op.drop_table("groups")
