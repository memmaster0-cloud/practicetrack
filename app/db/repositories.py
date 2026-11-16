"""Реализации репозиториев на SQLAlchemy: переводят ORM-строки в объекты предметной области.

Все запросы к БД находятся в app/db/crud.py; сервисы зависят только от абстракций.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from ..domain import Assignment, Group, Role, Status, Subject, Submission, User
from ..repositories import (AssignmentRepository, GroupRepository, SubjectRepository,
                            SubmissionRepository, UserRepository)
from . import crud
from .models import AssignmentRow, SubjectRow, SubmissionRow, UserRow


def _user(r: UserRow) -> User:
    return User(email=r.email, password_hash=r.password_hash, full_name=r.full_name,
                role=Role(r.role), group_id=r.group_id, id=r.id)


def _subject(r: SubjectRow) -> Subject:
    return Subject(name=r.name, teacher_id=r.teacher_id, group_id=r.group_id, id=r.id)


def _assignment(r: AssignmentRow) -> Assignment:
    return Assignment(subject_id=r.subject_id, title=r.title, description=r.description,
                      deadline=r.deadline, id=r.id)


def _submission(r: SubmissionRow) -> Submission:
    return Submission(assignment_id=r.assignment_id, student_id=r.student_id,
                      status=Status(r.status), comment=r.comment,
                      submitted_at=r.submitted_at, id=r.id)


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, user: User) -> User:
        row = crud.create_user(self._s, user.email, user.password_hash, user.full_name,
                               user.role.value, user.group_id)
        user.id = row.id
        return user

    def get(self, user_id: int) -> Optional[User]:
        row = crud.get_user(self._s, user_id)
        return _user(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = crud.get_user_by_email(self._s, email)
        return _user(row) if row else None

    def list_students(self, group_id: int) -> List[User]:
        return [_user(r) for r in crud.list_students(self._s, group_id)]


class SqlGroupRepository(GroupRepository):
    def __init__(self, session: Session):
        self._s = session

    def get_or_create(self, name: str) -> Group:
        row = crud.get_group_by_name(self._s, name) or crud.create_group(self._s, name)
        return Group(name=row.name, id=row.id)

    def get(self, group_id: int) -> Optional[Group]:
        row = crud.get_group(self._s, group_id)
        return Group(name=row.name, id=row.id) if row else None


class SqlSubjectRepository(SubjectRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, subject: Subject) -> Subject:
        row = crud.create_subject(self._s, subject.name, subject.teacher_id, subject.group_id)
        subject.id = row.id
        return subject

    def get(self, subject_id: int) -> Optional[Subject]:
        row = crud.get_subject(self._s, subject_id)
        return _subject(row) if row else None

    def list_by_group(self, group_id: int) -> List[Subject]:
        return [_subject(r) for r in crud.list_subjects(self._s, group_id=group_id)]

    def list_by_teacher(self, teacher_id: int) -> List[Subject]:
        return [_subject(r) for r in crud.list_subjects(self._s, teacher_id=teacher_id)]


class SqlAssignmentRepository(AssignmentRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, assignment: Assignment) -> Assignment:
        row = crud.create_assignment(self._s, assignment.subject_id, assignment.title,
                                     assignment.description, assignment.deadline)
        assignment.id = row.id
        return assignment

    def get(self, assignment_id: int) -> Optional[Assignment]:
        row = crud.get_assignment(self._s, assignment_id)
        return _assignment(row) if row else None

    def save(self, assignment: Assignment) -> None:
        crud.update_assignment(self._s, assignment.id, title=assignment.title,
                               description=assignment.description,
                               deadline=assignment.deadline)

    def delete(self, assignment_id: int) -> None:
        crud.delete_assignment(self._s, assignment_id)

    def list_by_subject(self, subject_id: int) -> List[Assignment]:
        return [_assignment(r) for r in crud.list_assignments(self._s, subject_id)]


class SqlSubmissionRepository(SubmissionRepository):
    def __init__(self, session: Session):
        self._s = session

    def add(self, submission: Submission) -> Submission:
        row = crud.create_submission(self._s, submission.assignment_id, submission.student_id,
                                     submission.status.value, submission.comment,
                                     submission.submitted_at)
        submission.id = row.id
        return submission

    def get(self, submission_id: int) -> Optional[Submission]:
        row = crud.get_submission(self._s, submission_id)
        return _submission(row) if row else None

    def save(self, submission: Submission) -> None:
        crud.update_submission(self._s, submission.id, status=submission.status.value,
                               comment=submission.comment,
                               submitted_at=submission.submitted_at)

    def delete_by_assignment(self, assignment_id: int) -> None:
        crud.delete_submissions_by_assignment(self._s, assignment_id)

    def list_by_student(self, student_id: int) -> List[Submission]:
        return [_submission(r) for r in crud.list_submissions(self._s, student_id=student_id)]

    def list_by_assignment(self, assignment_id: int) -> List[Submission]:
        return [_submission(r) for r in
                crud.list_submissions(self._s, assignment_id=assignment_id)]
