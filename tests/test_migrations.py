"""Тест миграций Alembic на SQLite. Пропускается, если alembic или sqlalchemy не установлены."""
import os
import subprocess
import sys
import tempfile
import unittest

try:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("alembic или sqlalchemy не установлены")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = {"groups", "users", "subjects", "assignments", "submissions"}


class MigrationTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.url = f"sqlite:///{self.path}"
        self._old = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = self.url
        self.cfg = Config(os.path.join(ROOT, "alembic.ini"))
        self.cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        if self._old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._old
        os.remove(self.path)

    def tables(self):
        engine = create_engine(self.url)
        try:
            return set(inspect(engine).get_table_names()) - {"alembic_version"}
        finally:
            engine.dispose()

    def columns(self, table):
        engine = create_engine(self.url)
        try:
            return {c["name"] for c in inspect(engine).get_columns(table)}
        finally:
            engine.dispose()

    def test_upgrade_creates_all_tables(self):
        command.upgrade(self.cfg, "head")
        self.assertEqual(self.tables(), TABLES)
        self.assertIn("submitted_at", self.columns("submissions"))

    def test_cli_upgrade_without_project_on_python_path(self):
        result = subprocess.run(
            [sys.executable, "-I", "-c", "from alembic.config import main; main()",
             "-c", os.path.join(ROOT, "alembic.ini"), "upgrade", "head"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tables(), TABLES)

    def test_first_revision_has_no_submitted_at(self):
        command.upgrade(self.cfg, "0001")
        self.assertNotIn("submitted_at", self.columns("submissions"))

    def test_downgrade_to_base_removes_tables(self):
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "base")
        self.assertEqual(self.tables(), set())

    def test_models_match_migrations(self):
        command.upgrade(self.cfg, "head")
        command.check(self.cfg)  # вызывает исключение, если модели и миграции расходятся


if __name__ == "__main__":
    unittest.main()
