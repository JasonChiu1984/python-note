"""CLI automation engineering sample package."""

from .engine import (
    EXIT_PARTIAL,
    EXIT_SUCCESS,
    EXIT_VALIDATION,
    apply_manifest,
    build_summary_line,
    load_manifest,
    plan_manifest,
    write_report,
)

__all__ = [
    "EXIT_PARTIAL",
    "EXIT_SUCCESS",
    "EXIT_VALIDATION",
    "apply_manifest",
    "build_summary_line",
    "load_manifest",
    "plan_manifest",
    "write_report",
]
