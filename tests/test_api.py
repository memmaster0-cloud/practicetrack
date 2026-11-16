"""Тесты REST API через TestClient. Пропускаются, если fastapi/httpx не установлены."""
import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("fastapi или httpx не установлены")

from app.api.factory import create_app
from app.api.routes import get_container
from app.container import build_memory_container
from tests.helpers import TODAY

PASSWORD = "secret123"


def make_client():
    container = build_memory_container(clock=lambda: TODAY)
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    return TestClient(app)


def register(client, email, role, name, group=None):
    body = {"email": email, "password": PASSWORD, "full_name": name, "role": role}
    if group:
        body["group"] = group
    return client.post("/api/auth/register", json=body)


def auth_header(client, email):
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


class ApiFlowBase(unittest.TestCase):
    def setUp(self):
        self.client = make_client()
        register(self.client, "t@example.kz", "teacher", "Преподаватель П.")
        register(self.client, "s@example.kz", "student", "Студент С.", "БИС 31с")
        self.t = auth_header(self.client, "t@example.kz")
        self.s = auth_header(self.client, "s@example.kz")

    def make_assignment(self, deadline="2026-11-20"):
        subject = self.client.post("/api/subjects", headers=self.t,
                                   json={"name": "ТР ПО", "group": "БИС 31с"}).json()
        a = self.client.post(f"/api/subjects/{subject['id']}/assignments", headers=self.t,
                             json={"title": "ПР1", "description": "Анализ",
                                   "deadline": deadline}).json()
        return subject, a


