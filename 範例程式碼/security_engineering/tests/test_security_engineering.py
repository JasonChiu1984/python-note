from __future__ import annotations

import unittest

from security_engineering.audit import AuditLog
from security_engineering.auth import PasswordHasher, constant_time_token_match
from security_engineering.policy import RolePolicy
from security_engineering.rate_limit import SlidingWindowRateLimiter
from security_engineering.supply_chain import DependencyRecord, validate_manifest
from security_engineering.validation import ValidationError, safe_error_response, validate_user_payload


class SecurityEngineeringTests(unittest.TestCase):
    def test_password_hash_verifies_and_rejects_wrong_password(self) -> None:
        hasher = PasswordHasher(iterations=120_000)
        encoded = hasher.hash_password("correct-horse-battery", salt=b"1234567890abcdef")

        self.assertTrue(hasher.verify("correct-horse-battery", encoded))
        self.assertFalse(hasher.verify("wrong-password", encoded))

    def test_policy_denies_unknown_permission_by_default(self) -> None:
        policy = RolePolicy()

        self.assertTrue(policy.can("operator", "write", "order"))
        self.assertFalse(policy.can("operator", "delete", "order"))
        self.assertFalse(policy.can("unknown", "read", "order"))

    def test_validation_and_safe_error_response(self) -> None:
        payload = validate_user_payload({"email": "operator@example.com", "role": "operator"})

        self.assertEqual(payload.role, "operator")
        with self.assertRaises(ValidationError):
            validate_user_payload({"email": "../bad", "role": "admin"})
        self.assertEqual(safe_error_response("invalid_request", "trace-1")["trace_id"], "trace-1")

    def test_audit_log_redacts_sensitive_fields(self) -> None:
        audit = AuditLog()

        event = audit.record("login.failed", "operator@example.com", "trace-2", token="secret-token")

        self.assertEqual(event["token"], "***")
        self.assertEqual(event["trace_id"], "trace-2")

    def test_rate_limit_blocks_after_threshold(self) -> None:
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)

        self.assertTrue(limiter.allow("actor-1", 1))
        self.assertTrue(limiter.allow("actor-1", 2))
        self.assertFalse(limiter.allow("actor-1", 3))
        self.assertTrue(limiter.allow("actor-1", 62))

    def test_manifest_gate_requires_hashes(self) -> None:
        ok = validate_manifest([DependencyRecord("fastapi", "0.120.0", "sha256:abc123")])
        bad = validate_manifest([DependencyRecord("unknown", "1.0.0", "nohash")])

        self.assertTrue(ok["passed"])
        self.assertFalse(bad["passed"])
        self.assertEqual(bad["missing_or_invalid"], ["unknown"])

    def test_constant_time_token_match(self) -> None:
        self.assertTrue(constant_time_token_match("token-a", "token-a"))
        self.assertFalse(constant_time_token_match("token-a", "token-b"))


if __name__ == "__main__":
    unittest.main()
