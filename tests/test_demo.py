import unittest
from datetime import date

from app.container import build_memory_container
from app.demo import DEMO_PASSWORD, STUDENT_EMAILS, TEACHER_EMAIL, seed_demo

TODAY = date(2026, 11, 20)


class DemoSeedTests(unittest.TestCase):
    def setUp(self):
        self.c = build_memory_container(clock=lambda: TODAY)
        self.result = seed_demo(self.c, today=TODAY)

    def login_student(self, i):
        token = self.c.auth.login(STUDENT_EMAILS[i], DEMO_PASSWORD)
        return self.c.auth.current_user(token)

    def test_creates_expected_data(self):
        self.assertTrue(self.result["created"])
        teacher = self.c.auth.current_user(self.c.auth.login(TEACHER_EMAIL, DEMO_PASSWORD))
        self.assertEqual(len(self.c.subjects.list_for_teacher(teacher)), 2)
        self.assertEqual(len(self.c.submissions.list_for_student(self.login_student(0))), 5)

    def test_statuses_cover_the_whole_cycle(self):
        statuses = {r["title"]: r["status"] for r in
                    self.c.submissions.list_for_student(self.login_student(0))}
        self.assertEqual(statuses["ПР1. Анализ предметной области"], "accepted")
        self.assertEqual(statuses["ПР2. Требования"], "submitted")
        self.assertEqual(statuses["ПР3. UML"], "in_progress")
        rework = next(r for r in self.c.submissions.list_for_student(self.login_student(1))
                      if r["status"] == "rework")
        self.assertEqual(rework["comment"], "Уточните границы проекта")

    def test_deadlines_show_flags(self):
        flags = {r["title"]: r["flag"] for r in
                 self.c.submissions.list_for_student(self.login_student(2))}
        self.assertEqual(flags["ПР1. Анализ предметной области"], "overdue")
        self.assertEqual(flags["ПР2. Требования"], "near")
        self.assertEqual(flags["ПР3. UML"], "")

    def test_progress_for_demo_students(self):
        self.assertEqual(self.c.submissions.progress(self.login_student(0))["percent"], 20)
        self.assertEqual(self.c.submissions.progress(self.login_student(2))["percent"], 0)

    def test_second_call_changes_nothing(self):
        self.assertEqual(seed_demo(self.c, today=TODAY), {"created": False})
        self.assertEqual(len(self.c.submissions.list_for_student(self.login_student(0))), 5)


if __name__ == "__main__":
    unittest.main()
