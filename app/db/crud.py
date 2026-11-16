"""CRUD-операции над ORM-моделями (SQLAlchemy 2.0).

Функции делают flush, но не commit: транзакцией управляет вызывающий код
(контейнер зависимостей фиксирует изменения после успешной обработки запроса).
"""
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..domain import Role
from .models import AssignmentRow, GroupRow, SubjectRow, SubmissionRow, UserRow

USER_FIELDS = {"email", "password_hash", "full_name", "role", "group_id"}
SUBJECT_FIELDS = {"name", "teacher_id", "group_id"}
ASSIGNMENT_FIELDS = {"title", "description", "deadline"}
SUBMISSION_FIELDS = {"status", "comment", "submitted_at"}


def _create(db: Session, row):
    db.add(row)
    db.flush()
    return row


def _update(db: Session, model, row_id: int, data: Dict, allowed: set):
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Недопустимые поля: {sorted(unknown)}")
    row = db.get(model, row_id)
    if row is None:
        return None
    for key, value in data.items():
        setattr(row, key, value)
    db.flush()
    return row


def _delete(db: Session, model, row_id: int) -> bool:
    row = db.get(model, row_id)
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


# --- Группы ------------------------------------------------------------------------------

def create_group(db: Session, name: str) -> GroupRow:
    return _create(db, GroupRow(name=name))


def get_group(db: Session, group_id: int) -> Optional[GroupRow]:
    return db.get(GroupRow, group_id)


def get_group_by_name(db: Session, name: str) -> Optional[GroupRow]:
    return db.scalar(select(GroupRow).where(GroupRow.name == name))


def list_groups(db: Session) -> List[GroupRow]:
    return list(db.scalars(select(GroupRow).order_by(GroupRow.name)))


def update_group(db: Session, group_id: int, **data) -> Optional[GroupRow]:
    return _update(db, GroupRow, group_id, data, {"name"})


def delete_group(db: Session, group_id: int) -> bool:
    return _delete(db, GroupRow, group_id)


# --- Пользователи -------------------------------------------------------------------------

def create_user(db: Session, email: str, password_hash: str, full_name: str, role: str,
                group_id: Optional[int] = None) -> UserRow:
    return _create(db, UserRow(email=email, password_hash=password_hash, full_name=full_name,
                               role=role, group_id=group_id))


def get_user(db: Session, user_id: int) -> Optional[UserRow]:
    return db.get(UserRow, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[UserRow]:
    return db.scalar(select(UserRow).where(UserRow.email == email))


def list_users(db: Session, role: Optional[str] = None) -> List[UserRow]:
    query = select(UserRow).order_by(UserRow.id)
    if role is not None:
        query = query.where(UserRow.role == role)
    return list(db.scalars(query))


def list_students(db: Session, group_id: int) -> List[UserRow]:
    return list(db.scalars(select(UserRow).where(
        UserRow.group_id == group_id,
        UserRow.role == Role.STUDENT.value).order_by(UserRow.full_name)))


def update_user(db: Session, user_id: int, **data) -> Optional[UserRow]:
    return _update(db, UserRow, user_id, data, USER_FIELDS)


def delete_user(db: Session, user_id: int) -> bool:
    return _delete(db, UserRow, user_id)


# --- Дисциплины ---------------------------------------------------------------------------

def create_subject(db: Session, name: str, teacher_id: int, group_id: int) -> SubjectRow:
    return _create(db, SubjectRow(name=name, teacher_id=teacher_id, group_id=group_id))


def get_subject(db: Session, subject_id: int) -> Optional[SubjectRow]:
    return db.get(SubjectRow, subject_id)


def list_subjects(db: Session, teacher_id: Optional[int] = None,
                  group_id: Optional[int] = None) -> List[SubjectRow]:
    query = select(SubjectRow).order_by(SubjectRow.id)
    if teacher_id is not None:
        query = query.where(SubjectRow.teacher_id == teacher_id)
    if group_id is not None:
        query = query.where(SubjectRow.group_id == group_id)
    return list(db.scalars(query))


def update_subject(db: Session, subject_id: int, **data) -> Optional[SubjectRow]:
    return _update(db, SubjectRow, subject_id, data, SUBJECT_FIELDS)


def delete_subject(db: Session, subject_id: int) -> bool:
    return _delete(db, SubjectRow, subject_id)


# --- Практические работы ------------------------------------------------------------------

def create_assignment(db: Session, subject_id: int, title: str, description: str,
                      deadline: date) -> AssignmentRow:
    return _create(db, AssignmentRow(subject_id=subject_id, title=title,
                                     description=description, deadline=deadline))


def get_assignment(db: Session, assignment_id: int) -> Optional[AssignmentRow]:
    return db.get(AssignmentRow, assignment_id)


def list_assignments(db: Session, subject_id: int) -> List[AssignmentRow]:
    return list(db.scalars(select(AssignmentRow).where(
        AssignmentRow.subject_id == subject_id).order_by(AssignmentRow.deadline)))


def update_assignment(db: Session, assignment_id: int, **data) -> Optional[AssignmentRow]:
    return _update(db, AssignmentRow, assignment_id, data, ASSIGNMENT_FIELDS)


def delete_assignment(db: Session, assignment_id: int) -> bool:
    return _delete(db, AssignmentRow, assignment_id)


# --- Сдачи --------------------------------------------------------------------------------

def create_submission(db: Session, assignment_id: int, student_id: int,
                      status: str = "not_started", comment: str = "",
                      submitted_at: Optional[datetime] = None) -> SubmissionRow:
    return _create(db, SubmissionRow(assignment_id=assignment_id, student_id=student_id,
                                     status=status, comment=comment,
                                     submitted_at=submitted_at))


def get_submission(db: Session, submission_id: int) -> Optional[SubmissionRow]:
    return db.get(SubmissionRow, submission_id)


def list_submissions(db: Session, student_id: Optional[int] = None,
                     assignment_id: Optional[int] = None) -> List[SubmissionRow]:
    query = select(SubmissionRow).order_by(SubmissionRow.id)
    if student_id is not None:
        query = query.where(SubmissionRow.student_id == student_id)
    if assignment_id is not None:
        query = query.where(SubmissionRow.assignment_id == assignment_id)
    return list(db.scalars(query))


def update_submission(db: Session, submission_id: int, **data) -> Optional[SubmissionRow]:
    return _update(db, SubmissionRow, submission_id, data, SUBMISSION_FIELDS)


def delete_submission(db: Session, submission_id: int) -> bool:
    return _delete(db, SubmissionRow, submission_id)


def delete_submissions_by_assignment(db: Session, assignment_id: int) -> int:
    """Удаляет все сдачи работы одним запросом, возвращает число удалённых строк."""
    result = db.execute(delete(SubmissionRow).where(SubmissionRow.assignment_id == assignment_id))
    return result.rowcount
