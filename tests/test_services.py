import unittest
from datetime import date

from app.domain import Role, Status
from app.errors import (AuthError, ConflictError, NotFoundError, PermissionDenied,
                        ValidationError)
from tests.helpers import PASSWORD, Env


class AuthServiceTests(unittest.TestCase):  # TC-01, TC-02
    def setUp(self):
        self.env = Env()

    def test_register_student_ok(self):
        u = self.env.student()
        self.assertEqual(u.role, Role.STUDENT)
        self.assertNotEqual(u.password_hash, PASSWORD)
        self.assertIsNotNone(u.group_id)

    def test_register_normalizes_email(self):
        u = self.env.auth.register("  Mix@Example.KZ ", PASSWORD, "Имя", Role.TEACHER)
        self.assertEqual(u.email, "mix@example.kz")

    def test_register_duplicate_email(self):
        self.env.student()
        with self.assertRaises(ConflictError):
            self.env.student()

    def test_register_bad_email(self):
        with self.assertRaises(ValidationError):
            self.env.auth.register("not-email", PASSWORD, "Имя", Role.TEACHER)

    def test_register_short_password(self):
        with self.assertRaises(ValidationError):
            self.env.auth.register("a@b.kz", "short", "Имя", Role.TEACHER)

    def test_register_empty_name(self):
        with self.assertRaises(ValidationError):
            self.env.auth.register("a@b.kz", PASSWORD, "  ", Role.TEACHER)

    def test_student_needs_group(self):
        with self.assertRaises(ValidationError):
            self.env.auth.register("a@b.kz", PASSWORD, "Имя", Role.STUDENT)

    def test_login_and_current_user(self):
        u = self.env.student()
        token = self.env.auth.login("student@example.kz", PASSWORD)
        self.assertEqual(self.env.auth.current_user(token).id, u.id)

    def test_login_wrong_password(self):
        self.env.student()
        with self.assertRaises(AuthError):
            self.env.auth.login("student@example.kz", "wrong-password")

    def test_login_unknown_user(self):
        with self.assertRaises(AuthError):
            self.env.auth.login("nobody@example.kz", PASSWORD)

    def test_current_user_deleted(self):
        u = self.env.student()
        token = self.env.auth.login("student@example.kz", PASSWORD)
        del self.env.users._items[u.id]
        with self.assertRaises(AuthError):
            self.env.auth.current_user(token)


class SubjectAndAssignmentTests(unittest.TestCase):  # TC-03, TC-04, TC-05
    def setUp(self):
        self.env = Env()
        self.t, self.s, self.subject, self.a, self.sub = self.env.setup_course()

    def test_create_subject_only_teacher(self):
        with self.assertRaises(PermissionDenied):
            self.env.subject_service.create(self.s, "X", "БИС 31с")

    def test_create_subject_validation(self):
        with self.assertRaises(ValidationError):
            self.env.subject_service.create(self.t, " ", "БИС 31с")

    def test_list_subjects_for_teacher(self):
        self.assertEqual(len(self.env.subject_service.list_for_teacher(self.t)), 1)

    def test_list_subjects_student_forbidden(self):
        with self.assertRaises(PermissionDenied):
            self.env.subject_service.list_for_teacher(self.s)

    def test_assignment_creates_submission_for_each_student(self):
        self.env.student("second@example.kz", "Второй В.")
        a2 = self.env.assignment_service.create(
            self.t, self.subject.id, "ПР2", "Требования", date(2026, 11, 25))
        self.assertEqual(len(self.env.submissions.list_by_assignment(a2.id)), 2)

    def test_assignment_empty_title(self):
        with self.assertRaises(ValidationError):
            self.env.assignment_service.create(self.t, self.subject.id, " ", "", date(2026, 12, 1))

    def test_assignment_foreign_subject_forbidden(self):
        other = self.env.teacher("other@example.kz", "Другой Д.")
        with self.assertRaises(PermissionDenied):
            self.env.assignment_service.create(other, self.subject.id, "X", "", date(2026, 12, 1))

    def test_assignment_unknown_subject(self):
        with self.assertRaises(NotFoundError):
            self.env.assignment_service.create(self.t, 999, "X", "", date(2026, 12, 1))

    def test_update_assignment(self):
        upd = self.env.assignment_service.update(
            self.t, self.a.id, title="ПР1 (новое)", description="Новое", deadline=date(2026, 12, 5))
        self.assertEqual((upd.title, upd.deadline), ("ПР1 (новое)", date(2026, 12, 5)))

    def test_update_empty_title_rejected(self):
        with self.assertRaises(ValidationError):
            self.env.assignment_service.update(self.t, self.a.id, title=" ")

    def test_update_unknown_assignment(self):
        with self.assertRaises(NotFoundError):
            self.env.assignment_service.update(self.t, 999, title="X")

    def test_delete_assignment_removes_submissions(self):
        self.env.assignment_service.delete(self.t, self.a.id)
        self.assertIsNone(self.env.assignments.get(self.a.id))
        self.assertEqual(self.env.submissions.list_by_assignment(self.a.id), [])


