import unittest

from app.domain import Status
from app.progress import calculate_progress, format_days_left


class CalculateProgressTests(unittest.TestCase):
    def test_empty_list_gives_zero(self):
        self.assertEqual(calculate_progress([]), 0)

    def test_all_accepted_gives_100(self):
        self.assertEqual(calculate_progress([Status.ACCEPTED, Status.ACCEPTED]), 100)

    def test_none_accepted_gives_zero(self):
        self.assertEqual(calculate_progress([Status.IN_PROGRESS, Status.SUBMITTED]), 0)

    def test_half_accepted_gives_50(self):
        self.assertEqual(calculate_progress([Status.ACCEPTED, Status.REWORK]), 50)

    def test_result_is_rounded_down(self):
        statuses = [Status.ACCEPTED, Status.NOT_STARTED, Status.NOT_STARTED]
        self.assertEqual(calculate_progress(statuses), 33)


class FormatDaysLeftTests(unittest.TestCase):
    def test_today(self):
        self.assertEqual(format_days_left(0), "сегодня")

    def test_tomorrow(self):
        self.assertEqual(format_days_left(1), "завтра")

    def test_five_days(self):
        self.assertEqual(format_days_left(5), "через 5 дней")

    def test_two_days_uses_genitive_singular(self):
        self.assertEqual(format_days_left(2), "через 2 дня")

    def test_twenty_one_days(self):
        self.assertEqual(format_days_left(21), "через 21 день")

    def test_eleven_is_exception(self):
        self.assertEqual(format_days_left(11), "через 11 дней")

    def test_overdue_one_day(self):
        self.assertEqual(format_days_left(-1), "просрочено на 1 день")

    def test_overdue_three_days(self):
        self.assertEqual(format_days_left(-3), "просрочено на 3 дня")


if __name__ == "__main__":
    unittest.main()
