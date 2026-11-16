"""Предметная область: роли, статусы, сущности и правила переходов."""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from .errors import ValidationError


class Role(str, Enum):
    """Роль пользователя."""

    STUDENT = "student"
    TEACHER = "teacher"


class Status(str, Enum):
    """Статус сдачи практической работы."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    REWORK = "rework"
    ACCEPTED = "accepted"


ALLOWED_TRANSITIONS = {
    Status.NOT_STARTED: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.SUBMITTED},
    Status.SUBMITTED: {Status.ACCEPTED, Status.REWORK},
    Status.REWORK: {Status.SUBMITTED},
    Status.ACCEPTED: set(),
}

NEAR_DEADLINE_DAYS = 3


@dataclass
class Group:
    """Учебная группа."""

    name: str
    id: Optional[int] = None


@dataclass
class User:
    """Пользователь системы: студент или преподаватель."""

    email: str
    password_hash: str
    full_name: str
    role: Role
    group_id: Optional[int] = None
    id: Optional[int] = None


@dataclass
class Subject:
    """Дисциплина, которую преподаватель ведёт для группы."""

    name: str
    teacher_id: int
    group_id: int
    id: Optional[int] = None


@dataclass
class Assignment:
    """Практическая работа дисциплины со сроком сдачи."""

    subject_id: int
    title: str
    description: str
    deadline: date
    id: Optional[int] = None


@dataclass
class Submission:
    """Состояние работы у конкретного студента."""

    assignment_id: int
    student_id: int
    status: Status = Status.NOT_STARTED
    comment: str = ""
    submitted_at: Optional[datetime] = None
    id: Optional[int] = None

    def change_status(self, new_status: Status, comment: str = "",
                      now: Optional[datetime] = None) -> Status:
        """Меняет статус по правилам переходов, возвращает прежний статус."""
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValidationError(
                f"Переход {self.status.value} -> {new_status.value} запрещён")
        if new_status == Status.REWORK and not comment.strip():
            raise ValidationError("При возврате на доработку нужен комментарий")
        old = self.status
        self.status = new_status
        if new_status == Status.SUBMITTED:
            self.submitted_at = now or datetime.now()
        if new_status in (Status.REWORK, Status.ACCEPTED):
            self.comment = comment
        return old


def days_left(deadline: date, today: date) -> int:
    """Сколько дней осталось до срока (отрицательное число, если срок прошёл)."""
    return (deadline - today).days


def deadline_flag(deadline: date, today: date, status: Status) -> str:
    """Подсветка срока: 'overdue', 'near' или '' (FR-11)."""
    if status == Status.ACCEPTED:
        return ""
    left = days_left(deadline, today)
    if left < 0:
        return "overdue"
    if left <= NEAR_DEADLINE_DAYS:
        return "near"
    return ""
