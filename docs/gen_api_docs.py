"""Генерация docs/openapi.yaml и коллекции Postman из единой таблицы эндпоинтов."""
import json
import yaml

E = [  # (метод, путь, успех, ошибки, тег, описание, тело, ответ, авторизация, query)
    ("POST", "/api/auth/register", 201,
     [409, 422], "auth", "Регистрация пользователя", "RegisterRequest", "UserOut", False, []),
    ("POST", "/api/auth/login", 200, [401, 422], "auth",
        "Вход: получение токена", "LoginRequest", "TokenOut", False, []),
    ("GET", "/api/auth/me", 200, [401], "auth", "Текущий пользователь", None, "UserOut", True, []),
    ("POST", "/api/subjects", 201, [401, 403, 422], "subjects",
        "Создать дисциплину", "SubjectCreate", "SubjectOut", True, []),
    ("GET", "/api/subjects", 200, [401, 403], "subjects",
        "Мои дисциплины (преподаватель)", None, "[SubjectOut]", True, []),
    ("POST", "/api/subjects/{subject_id}/assignments", 201, [401, 403, 404, 422], "assignments",
        "Добавить практическую работу", "AssignmentCreate", "AssignmentOut", True, []),
    ("PATCH", "/api/assignments/{assignment_id}", 200, [401, 403, 404, 422], "assignments",
        "Изменить практическую работу", "AssignmentUpdate", "AssignmentOut", True, []),
    ("DELETE", "/api/assignments/{assignment_id}", 204, [401, 403, 404],
        "assignments", "Удалить практическую работу", None, None, True, []),
    ("GET", "/api/assignments/{assignment_id}/submissions", 200, [
        401, 403, 404], "assignments", "Сдачи группы по работе (преподаватель)", None, "[SubmissionRowOut]", True, []),
    ("GET", "/api/subjects/{subject_id}/debtors", 200, [401, 403, 404], "reports",
        "Отчёт о задолженностях (преподаватель)", None, "[DebtorOut]", True, []),
    ("GET", "/api/submissions", 200, [401, 403, 422], "submissions",
        "Мои работы (студент) с фильтрами", None, "[SubmissionOut]", True, ["subject_id", "status"]),
    ("GET", "/api/submissions/progress", 200,
        [401, 403], "submissions", "Прогресс студента: процент принятых работ", None, "ProgressOut", True, []),
    ("PATCH", "/api/submissions/{submission_id}/status", 200, [401, 403, 404, 422], "submissions",
        "Студент: начать работу или сдать её", "StatusChange", "SubmissionOut", True, []),
    ("POST", "/api/submissions/{submission_id}/review", 200, [401, 403, 404, 422], "submissions",
        "Преподаватель: принять или вернуть на доработку", "ReviewRequest", "SubmissionOut", True, []),
]
ERR = {400: "Некорректный запрос", 401: "Не авторизован или недействительный токен", 403: "Недостаточно прав",
       404: "Объект не найден", 409: "Конфликт данных (например, email уже занят)",
       422: "Ошибка валидации данных или недопустимое действие"}
OK = {200: "Успешно", 201: "Создано", 204: "Удалено, тело ответа пустое"}
STR, INT = {"type": "string"}, {"type": "integer"}
ROLE = {"type": "string", "enum": ["student", "teacher"]}
STATUS = {"type": "string", "enum": ["not_started",
                                     "in_progress", "submitted", "rework", "accepted"]}