class AuthApiTests(ApiFlowBase):
    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_register_returns_201_without_password(self):
        r = register(self.client, "new@example.kz", "teacher", "Новый Н.")
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("password", r.json())
        self.assertNotIn("password_hash", r.json())

    def test_register_duplicate_409(self):
        r = register(self.client, "t@example.kz", "teacher", "Дубль")
        self.assertEqual(r.status_code, 409)

    def test_register_invalid_body_422(self):
        r = self.client.post("/api/auth/register", json={"email": "a@b.kz"})
        self.assertEqual(r.status_code, 422)

    def test_register_short_password_422(self):
        r = self.client.post("/api/auth/register", json={
            "email": "x@example.kz", "password": "short", "full_name": "Х", "role": "teacher"})
        self.assertEqual(r.status_code, 422)

    def test_register_invalid_role_422(self):
        r = self.client.post("/api/auth/register", json={
            "email": "x@example.kz", "password": PASSWORD, "full_name": "Х", "role": "admin"})
        self.assertEqual(r.status_code, 422)

    def test_login_ok_and_wrong_password(self):
        ok = self.client.post("/api/auth/login",
                              json={"email": "s@example.kz", "password": PASSWORD})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["token_type"], "bearer")
        bad = self.client.post("/api/auth/login",
                               json={"email": "s@example.kz", "password": "wrong-pass"})
        self.assertEqual(bad.status_code, 401)

    def test_me_requires_token(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        r = self.client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
        self.assertEqual(r.status_code, 401)

    def test_me_returns_user(self):
        r = self.client.get("/api/auth/me", headers=self.s)
        self.assertEqual((r.status_code, r.json()["role"]), (200, "student"))


class SubjectAssignmentApiTests(ApiFlowBase):
    def test_student_cannot_create_subject_403(self):
        r = self.client.post("/api/subjects", headers=self.s,
                             json={"name": "X", "group": "БИС 31с"})
        self.assertEqual(r.status_code, 403)

    def test_create_subject_and_list(self):
        subject, _ = self.make_assignment()
        r = self.client.get("/api/subjects", headers=self.t)
        self.assertEqual([s["id"] for s in r.json()], [subject["id"]])

    def test_create_subject_empty_name_422(self):
        r = self.client.post("/api/subjects", headers=self.t, json={"name": "", "group": "Г"})
        self.assertEqual(r.status_code, 422)

    def test_create_assignment_201_and_visible_to_student(self):
        self.make_assignment()
        rows = self.client.get("/api/submissions", headers=self.s).json()
        self.assertEqual([r["title"] for r in rows], ["ПР1"])
        self.assertEqual(rows[0]["status"], "not_started")

    def test_create_assignment_bad_date_422(self):
        subject, _ = self.make_assignment()
        r = self.client.post(f"/api/subjects/{subject['id']}/assignments", headers=self.t,
                             json={"title": "ПР2", "deadline": "не дата"})
        self.assertEqual(r.status_code, 422)

    def test_create_assignment_unknown_subject_404(self):
        r = self.client.post("/api/subjects/999/assignments", headers=self.t,
                             json={"title": "ПР2", "deadline": "2026-12-01"})
        self.assertEqual(r.status_code, 404)

    def test_update_assignment(self):
        _, a = self.make_assignment()
        r = self.client.patch(f"/api/assignments/{a['id']}", headers=self.t,
                              json={"deadline": "2026-12-05"})
        self.assertEqual((r.status_code, r.json()["deadline"]), (200, "2026-12-05"))

    def test_delete_assignment_204_then_404(self):
        _, a = self.make_assignment()
        self.assertEqual(self.client.delete(f"/api/assignments/{a['id']}",
                                            headers=self.t).status_code, 204)
        self.assertEqual(self.client.delete(f"/api/assignments/{a['id']}",
                                            headers=self.t).status_code, 404)

    def test_student_cannot_delete_assignment_403(self):
        _, a = self.make_assignment()
        r = self.client.delete(f"/api/assignments/{a['id']}", headers=self.s)
        self.assertEqual(r.status_code, 403)


class SubmissionApiTests(ApiFlowBase):
    def setUp(self):
        super().setUp()
        self.subject, self.a = self.make_assignment()
        self.sub_id = self.client.get("/api/submissions", headers=self.s).json()[0]["id"]

    def set_status(self, status):
        return self.client.patch(f"/api/submissions/{self.sub_id}/status", headers=self.s,
                                 json={"status": status})

    def test_full_review_cycle(self):
        self.assertEqual(self.set_status("in_progress").status_code, 200)
        self.assertEqual(self.set_status("submitted").json()["status"], "submitted")
        r = self.client.post(f"/api/submissions/{self.sub_id}/review", headers=self.t,
                             json={"accept": False, "comment": "Уточнить границы"})
        self.assertEqual((r.status_code, r.json()["status"]), (200, "rework"))
        mine = self.client.get("/api/submissions", headers=self.s).json()[0]
        self.assertEqual(mine["comment"], "Уточнить границы")

    def test_invalid_transition_422(self):
        self.assertEqual(self.set_status("submitted").status_code, 422)

    def test_student_cannot_accept_403(self):
        self.set_status("in_progress")
        self.assertEqual(self.set_status("accepted").status_code, 403)

    def test_unknown_status_value_422(self):
        self.assertEqual(self.set_status("finished").status_code, 422)

    def test_rework_without_comment_422(self):
        self.set_status("in_progress")
        self.set_status("submitted")
        r = self.client.post(f"/api/submissions/{self.sub_id}/review", headers=self.t,
                             json={"accept": False, "comment": ""})
        self.assertEqual(r.status_code, 422)

    def test_student_cannot_review_403(self):
        r = self.client.post(f"/api/submissions/{self.sub_id}/review", headers=self.s,
                             json={"accept": True})
        self.assertEqual(r.status_code, 403)

    def test_unknown_submission_404(self):
        r = self.client.patch("/api/submissions/999/status", headers=self.s,
                              json={"status": "in_progress"})
        self.assertEqual(r.status_code, 404)

    def test_filters(self):
        r = self.client.get("/api/submissions?status=accepted", headers=self.s)
        self.assertEqual(r.json(), [])
        r = self.client.get(f"/api/submissions?subject_id={self.subject['id']}", headers=self.s)
        self.assertEqual(len(r.json()), 1)

    def test_teacher_sees_group_submissions(self):
        r = self.client.get(f"/api/assignments/{self.a['id']}/submissions", headers=self.t)
        self.assertEqual([x["student"] for x in r.json()], ["Студент С."])

    def test_debtors_report_and_progress(self):
        r = self.client.get(f"/api/subjects/{self.subject['id']}/debtors", headers=self.t)
        self.assertEqual(r.json()[0]["assignment"], "ПР1")
        p = self.client.get("/api/submissions/progress", headers=self.s).json()
        self.assertEqual(p, {"percent": 0, "total": 1, "accepted": 0})
        self.set_status("in_progress")
        self.set_status("submitted")
        self.client.post(f"/api/submissions/{self.sub_id}/review", headers=self.t,
                         json={"accept": True})
        p = self.client.get("/api/submissions/progress", headers=self.s).json()
        self.assertEqual(p["percent"], 100)

    def test_protected_routes_require_token(self):
        for method, url in [("get", "/api/submissions"), ("get", "/api/subjects"),
                            ("get", "/api/submissions/progress")]:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 401)


if __name__ == "__main__":
    unittest.main()
