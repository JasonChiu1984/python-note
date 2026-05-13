from __future__ import annotations

import re
from dataclasses import dataclass


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class UserPayload:
    email: str
    role: str


def validate_user_payload(payload: dict[str, object]) -> UserPayload:
    email = payload.get("email")
    role = payload.get("role")
    if not isinstance(email, str) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValidationError("invalid email")
    if len(email) > 120:
        raise ValidationError("email too long")
    if role not in {"admin", "operator", "auditor"}:
        raise ValidationError("invalid role")
    return UserPayload(email=email, role=str(role))


def safe_error_response(error_code: str, trace_id: str) -> dict[str, str]:
    return {"error": error_code, "trace_id": trace_id}
