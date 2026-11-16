"""Run real project checks and retain their output for the practical reports."""
import json
import os
from datetime import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "delivery" / "evidence"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    checks = {
        "pytest": ["-m", "pytest", "--cov=app", "--cov-report=term-missing",
                   "--cov-report=json:delivery/evidence/coverage.json",
                   "--junitxml=delivery/evidence/junit.xml"],
        "behave": ["-m", "behave", "--no-color"],
        "sql_api_smoke": ["scripts/smoke_delivery.py"],
        "flake8": ["-m", "flake8", ".",
                   "--exclude=.venv,.git,__pycache__,delivery,alembic/versions"],
        "analysis": ["docs/analyze_code.py"],
        "dependencies": ["-m", "pip", "freeze"],
    }
    results = {}
    for name, args in checks.items():
        result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                                capture_output=True, encoding="utf-8", errors="replace")
        (OUT / f"{name}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
        results[name] = {"exit_code": result.returncode,
                         "command": "python " + " ".join(args)}
        print(name, result.returncode, flush=True)
    results["python"] = sys.version
    results["platform"] = sys.platform
    results["checked_at"] = datetime.now().astimezone().isoformat()
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    raise SystemExit(int(any(v["exit_code"] for v in results.values() if isinstance(v, dict))))


if __name__ == "__main__":
    main()
