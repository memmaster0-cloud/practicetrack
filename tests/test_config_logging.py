import io
import logging
import unittest
from contextlib import redirect_stdout

from app.config import DEV_SECRET, load_settings
from app.errors import ValidationError
from app.logging_config import configure_logging
from app.observers import LoggingObserver
from tests.helpers import Env


class SettingsTests(unittest.TestCase):
    def test_defaults_for_development(self):
        s = load_settings({})
        self.assertEqual((s.app_env, s.log_level, s.port), ("development", "INFO", 8000))
        self.assertEqual(s.secret_key, DEV_SECRET)
        self.assertTrue(s.database_url.startswith("sqlite"))

    def test_values_from_environment(self):
        s = load_settings({"DATABASE_URL": "postgresql://u:p@db/x", "SECRET_KEY": "k",
                           "LOG_LEVEL": "debug", "PORT": "9000", "TOKEN_TTL_SECONDS": "60"})
        self.assertEqual((s.log_level, s.port, s.token_ttl_seconds), ("DEBUG", 9000, 60))
        self.assertEqual(s.database_url, "postgresql://u:p@db/x")

    def test_production_requires_secret(self):
        with self.assertRaises(ValidationError):
            load_settings({"APP_ENV": "production"})
        with self.assertRaises(ValidationError):
            load_settings({"APP_ENV": "production", "SECRET_KEY": DEV_SECRET})

    def test_production_with_secret_ok(self):
        s = load_settings({"APP_ENV": "production", "SECRET_KEY": "long-random"})
        self.assertEqual(s.app_env, "production")

    def test_invalid_log_level(self):
        with self.assertRaises(ValidationError):
            load_settings({"LOG_LEVEL": "LOUD"})

    def test_invalid_number(self):
        with self.assertRaises(ValidationError):
            load_settings({"PORT": "abc"})

    def test_nonpositive_token_ttl_rejected(self):
        for ttl in ("0", "-1"):
            with self.subTest(ttl=ttl), self.assertRaises(ValidationError):
                load_settings({"TOKEN_TTL_SECONDS": ttl})

    def test_port_outside_tcp_range_rejected(self):
        for port in ("0", "-1", "65536"):
            with self.subTest(port=port), self.assertRaises(ValidationError):
                load_settings({"PORT": port})

    def test_valid_numeric_boundaries(self):
        for port in ("1", "65535"):
            settings = load_settings({"PORT": port, "TOKEN_TTL_SECONDS": "1"})
            self.assertEqual(settings.port, int(port))
            self.assertEqual(settings.token_ttl_seconds, 1)

    def test_uses_os_environ_by_default(self):
        self.assertEqual(load_settings().app_env in ("development", "production", "test"), True)


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self._reset()
        self.addCleanup(self._reset)

    @staticmethod
    def _reset():
        """Убирает обработчик, чтобы каждый тест создавал его заново со своим stdout."""
        logger = logging.getLogger("practicetrack")
        for h in list(logger.handlers):
            logger.removeHandler(h)

    def test_writes_to_stdout_without_duplicates(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            logger = configure_logging("INFO")
            logger = configure_logging("INFO")
            logger.info("проверка")
        self.assertEqual(buf.getvalue().count("проверка"), 1)
        self.assertIn("INFO practicetrack: проверка", buf.getvalue())
        self.assertEqual(len([h for h in logger.handlers
                              if h.get_name() == "practicetrack-stdout"]), 1)

    def test_level_filters_messages(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            logger = configure_logging("WARNING")
            logger.info("тихо")
            logger.warning("громко")
        self.assertNotIn("тихо", buf.getvalue())
        self.assertIn("громко", buf.getvalue())

    def test_auth_events_logged_without_password(self):
        env = Env()
        with self.assertLogs("practicetrack.auth", level="INFO") as cm:
            env.student()
            env.auth.login("student@example.kz", "secret123")
            try:
                env.auth.login("student@example.kz", "wrong-password")
            except Exception:
                pass
        text = "\n".join(cm.output)
        self.assertIn("registered user", text)
        self.assertIn("failed login attempt", text)
        self.assertNotIn("secret123", text)
        self.assertNotIn("wrong-password", text)

    def test_logging_observer_records_status_change(self):
        from app.domain import Status
        env = Env()
        t, s, subject, a, sub = env.setup_course()
        env.submission_service.subscribe(LoggingObserver())
        with self.assertLogs("practicetrack.submissions", level="INFO") as cm:
            env.submission_service.change_status_by_student(s, sub.id, Status.IN_PROGRESS)
        self.assertIn("not_started -> in_progress", cm.output[0])


if __name__ == "__main__":
    unittest.main()