class SubmissionServiceTests(unittest.TestCase):  # TC-06 ... TC-13
    def setUp(self):
        self.env = Env()
        self.t, self.s, self.subject, self.a, self.sub = self.env.setup_course()
        self.svc = self.env.submission_service

    def test_student_sees_own_list(self):
        rows = self.svc.list_for_student(self.s)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "not_started")
        self.assertEqual(rows[0]["days_left"], 11)

    def test_list_other_student_not_visible(self):
        other = self.env.student("o@example.kz", "Иной И.")
        rows = self.svc.list_for_student(other)
        self.assertTrue(all(r["id"] != self.sub.id for r in rows))

    def test_teacher_cannot_use_student_list(self):
        with self.assertRaises(PermissionDenied):
            self.svc.list_for_student(self.t)

    def test_filters(self):
        self.assertEqual(len(self.svc.list_for_student(self.s, subject_id=self.subject.id)), 1)
        self.assertEqual(self.svc.list_for_student(self.s, subject_id=999), [])
        self.assertEqual(len(self.svc.list_for_student(self.s, status=Status.NOT_STARTED)), 1)
        self.assertEqual(self.svc.list_for_student(self.s, status=Status.ACCEPTED), [])

    def test_list_sorted_by_deadline(self):
        self.env.assignment_service.create(
            self.t, self.subject.id, "ПР0", "", date(2026, 11, 12))
        rows = self.svc.list_for_student(self.s)
        self.assertEqual([r["title"] for r in rows], ["ПР0", "ПР1"])

    def test_near_deadline_flag_in_list(self):
        self.env.assignment_service.create(
            self.t, self.subject.id, "Срочная", "", date(2026, 11, 10))
        flags = {r["title"]: r["flag"] for r in self.svc.list_for_student(self.s)}
        self.assertEqual(flags["Срочная"], "near")
        self.assertEqual(flags["ПР1"], "")

    def test_student_start_and_submit(self):
        self.svc.change_status_by_student(self.s, self.sub.id, Status.IN_PROGRESS)
        view = self.svc.change_status_by_student(self.s, self.sub.id, Status.SUBMITTED)
        self.assertEqual(view["status"], "submitted")

    def test_observer_notified(self):
        self.svc.change_status_by_student(self.s, self.sub.id, Status.IN_PROGRESS)
        self.assertEqual(self.env.observer.events,
                         [(self.sub.id, "not_started", "in_progress")])

    def test_student_cannot_accept(self):
        self.svc.change_status_by_student(self.s, self.sub.id, Status.IN_PROGRESS)
        with self.assertRaises(PermissionDenied):
            self.svc.change_status_by_student(self.s, self.sub.id, Status.ACCEPTED)

    def test_student_invalid_transition(self):
        with self.assertRaises(ValidationError):
            self.svc.change_status_by_student(self.s, self.sub.id, Status.SUBMITTED)

    def test_student_cannot_change_foreign_submission(self):
        other = self.env.student("o@example.kz", "Иной И.")
        with self.assertRaises(PermissionDenied):
            self.svc.change_status_by_student(other, self.sub.id, Status.IN_PROGRESS)

    def test_unknown_submission(self):
        with self.assertRaises(NotFoundError):
            self.svc.change_status_by_student(self.s, 999, Status.IN_PROGRESS)

    def _submit(self):
        self.svc.change_status_by_student(self.s, self.sub.id, Status.IN_PROGRESS)
        self.svc.change_status_by_student(self.s, self.sub.id, Status.SUBMITTED)

    def test_teacher_accepts(self):
        self._submit()
        view = self.svc.review(self.t, self.sub.id, accept=True, comment="Отлично")
        self.assertEqual(view["status"], "accepted")

    def test_teacher_returns_with_comment_visible_to_student(self):
        self._submit()
        self.svc.review(self.t, self.sub.id, accept=False, comment="Уточнить границы")
        row = self.svc.list_for_student(self.s)[0]
        self.assertEqual((row["status"], row["comment"]), ("rework", "Уточнить границы"))

    def test_return_without_comment_rejected(self):
        self._submit()
        with self.assertRaises(ValidationError):
            self.svc.review(self.t, self.sub.id, accept=False, comment="")

    def test_review_not_submitted_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.review(self.t, self.sub.id, accept=True)

    def test_student_cannot_review(self):
        self._submit()
        with self.assertRaises(PermissionDenied):
            self.svc.review(self.s, self.sub.id, accept=True)

    def test_foreign_teacher_cannot_review(self):
        self._submit()
        other = self.env.teacher("other@example.kz", "Другой Д.")
        with self.assertRaises(PermissionDenied):
            self.svc.review(other, self.sub.id, accept=True)

    def test_list_for_assignment(self):
        self.env.student("b@example.kz", "Алиев А.")
        a2 = self.env.assignment_service.create(
            self.t, self.subject.id, "ПР2", "", date(2026, 12, 1))
        rows = self.svc.list_for_assignment(self.t, a2.id)
        self.assertEqual([r["student"] for r in rows], ["Алиев А.", "Студент С."])

    def test_list_for_assignment_errors(self):
        with self.assertRaises(NotFoundError):
            self.svc.list_for_assignment(self.t, 999)
        other = self.env.teacher("other@example.kz", "Другой Д.")
        with self.assertRaises(PermissionDenied):
            self.svc.list_for_assignment(other, self.a.id)

    def test_debtors_report(self):
        self._submit()
        self.svc.review(self.t, self.sub.id, accept=True)
        self.assertEqual(self.svc.debtors_report(self.t, self.subject.id), [])
        self.env.assignment_service.create(
            self.t, self.subject.id, "ПР2", "", date(2026, 12, 1))
        report = self.svc.debtors_report(self.t, self.subject.id)
        self.assertEqual(report, [{"student": "Студент С.", "assignment": "ПР2",
                                   "status": "not_started"}])

    def test_debtors_report_errors(self):
        with self.assertRaises(NotFoundError):
            self.svc.debtors_report(self.t, 999)
        other = self.env.teacher("other@example.kz", "Другой Д.")
        with self.assertRaises(PermissionDenied):
            self.svc.debtors_report(other, self.subject.id)


