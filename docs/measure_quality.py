"""Метрики поведения для сравнения до и после рефакторинга: число обращений к репозиториям."""
import sys
from datetime import date

sys.path.insert(0, ".")
from app.domain import Status  # noqa: E402
from tests.helpers import Env  # noqa: E402


class Counter:
    """Оборачивает метод репозитория и считает вызовы."""
    def __init__(self, repo, name):
        self.calls, original = 0, getattr(repo, name)

        def wrapper(*args, **kwargs):
            self.calls += 1
            return original(*args, **kwargs)
        setattr(repo, name, wrapper)


def main(n=5):
    env = Env()
    t, s, subject, a, sub = env.setup_course()
    for i in range(n - 1):
        env.assignment_service.create(t, subject.id, f"ПР{i + 2}", "", date(2026, 12, 1 + i))
    subjects_get = Counter(env.subjects, "get")
    assignments_get = Counter(env.assignments, "get")
    rows = env.submission_service.list_for_student(s)
    print(f"Список из {len(rows)} работ студента: обращений к subjects.get = {subjects_get.calls}, "
          f"assignments.get = {assignments_get.calls}")
    subjects_get.calls = assignments_get.calls = 0
    env.submission_service.progress(s)
    print(f"Прогресс по {len(rows)} работам: обращений к subjects.get = {subjects_get.calls}, "
          f"assignments.get = {assignments_get.calls}")
    sub_id = rows[0]["id"]
    env.submission_service.change_status_by_student(s, sub_id, Status.IN_PROGRESS)


if __name__ == "__main__":
    main()
