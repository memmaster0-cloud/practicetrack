"""ORM-модели SQLAlchemy 2.0, соответствующие db/schema.sql."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GroupRow(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student', 'teacher')", name="ck_users_role"),
        Index("ix_users_group_id", "group_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("groups.id"))


class SubjectRow(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        Index("ix_subjects_teacher_id", "teacher_id"),
        Index("ix_subjects_group_id", "group_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))


class AssignmentRow(Base):
    __tablename__ = "assignments"
    __table_args__ = (Index("ix_assignments_subject_id", "subject_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    deadline: Mapped[date] = mapped_column(Date)


class SubmissionRow(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_submission_assignment_student"),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'submitted', 'rework', 'accepted')",
            name="ck_submissions_status"),
        Index("ix_submissions_student_id", "student_id"),
        Index("ix_submissions_assignment_id", "assignment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="not_started",
                                        server_default="not_started")
    comment: Mapped[str] = mapped_column(Text, default="", server_default="")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
