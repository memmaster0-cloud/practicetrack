import unittest
from datetime import date, datetime

from app.domain import Status, Submission, days_left, deadline_flag
from app.errors import ValidationError


class SubmissionTransitionTests(unittest.TestCase):
    def setUp(self):
        self.sub = Submission(assignment_id=1, student_id=1)

    def test_new_submission_is_not_started(self):
        self.assertEqual(self.sub.status, Status.NOT_STARTED)

    def test_full_happy_path(self):
        self.sub.change_status(Status.IN_PROGRESS)
        self.sub.change_status(Status.SUBMITTED)
        self.sub.change_status(Status.ACCEPTED, "Хорошо")
        self.assertEqual(self.sub.status, Status.ACCEPTED)
        self.assertEqual(self.sub.comment, "Хорошо")

    def test_returns_old_status(self):
        self.assertEqual(self.sub.change_status(Status.IN_PROGRESS), Status.NOT_STARTED)

    def test_cannot_skip_in_progress(self):
        with self.assertRaises(ValidationError):
            self.sub.change_status(Status.SUBMITTED)

    def test_cannot_change_accepted(self):
        for st in (Status.IN_PROGRESS, Status.SUBMITTED, Status.ACCEPTED):
            self.sub.change_status(st)
        with self.assertRaises(ValidationError):
            self.sub.change_status(Status.IN_PROGRESS)

    def test_rework_requires_comment(self):
        self.sub.change_status(Status.IN_PROGRESS)
        self.sub.change_status(Status.SUBMITTED)
        with self.assertRaises(ValidationError):
            self.sub.change_status(Status.REWORK, "   ")
        self.assertEqual(self.sub.status, Status.SUBMITTED)

    def test_rework_then_resubmit(self):
        self.sub.change_status(Status.IN_PROGRESS)
        self.sub.change_status(Status.SUBMITTED)
        self.sub.change_status(Status.REWORK, "Исправить")
        self.sub.change_status(Status.SUBMITTED)
        self.assertEqual(self.sub.status, Status.SUBMITTED)
        self.assertEqual(self.sub.comment, "Исправить")


class SubmittedAtTests(unittest.TestCase):
    def test_set_on_submit_only(self):
        sub = Submission(assignment_id=1, student_id=1)
        sub.change_status(Status.IN_PROGRESS)
        self.assertIsNone(sub.submitted_at)
        moment = datetime(2026, 11, 10, 12, 0)
        sub.change_status(Status.SUBMITTED, now=moment)
        self.assertEqual(sub.submitted_at, moment)

    def test_default_uses_current_time(self):
        sub = Submission(assignment_id=1, student_id=1)
        sub.change_status(Status.IN_PROGRESS)
        sub.change_status(Status.SUBMITTED)
        self.assertIsInstance(sub.submitted_at, datetime)


class DeadlineTests(unittest.TestCase):
    TODAY = date(2026, 11, 9)

    def test_days_left(self):
        self.assertEqual(days_left(date(2026, 11, 12), self.TODAY), 3)

    def test_near_deadline_flag_boundary(self):
        self.assertEqual(deadline_flag(date(2026, 11, 12), self.TODAY, Status.IN_PROGRESS), "near")
        self.assertEqual(deadline_flag(date(2026, 11, 13), self.TODAY, Status.IN_PROGRESS), "")

    def test_today_is_near(self):
        self.assertEqual(deadline_flag(self.TODAY, self.TODAY, Status.NOT_STARTED), "near")

    def test_overdue_flag(self):
        flag = deadline_flag(date(2026, 11, 8), self.TODAY, Status.NOT_STARTED)
        self.assertEqual(flag, "overdue")

    def test_accepted_never_flagged(self):
        self.assertEqual(deadline_flag(date(2026, 11, 1), self.TODAY, Status.ACCEPTED), "")


if __name__ == "__main__":
    unittest.main()
