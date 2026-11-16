import unittest

from app.api.errors import status_for
from app.errors import (AuthError, ConflictError, DomainError, NotFoundError,
                        PermissionDenied, ValidationError)


class StatusMappingTests(unittest.TestCase):
    def test_each_error_has_expected_http_status(self):
        cases = [(AuthError("x"), 401), (PermissionDenied("x"), 403),
                 (NotFoundError("x"), 404), (ConflictError("x"), 409),
                 (ValidationError("x"), 422), (DomainError("x"), 400)]
        for exc, code in cases:
            with self.subTest(exc=type(exc).__name__):
                self.assertEqual(status_for(exc), code)

    def test_unknown_exception_is_500(self):
        self.assertEqual(status_for(RuntimeError("boom")), 500)


if __name__ == "__main__":
    unittest.main()
