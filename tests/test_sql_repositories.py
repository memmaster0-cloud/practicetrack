"""Проверка сервисов на реальных SQL-репозиториях (SQLite в памяти). Пропускается без SQLAlchemy."""
import unittest
from datetime import date

try:
    from sqlalchemy.pool import StaticPool
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("sqlalchemy не установлен")

from app.container import build_sql_container
from app.db.models import Base
from app.domain import Role, Status
from app.errors import ConflictError


class SqlFlowTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        self.session = sessionmaker(bind=engine, expire_on_commit=False)()
        self.c = build_sql_container(self.session, "secret", 3600,
                                     clock=lambda: date(2026, 11, 9))
        self.addCleanup(engine.dispose)
        self.addCleanup(self.session.close)

    def test_full_cycle_on_sql(self):
        t = self.c.auth.register("t@example.kz", "secret123", "Преп", Role.TEACHER)
        s = self.c.auth.register("s@example.kz", "secret123", "Студ", Role.STUDENT, "БИС 31с")
        subject = self.c.subjects.create(t, "ТР ПО", "БИС 31с")
        a = self.c.assignments.create(t, subject.id, "ПР1", "", date(2026, 11, 20))
        self.c.commit()
        rows = self.c.submissions.list_for_student(s)
        self.assertEqual([r["title"] for r in rows], ["ПР1"])
        self.c.submissions.change_status_by_student(s, rows[0]["id"], Status.IN_PROGRESS)
        self.c.submissions.change_status_by_student(s, rows[0]["id"], Status.SUBMITTED)
        view = self.c.submissions.review(t, rows[0]["id"], accept=True)
        self.c.commit()
        self.assertEqual(view["status"], "accepted")
        self.assertIsNotNone(view["submitted_at"])
        self.assertEqual(self.c.submissions.progress(s)["percent"], 100)
        self.c.assignments.delete(t, a.id)
        self.assertEqual(self.c.submissions.list_for_student(s), [])

    def test_late_student_gets_submissions_on_sql(self):
        t = self.c.auth.register("t@example.kz", "secret123", "Преп", Role.TEACHER)
        subject = self.c.subjects.create(t, "ТР ПО", "БИС 31с")
        self.c.assignments.create(t, subject.id, "ПР1", "", date(2026, 11, 20))
        late = self.c.auth.register("l@example.kz", "secret123", "Поздний", Role.STUDENT,
                                    "БИС 31с")
        self.assertEqual(len(self.c.submissions.list_for_student(late)), 1)

    def test_duplicate_email_detected(self):
        self.c.auth.register("t@example.kz", "secret123", "Преп", Role.TEACHER)
        with self.assertRaises(ConflictError):
            self.c.auth.register("t@example.kz", "secret123", "Преп", Role.TEACHER)


if __name__ == "__main__":
    unittest.main()
