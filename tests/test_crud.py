"""Тесты CRUD-операций на SQLite. Пропускаются, если SQLAlchemy не установлена."""
import os
import tempfile
import unittest
from datetime import date

try:
    from sqlalchemy.exc import IntegrityError
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("sqlalchemy не установлена")

from app.db import crud
from app.db.models import Base
from app.db.session import make_session_factory


class CrudTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine, factory = make_session_factory(f"sqlite:///{self.path}")
        Base.metadata.create_all(self.engine)
        self.db = factory()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.db.close()
        self.engine.dispose()
        os.remove(self.path)

    def seed(self):
        group = crud.create_group(self.db, "БИС 31с")
        teacher = crud.create_user(self.db, "t@e.kz", "h", "Преп", "teacher")
        student = crud.create_user(self.db, "s@e.kz", "h", "Студ", "student", group.id)
        subject = crud.create_subject(self.db, "ТР ПО", teacher.id, group.id)
        assignment = crud.create_assignment(self.db, subject.id, "ПР1", "", date(2026, 11, 20))
        submission = crud.create_submission(self.db, assignment.id, student.id)
        return group, teacher, student, subject, assignment, submission


class CreateReadTests(CrudTestCase):
    def test_create_and_read_all_entities(self):
        group, teacher, student, subject, assignment, submission = self.seed()
        self.assertEqual(crud.get_group(self.db, group.id).name, "БИС 31с")
        self.assertEqual(crud.get_group_by_name(self.db, "БИС 31с").id, group.id)
        self.assertEqual(crud.get_user_by_email(self.db, "s@e.kz").id, student.id)
        self.assertEqual([u.id for u in crud.list_students(self.db, group.id)], [student.id])
        self.assertEqual(len(crud.list_users(self.db)), 2)
        self.assertEqual([u.id for u in crud.list_users(self.db, role="teacher")], [teacher.id])
        self.assertEqual(crud.list_subjects(self.db, teacher_id=teacher.id)[0].id, subject.id)
        self.assertEqual(crud.list_assignments(self.db, subject.id)[0].title, "ПР1")
        self.assertEqual(crud.get_submission(self.db, submission.id).status, "not_started")
        self.assertEqual(len(crud.list_submissions(self.db, student_id=student.id)), 1)
        self.assertEqual(len(crud.list_submissions(self.db, assignment_id=assignment.id)), 1)

    def test_missing_objects_return_none(self):
        self.assertIsNone(crud.get_user(self.db, 999))
        self.assertIsNone(crud.get_group_by_name(self.db, "нет"))
        self.assertEqual(crud.list_groups(self.db), [])


class UpdateDeleteTests(CrudTestCase):
    def test_update_changes_fields(self):
        _, _, _, _, assignment, submission = self.seed()
        crud.update_assignment(self.db, assignment.id, title="ПР1 (новое)")
        crud.update_submission(self.db, submission.id, status="submitted", comment="ok")
        self.assertEqual(crud.get_assignment(self.db, assignment.id).title, "ПР1 (новое)")
        self.assertEqual(crud.get_submission(self.db, submission.id).status, "submitted")

    def test_update_unknown_field_rejected(self):
        group = crud.create_group(self.db, "Г")
        with self.assertRaises(ValueError):
            crud.update_group(self.db, group.id, id=5)

    def test_update_missing_returns_none(self):
        self.assertIsNone(crud.update_user(self.db, 999, full_name="X"))

    def test_delete_returns_flag(self):
        group = crud.create_group(self.db, "Г")
        self.assertTrue(crud.delete_group(self.db, group.id))
        self.assertFalse(crud.delete_group(self.db, group.id))

    def test_deleting_assignment_cascades_to_submissions(self):
        _, _, student, _, assignment, _ = self.seed()
        crud.delete_assignment(self.db, assignment.id)
        self.db.expire_all()
        self.assertEqual(crud.list_submissions(self.db, student_id=student.id), [])

    def test_bulk_delete_by_assignment(self):
        _, _, _, _, assignment, _ = self.seed()
        self.assertEqual(crud.delete_submissions_by_assignment(self.db, assignment.id), 1)


class ConstraintTests(CrudTestCase):
    def test_duplicate_email_rejected(self):
        crud.create_user(self.db, "a@e.kz", "h", "А", "teacher")
        with self.assertRaises(IntegrityError):
            crud.create_user(self.db, "a@e.kz", "h", "Б", "teacher")

    def test_invalid_role_rejected(self):
        with self.assertRaises(IntegrityError):
            crud.create_user(self.db, "a@e.kz", "h", "А", "admin")

    def test_foreign_key_enforced(self):
        with self.assertRaises(IntegrityError):
            crud.create_subject(self.db, "X", teacher_id=99, group_id=99)

    def test_second_submission_for_same_student_rejected(self):
        _, _, student, _, assignment, _ = self.seed()
        with self.assertRaises(IntegrityError):
            crud.create_submission(self.db, assignment.id, student.id)


if __name__ == "__main__":
    unittest.main()
