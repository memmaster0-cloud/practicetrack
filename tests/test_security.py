import unittest

from app.errors import AuthError
from app.security import (create_token, decode_token, hash_password,
                          verify_password)


class PasswordTests(unittest.TestCase):
    def test_hash_is_not_plain_password(self):
        self.assertNotIn("secret123", hash_password("secret123"))

    def test_same_password_gives_different_hashes(self):
        self.assertNotEqual(hash_password("secret123"), hash_password("secret123"))

    def test_verify_correct_and_wrong(self):
        stored = hash_password("secret123")
        self.assertTrue(verify_password("secret123", stored))
        self.assertFalse(verify_password("other", stored))

    def test_verify_broken_hash_returns_false(self):
        self.assertFalse(verify_password("x", "not-a-hash"))


class TokenTests(unittest.TestCase):
    def test_roundtrip(self):
        token = create_token(7, "teacher", "s")
        self.assertEqual(decode_token(token, "s"), (7, "teacher"))

    def test_wrong_secret_rejected(self):
        with self.assertRaises(AuthError):
            decode_token(create_token(1, "student", "s"), "other")

    def test_expired_rejected(self):
        token = create_token(1, "student", "s", ttl_seconds=-1)
        with self.assertRaises(AuthError):
            decode_token(token, "s")

    def test_garbage_rejected(self):
        with self.assertRaises(AuthError):
            decode_token("abc.def.ghi", "s")


if __name__ == "__main__":
    unittest.main()
