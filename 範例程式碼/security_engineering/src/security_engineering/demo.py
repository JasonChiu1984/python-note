from __future__ import annotations

import json

from .audit import AuditLog
from .auth import PasswordHasher, constant_time_token_match
from .policy import RolePolicy
from .rate_limit import SlidingWindowRateLimiter
from .supply_chain import DependencyRecord, validate_manifest
from .validation import safe_error_response, validate_user_payload


def main() -> int:
    hasher = PasswordHasher(iterations=120_000)
    encoded = hasher.hash_password("correct-horse-battery")
    policy = RolePolicy()
    audit = AuditLog()
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
    payload = validate_user_payload({"email": "operator@example.com", "role": "operator"})
    audit.record("login.success", payload.email, "trace-sec-1", token="demo-token")
    result = {
        "password_verified": hasher.verify("correct-horse-battery", encoded),
        "token_match": constant_time_token_match("expected-token", "expected-token"),
        "operator_can_write_order": policy.can(payload.role, "write", "order"),
        "operator_can_delete_order": policy.can(payload.role, "delete", "order"),
        "rate_limit": [limiter.allow(payload.email, 1), limiter.allow(payload.email, 2), limiter.allow(payload.email, 3)],
        "audit": audit.events,
        "safe_error": safe_error_response("invalid_request", "trace-sec-1"),
        "manifest": validate_manifest([DependencyRecord("fastapi", "0.120.0", "sha256:abc123")]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
