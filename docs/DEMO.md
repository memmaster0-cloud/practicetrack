# Сценарий демонстрации (3–5 минут)

Подготовка (до выступления): запустите проект (`docker compose up -d --build`), создайте
демо-данные (`docker compose exec app python scripts/seed_demo.py`), откройте
http://localhost:8000/docs. Резервный вариант: запишите видео этого сценария заранее.

| Шаг | Что делаем в Swagger UI | Что показываем и говорим |
| --- | --- | --- |
| 1 | `POST /api/auth/login`: `teacher@demo.kz` / `demo12345`, скопировать `access_token`, нажать Authorize | Вход по токену; пароли хранятся в виде хэша |
| 2 | `GET /api/subjects` | У преподавателя две дисциплины |
| 3 | `GET /api/assignments/2/submissions` | Сдачи группы по работе «ПР2. Требования»: у студента Алиев работа сдана и ждёт проверки (запомнить `submission_id`) |
| 4 | `GET /api/subjects/1/debtors` | Отчёт о задолженностях по дисциплине (FR-13) |
| 5 | `POST /api/submissions/{id}/review` с `{"accept": true}` для сдачи Алиева | Преподаватель принимает работу |
| 6 | Authorize под `student3@demo.kz`, `GET /api/submissions` | Работы студента, подсветка в поле `flag`: `overdue` у ПР1 и `near` у ПР2 (FR-11) |
| 7 | Authorize под `student1@demo.kz`, `GET /api/submissions/progress` | Принято 2 работы из 5, 40% |
| 8 | `GET /api/submissions`, найти работу «ПР3. UML» в статусе `in_progress`, затем `PATCH /api/submissions/{id}/status` с `{"status": "submitted"}` | Студент сдаёт работу |
| 9 | Тот же запрос с `{"status": "accepted"}` | Ошибка 403: студент не может принять работу (защита по ролям) |

Если что-то не запускается: `docker compose logs app`, `curl http://localhost:8000/health`,
проверьте `.env` и что порт 8000 свободен.
