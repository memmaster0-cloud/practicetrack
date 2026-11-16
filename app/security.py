"""Хэширование паролей и JWT-токены (NFR-02)."""
import hashlib
import hmac
import os
import time
from typing import Tuple

import jwt

from .errors import AuthError

ITERATIONS = 120_000
ALGORITHM = "HS256"
DEFAULT_TOKEN_TTL_SECONDS = 3600


def hash_password(password: str, salt: bytes = None) -> str:
    """Возвращает хэш пароля PBKDF2-SHA256 вместе с солью и числом итераций."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Сравнивает пароль с сохранённым хэшем; на повреждённый хэш отвечает False."""
    try:
        _, iters, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user_id: int, role: str, secret: str,
                 ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> str:
    """Создаёт подписанный JWT-токен с идентификатором и ролью."""
    now = int(time.time())
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> Tuple[int, str]:
    """Проверяет токен и возвращает (id пользователя, роль) или вызывает AuthError."""
    try:
        data = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return int(data["sub"]), data["role"]
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthError("Недействительный или просроченный токен") from exc
