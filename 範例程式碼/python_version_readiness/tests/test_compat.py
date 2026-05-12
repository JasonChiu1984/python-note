import unittest

from version_readiness.compat import (
    FeaturePolicy,
    RuntimeProfile,
    build_readiness_report,
)


class RuntimeReadinessTests(unittest.TestCase):
    def test_profile_version_label(self) -> None:
        profile = RuntimeProfile(3, 14, 5, "CPython")
        self.assertEqual(profile.version_label, "3.14.5")
        self.assertTrue(profile.at_least(3, 14))
        self.assertFalse(profile.at_least(3, 15))

    def test_policy_availability_uses_major_minor(self) -> None:
        policy = FeaturePolicy("demo", (3, 14), "use", "fallback")
        self.assertTrue(policy.available_on(RuntimeProfile(3, 14, 0, "CPython")))
        self.assertFalse(policy.available_on(RuntimeProfile(3, 13, 9, "CPython")))

    def test_report_contains_fallback_for_unavailable_features(self) -> None:
        report = build_readiness_report(
            RuntimeProfile(3, 13, 10, "CPython"),
            (FeaturePolicy("future_feature", (3, 14), "use it", "keep fallback"),),
        )
        self.assertEqual(report["runtime"], "3.13.10")
        self.assertEqual(report["features"][0]["action"], "keep fallback")
        self.assertFalse(report["features"][0]["available"])


if __name__ == "__main__":
    unittest.main()
