"""Exercise the actual app entrypoint and SQL transactions without a network server."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory() as folder:
        os.environ["DATABASE_URL"] = "sqlite:///" + (Path(folder) / "smoke.db").as_posix()
        os.environ["SECRET_KEY"] = "local-smoke-key-with-more-than-32-bytes"
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                                cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
        from fastapi.testclient import TestClient
        from app.main import app, _engine
        records = []

        def request(client, method, path, expected, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.status_code == expected, (path, response.status_code, response.text)
            body = response.json() if "application/json" in response.headers.get(
                "content-type", "") else None
            safe = ({k: v for k, v in body.items() if k not in ("access_token", "password_hash")}
                    if isinstance(body, dict) else body)
            records.append({"method": method, "path": path, "status": expected, "body": safe})
            return body

        try:
            with TestClient(app) as client:
                request(client, "GET", "/health", 200)
                assert client.get("/docs").status_code == 200
                for role, email in [("teacher", "t@smoke.kz"), ("student", "s@smoke.kz")]:
                    request(client, "POST", "/api/auth/register", 201, json={
                        "email": email, "password": "smoke-pass-123", "full_name": role,
                        "role": role, "group": "Smoke group"})
                headers = {}
                for role, email in [("teacher", "t@smoke.kz"), ("student", "s@smoke.kz")]:
                    token = request(client, "POST", "/api/auth/login", 200,
                                    json={"email": email, "password": "smoke-pass-123"})
                    headers[role] = {"Authorization": "Bearer " + token["access_token"]}
                teacher, student = headers["teacher"], headers["student"]
                subject = request(client, "POST", "/api/subjects", 201, headers=teacher,
                                  json={"name": "Smoke subject", "group": "Smoke group"})
                request(client, "POST", f"/api/subjects/{subject['id']}/assignments", 201,
                        headers=teacher,
                        json={"title": "Smoke assignment", "deadline": "2026-12-01"})
                rows = request(client, "GET", "/api/submissions", 200, headers=student)
                sub_id = rows[0]["id"]
                path = f"/api/submissions/{sub_id}/status"
                request(client, "PATCH", path, 422, headers=student, json={"status": "submitted"})
                for state in ("in_progress", "submitted"):
                    request(client, "PATCH", path, 200, headers=student, json={"status": state})
                request(client, "PATCH", path, 403, headers=student, json={"status": "accepted"})
                review = f"/api/submissions/{sub_id}/review"
                request(client, "POST", review, 200, headers=teacher,
                        json={"accept": False, "comment": "Уточнить описание"})
                request(client, "PATCH", path, 200, headers=student, json={"status": "submitted"})
                request(client, "POST", review, 200, headers=teacher, json={"accept": True})
                progress = request(client, "GET", "/api/submissions/progress", 200, headers=student)
                assert progress["percent"] == 100
            with TestClient(app) as client:
                rows = request(client, "GET", "/api/submissions", 200, headers=student)
                assert rows[0]["status"] == "accepted"
        finally:
            _engine.dispose()
        output = ROOT / "delivery/evidence/sql_api_smoke.json"
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"PASS: {len(records)} HTTP requests, real app + migrated SQLite, "
              "persisted acceptance")


if __name__ == "__main__":
    main()
