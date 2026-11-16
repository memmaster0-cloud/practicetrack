"""Прогон сценария Postman через сервисы (без HTTP): порядок шагов и коды ответа."""
import sys
from datetime import date

sys.path.insert(0, ".")
from app.api.errors import status_for  # noqa: E402
from app.container import build_memory_container  # noqa: E402
from app.domain import Role, Status  # noqa: E402

c = build_memory_container(clock=lambda: date(2026, 11, 9))
rows = []
PASSWORD = "secret123"
by_student = c.submissions.change_status_by_student


def step(name, expected, fn):
    try:
        result = fn()
        code = expected if expected < 300 else 200  # успех: без исключения
    except Exception as exc:
        code = status_for(exc)  # ошибка: исключение отображается в HTTP-код
        result = None
    rows.append((name, expected, code, "OK" if code == expected else "РАСХОЖДЕНИЕ"))
    return result


reg, login = c.auth.register, c.auth.login
t = step("Регистрация преподавателя", 201, lambda: reg("t@e.kz", PASSWORD, "Преп", Role.TEACHER))
s = step("Регистрация студента", 201,
         lambda: reg("s@e.kz", PASSWORD, "Студ", Role.STUDENT, "БИС 31с"))
step("Вход преподавателя", 200, lambda: login("t@e.kz", PASSWORD))
step("Вход студента", 200, lambda: login("s@e.kz", PASSWORD))
sub = step("Создать дисциплину", 201, lambda: c.subjects.create(t, "ТР ПО", "БИС 31с"))
a = step("Добавить практическую работу", 201,
         lambda: c.assignments.create(t, sub.id, "ПР1", "", date(2026, 11, 20)))
step("Изменить работу", 200,
     lambda: c.assignments.update(t, a.id, deadline=date(2026, 12, 5)))
step("Сдачи группы по работе", 200, lambda: c.submissions.list_for_assignment(t, a.id))
lst = step("Мои работы", 200, lambda: c.submissions.list_for_student(s))
sid = lst[0]["id"]
step("Мои работы с фильтром", 200,
     lambda: c.submissions.list_for_student(s, status=Status.NOT_STARTED))
step("Прогресс", 200, lambda: c.submissions.progress(s))
step("Начать работу", 200, lambda: by_student(s, sid, Status.IN_PROGRESS))
step("Сдать работу", 200, lambda: by_student(s, sid, Status.SUBMITTED))
step("Вернуть на доработку", 200,
     lambda: c.submissions.review(t, sid, False, "Уточнить границы проекта"))
step("Студент пересдаёт", 200, lambda: by_student(s, sid, Status.SUBMITTED))
step("Принять работу", 200, lambda: c.submissions.review(t, sid, True))
step("Отчёт о задолженностях", 200, lambda: c.submissions.debtors_report(t, sub.id))
step("Студент создаёт дисциплину: 403", 403, lambda: c.subjects.create(s, "X", "Г"))
step("Повторная регистрация: 409", 409,
     lambda: reg("t@e.kz", PASSWORD, "Дубль", Role.TEACHER))
step("Короткий пароль: 422", 422, lambda: reg("x@e.kz", "short", "Х", Role.TEACHER))
step("Неверный пароль: 401", 401, lambda: login("s@e.kz", "wrong-password"))
step("Недопустимый переход статуса: 422", 422,
     lambda: by_student(s, sid, Status.IN_PROGRESS))
step("Несуществующая сдача: 404", 404, lambda: by_student(s, 999999, Status.IN_PROGRESS))
step("Удалить работу: 204", 204, lambda: c.assignments.delete(t, a.id))
step("Удалить повторно: 404", 404, lambda: c.assignments.delete(t, a.id))

for r in rows:
    print(f"{r[0]:42} ожидается {r[1]}  получено {r[2]}  {r[3]}")
bad = [r for r in rows if r[3] != "OK"]
print(f"\nШагов: {len(rows)}, совпало: {len(rows) - len(bad)}, расхождений: {len(bad)}")
sys.exit(1 if bad else 0)