if __name__ == "__main__":
    unittest.main()


class LateStudentTests(unittest.TestCase):  # дефект DEF-01
    def test_student_registered_after_assignment_sees_it(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        late = env.student("late@example.kz", "Поздний П.")
        rows = env.submission_service.list_for_student(late)
        self.assertEqual([r["title"] for r in rows], ["ПР1"])

    def test_no_duplicate_submissions_on_repeated_listing(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        env.submission_service.list_for_student(s)
        env.submission_service.list_for_student(s)
        self.assertEqual(len(env.submissions.list_by_student(s.id)), 1)

    def test_subscribe_adds_observer(self):
        from app.observers import RecordingObserver
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        extra = RecordingObserver()
        env.submission_service.subscribe(extra)
        env.submission_service.change_status_by_student(s, sub.id, Status.IN_PROGRESS)
        self.assertEqual(len(extra.events), 1)


class ProgressTests(unittest.TestCase):
    def test_progress_counts_accepted(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        env.assignment_service.create(t, subject.id, "ПР2", "", date(2026, 12, 1))
        svc = env.submission_service
        self.assertEqual(svc.progress(s), {"percent": 0, "total": 2, "accepted": 0})
        svc.change_status_by_student(s, sub.id, Status.IN_PROGRESS)
        svc.change_status_by_student(s, sub.id, Status.SUBMITTED)
        view = svc.review(t, sub.id, accept=True)
        self.assertIsNotNone(view["submitted_at"])
        self.assertEqual(svc.progress(s), {"percent": 50, "total": 2, "accepted": 1})


class RefactoringTests(unittest.TestCase):  # ПР14: поведение и эффективность после рефакторинга
    def test_listing_loads_each_subject_once(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        for i in range(4):
            env.assignment_service.create(t, subject.id, f"ПР{i + 2}", "", date(2026, 12, 1 + i))
        calls = []
        original = env.subjects.get
        env.subjects.get = lambda sid: calls.append(sid) or original(sid)
        rows = env.submission_service.list_for_student(s)
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(calls), 1)

    def test_progress_does_not_build_views(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        calls = []
        original = env.assignments.get
        env.assignments.get = lambda aid: calls.append(aid) or original(aid)
        env.submission_service.progress(s)
        self.assertEqual(calls, [])

    def test_progress_requires_student_role(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        with self.assertRaises(PermissionDenied):
            env.submission_service.progress(t)

    def test_owned_subject_checks_role_existence_and_owner(self):
        from app.services import owned_subject
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        self.assertEqual(owned_subject(env.subjects, t, subject.id).id, subject.id)
        with self.assertRaises(PermissionDenied):
            owned_subject(env.subjects, s, subject.id)
        with self.assertRaises(NotFoundError):
            owned_subject(env.subjects, t, 999)
        other = env.teacher("other@example.kz", "Другой Д.")
        with self.assertRaises(PermissionDenied):
            owned_subject(env.subjects, other, subject.id)

    def test_token_ttl_default_is_shared_constant(self):
        from app.config import load_settings
        from app.security import DEFAULT_TOKEN_TTL_SECONDS
        self.assertEqual(load_settings({}).token_ttl_seconds, DEFAULT_TOKEN_TTL_SECONDS)

    def test_review_of_submission_with_missing_assignment_gives_not_found(self):
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        env.assignments.delete(a.id)  # нарушение целостности: сдача осталась без работы
        with self.assertRaises(NotFoundError):
            env.submission_service.review(t, sub.id, accept=True)