S = {
    "RegisterRequest": {"required": ["email", "password", "full_name", "role"], "properties": {"email": {"type": "string", "minLength": 3, "maxLength": 255, "example": "student@example.kz"}, "password": {"type": "string", "minLength": 8, "maxLength": 128, "example": "secret123"}, "full_name": {"type": "string", "minLength": 1, "maxLength": 255}, "role": ROLE, "group": {"type": "string", "maxLength": 100, "nullable": True, "example": "БИС 31с"}}},
    "LoginRequest": {"required": ["email", "password"], "properties": {"email": STR, "password": STR}},
    "TokenOut": {"required": ["access_token"], "properties": {"access_token": STR, "token_type": {"type": "string", "default": "bearer"}}},
    "UserOut": {"required": ["id", "email", "full_name", "role"], "properties": {"id": INT, "email": STR, "full_name": STR, "role": ROLE, "group_id": {"type": "integer", "nullable": True}}},
    "SubjectCreate": {"required": ["name", "group"], "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 200}, "group": {"type": "string", "minLength": 1, "maxLength": 100}}},
    "SubjectOut": {"required": ["id", "name", "group_id"], "properties": {"id": INT, "name": STR, "group_id": INT}},
    "AssignmentCreate": {"required": ["title", "deadline"], "properties": {"title": {"type": "string", "minLength": 1, "maxLength": 200}, "description": {"type": "string", "default": "", "maxLength": 5000}, "deadline": {"type": "string", "format": "date", "example": "2026-11-20"}}},
    "AssignmentUpdate": {"properties": {"title": {"type": "string", "minLength": 1, "maxLength": 200, "nullable": True}, "description": {"type": "string", "maxLength": 5000, "nullable": True}, "deadline": {"type": "string", "format": "date", "nullable": True}}},
    "AssignmentOut": {"required": ["id", "subject_id", "title", "description", "deadline"], "properties": {"id": INT, "subject_id": INT, "title": STR, "description": STR, "deadline": {"type": "string", "format": "date"}}},
    "StatusChange": {"required": ["status"], "properties": {"status": STATUS}},
    "ReviewRequest": {"required": ["accept"], "properties": {"accept": {"type": "boolean"}, "comment": {"type": "string", "default": "", "maxLength": 2000}}},
    "SubmissionOut": {"required": ["id", "assignment_id", "title", "subject_id", "subject", "deadline", "status", "comment", "days_left", "flag"], "properties": {"id": INT, "assignment_id": INT, "title": STR, "subject_id": INT, "subject": STR, "deadline": STR, "status": STATUS, "comment": STR, "submitted_at": {"type": "string", "nullable": True}, "days_left": INT, "flag": {"type": "string", "description": "near, overdue или пустая строка"}}},
    "SubmissionRowOut": {"required": ["submission_id", "student", "status", "comment"], "properties": {"submission_id": INT, "student": STR, "status": STATUS, "comment": STR}},
    "DebtorOut": {"required": ["student", "assignment", "status"], "properties": {"student": STR, "assignment": STR, "status": STATUS}},
    "ProgressOut": {"required": ["percent", "total", "accepted"], "properties": {"percent": INT, "total": INT, "accepted": INT}},
}
for v in S.values():
    v["type"] = "object"
S["Error"] = {"type": "object", "required": ["detail"], "properties": {"detail": {"oneOf": [STR, {"type": "array", "items": {
    "type": "object"}}], "description": "Строка для ошибок логики; массив для ошибок формата тела запроса"}}}


def ref(name):
    if name.startswith("["):
        return {"type": "array", "items": {"$ref": "#/components/schemas/" + name[1:-1]}}
    return {"$ref": "#/components/schemas/" + name}


def build_openapi():
    paths = {}
    for m, path, ok, errs, tag, summ, body, resp, auth, query in E:
        op = {"tags": [tag], "summary": summ}
        params = [{"name": n, "in": "path", "required": True, "schema": INT} for n in
                  [p[1:-1] for p in path.split("/") if p.startswith("{")]]
        for q in query:
            params.append({"name": q, "in": "query", "required": False,
                          "schema": STATUS if q == "status" else INT})
        if params:
            op["parameters"] = params
        if body:
            op["requestBody"] = {"required": True, "content": {
                "application/json": {"schema": ref(body)}}}
        r = {str(ok): {"description": OK[ok]}}
        if resp:
            r[str(ok)]["content"] = {"application/json": {"schema": ref(resp)}}
        for code in errs:
            r[str(code)] = {"description": ERR[code], "content": {
                "application/json": {"schema": ref("Error")}}}
        op["responses"] = r
        if auth:
            op["security"] = [{"bearerAuth": []}]
        paths.setdefault(path, {})[m.lower()] = op
    paths["/health"] = {"get": {"tags": ["service"], "summary": "Проверка работоспособности",
                                "responses": {"200": {"description": "Сервис работает"}}}}
    return {"openapi": "3.0.3", "info": {"title": "ПрактикаТрек API", "version": "1.0.0", "description": "REST API учёта сдачи практических работ."},
            "servers": [{"url": "http://localhost:8000"}], "paths": paths,
            "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}, "schemas": S}}


def js(*lines): return {"listen": "test",
                        "script": {"type": "text/javascript", "exec": list(lines)}}


def status_test(code): return js(
    f'pm.test("Статус {code}", function () {{ pm.response.to.have.status({code}); }});')


def req(name, method, url, body=None, token=None, tests=None, pre=None):
    item = {"name": name, "request": {"method": method, "header": [], "url": {"raw": "{{baseUrl}}" +
                                                                              url, "host": ["{{baseUrl}}"], "path": [p for p in url.strip("/").split("/")]}}, "event": []}
    if body is not None:
        item["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
        item["request"]["body"] = {"mode": "raw",
                                   "raw": json.dumps(body, ensure_ascii=False, indent=2)}
    if token:
        item["request"]["auth"] = {"type": "bearer", "bearer": [
            {"key": "token", "value": "{{" + token + "}}", "type": "string"}]}
    if pre:
        item["event"].append({"listen": "prerequest", "script": {
                             "type": "text/javascript", "exec": pre}})
    if tests:
        item["event"].append(tests)
    return item


def build_postman():
    def save(var, code, expr): return js(
        f'pm.test("Статус {code}", function () {{ pm.response.to.have.status({code}); }});', f'pm.collectionVariables.set("{var}", {expr});')
    t, s = "teacherToken", "studentToken"
    groups = [
        ("1. Аутентификация", [
            req("Регистрация преподавателя", "POST", "/api/auth/register", {"email": "teacher{{runId}}@example.kz", "password": "secret123",
                                                                            "full_name": "Преподаватель П.", "role": "teacher"}, tests=status_test(201), pre=['pm.collectionVariables.set("runId", Date.now());']),
            req("Регистрация студента", "POST", "/api/auth/register", {"email": "student{{runId}}@example.kz",
                                                                       "password": "secret123", "full_name": "Студент С.", "role": "student", "group": "БИС 31с"}, tests=status_test(201)),
            req("Вход преподавателя", "POST", "/api/auth/login", {"email": "teacher{{runId}}@example.kz",
                                                                  "password": "secret123"}, tests=save("teacherToken", 200, "pm.response.json().access_token")),
            req("Вход студента", "POST", "/api/auth/login", {"email": "student{{runId}}@example.kz",
                                                             "password": "secret123"}, tests=save("studentToken", 200, "pm.response.json().access_token")),
            req("Текущий пользователь", "GET", "/api/auth/me", token=s,
                tests=js('pm.test("Статус 200 и роль student", function () { pm.response.to.have.status(200); pm.expect(pm.response.json().role).to.eql("student"); });')),
        ]),
        ("2. Преподаватель: дисциплины и работы", [
            req("Создать дисциплину", "POST", "/api/subjects", {"name": "Технологии разработки ПО",
                                                                "group": "БИС 31с"}, token=t, tests=save("subjectId", 201, "pm.response.json().id")),
            req("Мои дисциплины", "GET", "/api/subjects", token=t, tests=status_test(200)),
            req("Добавить практическую работу", "POST", "/api/subjects/{{subjectId}}/assignments", {
                "title": "ПР1", "description": "Анализ предметной области", "deadline": "2026-11-20"}, token=t, tests=save("assignmentId", 201, "pm.response.json().id")),
            req("Изменить работу", "PATCH", "/api/assignments/{{assignmentId}}", {"deadline": "2026-12-05"}, token=t, tests=js(
                'pm.test("Срок изменён", function () { pm.response.to.have.status(200); pm.expect(pm.response.json().deadline).to.eql("2026-12-05"); });')),
            req("Сдачи группы по работе", "GET",
                "/api/assignments/{{assignmentId}}/submissions", token=t, tests=status_test(200)),
        ]),
        ("3. Студент: работа над заданием", [
            req("Мои работы", "GET", "/api/submissions", token=s,
                tests=save("submissionId", 200, "pm.response.json()[0].id")),
            req("Мои работы с фильтром", "GET", "/api/submissions?status=not_started",
                token=s, tests=status_test(200)),
            req("Прогресс", "GET", "/api/submissions/progress", token=s, tests=status_test(200)),
            req("Начать работу", "PATCH", "/api/submissions/{{submissionId}}/status", {
                "status": "in_progress"}, token=s, tests=status_test(200)),
            req("Сдать работу", "PATCH", "/api/submissions/{{submissionId}}/status", {
                "status": "submitted"}, token=s, tests=status_test(200)),
        ]),
        ("4. Преподаватель: проверка", [
            req("Вернуть на доработку", "POST", "/api/submissions/{{submissionId}}/review", {
                "accept": False, "comment": "Уточнить границы проекта"}, token=t, tests=status_test(200)),
            req("Студент пересдаёт", "PATCH", "/api/submissions/{{submissionId}}/status", {
                "status": "submitted"}, token=s, tests=status_test(200)),
            req("Принять работу", "POST",
                "/api/submissions/{{submissionId}}/review", {"accept": True}, token=t, tests=status_test(200)),
            req("Отчёт о задолженностях", "GET",
                "/api/subjects/{{subjectId}}/debtors", token=t, tests=status_test(200)),
        ]),
        ("5. Негативные проверки", [
            req("Без токена: 401", "GET", "/api/submissions", tests=status_test(401)),
            req("Неверный пароль: 401", "POST", "/api/auth/login",
                {"email": "student{{runId}}@example.kz", "password": "wrong-password"}, tests=status_test(401)),
            req("Студент создаёт дисциплину: 403", "POST", "/api/subjects",
                {"name": "X", "group": "Г"}, token=s, tests=status_test(403)),
            req("Повторная регистрация: 409", "POST", "/api/auth/register",
                {"email": "teacher{{runId}}@example.kz", "password": "secret123", "full_name": "Дубль", "role": "teacher"}, tests=status_test(409)),
            req("Короткий пароль: 422", "POST", "/api/auth/register",
                {"email": "x@example.kz", "password": "short", "full_name": "Х", "role": "teacher"}, tests=status_test(422)),
            req("Недопустимый переход статуса: 422", "PATCH",
                "/api/submissions/{{submissionId}}/status", {"status": "in_progress"}, token=s, tests=status_test(422)),
            req("Несуществующая сдача: 404", "PATCH", "/api/submissions/999999/status",
                {"status": "in_progress"}, token=s, tests=status_test(404)),
            req("Удалить работу: 204", "DELETE",
                "/api/assignments/{{assignmentId}}", token=t, tests=status_test(204)),
            req("Удалить повторно: 404", "DELETE",
                "/api/assignments/{{assignmentId}}", token=t, tests=status_test(404)),
        ]),
    ]
    return {"info": {"name": "ПрактикаТрек API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json", "description": "Запускать папки по порядку (Collection Runner). Перед запуском стартуйте приложение на {{baseUrl}}."},
            "variable": [{"key": "baseUrl", "value": "http://localhost:8000"}] + [{"key": k, "value": ""} for k in ("runId", "teacherToken", "studentToken", "subjectId", "assignmentId", "submissionId")],
            "item": [{"name": n, "item": items} for n, items in groups]}


if __name__ == "__main__":
    with open("docs/openapi.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(build_openapi(), f, allow_unicode=True, sort_keys=False, width=100)
    with open("docs/practicetrack.postman_collection.json", "w", encoding="utf-8") as f:
        json.dump(build_postman(), f, ensure_ascii=False, indent=2)
    print("docs/openapi.yaml и docs/practicetrack.postman_collection.json созданы")
