"""Evaluate fictional authorization records offline; no token processing or network."""

from dataclasses import dataclass, replace
import argparse
import json
import unittest


@dataclass(frozen=True)
class Context:
    subject: str = "maintenance-reader"
    device_compliant: bool = True
    posture_age_s: int = 20
    audience: str = "hvac-support"
    action: str = "trend:read"
    resource: str = "site-a/ahu-01"
    expires_at: int = 150
    now: int = 100
    revoked: bool = False
    dependency_available: bool = True
    approved_ticket: bool = True


def evaluate(c: Context) -> tuple[bool, str]:
    """Input is an already verified context, not raw or application-supplied claims."""
    if not c.dependency_available:
        return False, "policy_dependency_unavailable"
    if c.revoked or not 0 <= c.now < c.expires_at:
        return False, "revoked_or_expired"
    if c.audience != "hvac-support":
        return False, "wrong_audience"
    if not c.device_compliant or not 0 <= c.posture_age_s <= 60:
        return False, "posture_missing_or_stale"
    if not c.approved_ticket:
        return False, "ticket_not_approved"
    if (c.subject, c.action, c.resource) != (
        "maintenance-reader", "trend:read", "site-a/ahu-01"
    ):
        return False, "outside_policy"
    return True, "allowed_read_only"


class DemoTests(unittest.TestCase):
    def test_only_approved_read(self):
        self.assertEqual(evaluate(Context()), (True, "allowed_read_only"))
        for change in (dict(action="output:write"), dict(resource="site-b/ahu-01"),
                       dict(subject="other"), dict(approved_ticket=False)):
            with self.subTest(change=change):
                self.assertFalse(evaluate(replace(Context(), **change))[0])

    def test_session_revocation_and_expiry(self):
        for change in (dict(revoked=True), dict(now=150), dict(audience="other-api")):
            self.assertFalse(evaluate(replace(Context(), **change))[0])

    def test_stale_posture_and_dependency(self):
        for change in (dict(posture_age_s=61), dict(posture_age_s=-1),
                       dict(device_compliant=False), dict(dependency_available=False)):
            self.assertFalse(evaluate(replace(Context(), **change))[0])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--test", action="store_true")
    if p.parse_args().test:
        unittest.main(argv=["lab"])
    else:
        for name, c in [
            ("approved", Context()),
            ("stale", replace(Context(), posture_age_s=61)),
            ("revoked", replace(Context(), revoked=True)),
            ("different_site", replace(Context(), resource="site-b/ahu-01")),
            ("policy_unavailable", replace(Context(), dependency_available=False)),
        ]:
            allowed, reason = evaluate(c)
            print(json.dumps({"case": name, "allowed": allowed, "reason": reason}))
