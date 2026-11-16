"""Демонстрационные данные для показа проекта (используются только сервисы приложения)."""
from datetime import date, timedelta
from typing import Dict, Optional

from .container import Container
from .domain import Role, Status
from .errors import ConflictError

DEMO_PASSWORD = "demo12345"
TEACHER_EMAIL = "teacher@demo.kz"
STUDENT_EMAILS = ("student1@demo.kz", "student2@demo.kz", "student3@demo.kz")
GROUP = "БИС 31с"


def seed_demo(c: Container, today: Optional[date] = None) -> Dict:
    """Создаёт преподавателя, трёх студентов, две дисциплины и пять работ в разных статусах.

    Повторный вызов ничего не меняет и возвращает {"created": False}.
    """
    today = today or date.today()
    try:
        teacher = c.auth.register(TEACHER_EMAIL, DEMO_PASSWORD, "Преподаватель П.П.",
                                  Role.TEACHER)
    except ConflictError:
        return {"created": False}
    students = [c.auth.register(email, DEMO_PASSWORD, name, Role.STUDENT, GROUP)
                for email, name in zip(STUDENT_EMAILS, ("Алиев А.А.", "Иванов И.И.",
                                                        "Сидоров С.С."))]
    tr = c.subjects.create(teacher, "Технологии разработки ПО", GROUP)
    db = c.subjects.create(teacher, "Базы данных", GROUP)
    plan = [(tr, "ПР1. Анализ предметной области", today + timedelta(days=-1)),
            (tr, "ПР2. Требования", today + timedelta(days=2)),
            (tr, "ПР3. UML", today + timedelta(days=10)),
            (db, "ПР1. ER-модель", today + timedelta(days=5)),
            (db, "ПР2. SQL-запросы", today + timedelta(days=14))]
    assignments = [c.assignments.create(teacher, s.id, title, "", deadline)
                   for s, title, deadline in plan]
    _advance(c, students[0], teacher, assignments[0], accept=True)
    _advance(c, students[0], teacher, assignments[1])  # сдана, ждёт проверки
    _start(c, students[0], assignments[2])
    _advance(c, students[1], teacher, assignments[0], accept=False,
             comment="Уточните границы проекта")
    _start(c, students[1], assignments[3])
    c.commit()
    return {"created": True, "teacher": TEACHER_EMAIL, "students": list(STUDENT_EMAILS),
            "password": DEMO_PASSWORD, "assignments": len(assignments)}


def _submission_id(c: Container, student, assignment) -> int:
    rows = c.submissions.list_for_student(student)
    return next(r["id"] for r in rows if r["assignment_id"] == assignment.id)


def _start(c: Container, student, assignment) -> int:
    sid = _submission_id(c, student, assignment)
    c.submissions.change_status_by_student(student, sid, Status.IN_PROGRESS)
    return sid


def _advance(c: Container, student, teacher, assignment, accept=None, comment="") -> None:
    sid = _start(c, student, assignment)
    c.submissions.change_status_by_student(student, sid, Status.SUBMITTED)
    if accept is not None:
        c.submissions.review(teacher, sid, accept, comment)
