"""Structured log helpers for container stdout."""

from __future__ import annotations

import json
import sys
import time
from typing import Any


SENSITIVE_KEYS = {"password", "secret", "token", "api_key"}


def redact(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_KEYS:
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted


def log_json(event: str, **fields: Any) -> str:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        **redact(fields),
    }
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    print(line, file=sys.stdout, flush=True)
    return line
