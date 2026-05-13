from __future__ import annotations

import base64
import hashlib
import hmac
import os


class PasswordHasher:
    def __init__(self, iterations: int = 200_000) -> None:
        if iterations < 100_000:
            raise ValueError("iterations must be at least 100000")
        self.iterations = iterations

    def hash_password(self, password: str, *, salt: bytes | None = None) -> str:
        if len(password) < 12:
            raise ValueError("password must be at least 12 characters")
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
        return ".".join(
            [
                "pbkdf2_sha256",
                str(self.iterations),
                base64.urlsafe_b64encode(salt).decode("ascii"),
                base64.urlsafe_b64encode(digest).decode("ascii"),
            ]
        )

    def verify(self, password: str, encoded_hash: str) -> bool:
        try:
            algorithm, iterations, salt_b64, digest_b64 = encoded_hash.split(".", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(expected, actual)
        except (ValueError, TypeError):
            return False


def constant_time_token_match(expected: str, actual: str) -> bool:
    return hmac.compare_digest(expected.encode("utf-8"), actual.encode("utf-8"))
