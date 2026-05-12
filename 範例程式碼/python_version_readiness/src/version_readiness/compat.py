from __future__ import annotations

from dataclasses import dataclass
import platform
import sys
from typing import Any


@dataclass(frozen=True)
class RuntimeProfile:
    major: int
    minor: int
    micro: int
    implementation: str

    @classmethod
    def current(cls) -> "RuntimeProfile":
        info = sys.version_info
        return cls(
            major=info.major,
            minor=info.minor,
            micro=info.micro,
            implementation=platform.python_implementation(),
        )

    @property
    def version_label(self) -> str:
        return f"{self.major}.{self.minor}.{self.micro}"

    def at_least(self, major: int, minor: int) -> bool:
        return (self.major, self.minor) >= (major, minor)


@dataclass(frozen=True)
class FeaturePolicy:
    name: str
    min_version: tuple[int, int]
    production_action: str
    fallback: str

    def available_on(self, profile: RuntimeProfile) -> bool:
        return profile.at_least(*self.min_version)


POLICIES: tuple[FeaturePolicy, ...] = (
    FeaturePolicy(
        name="template_string_literals",
        min_version=(3, 14),
        production_action="adopt only with code review rules for safe interpolation",
        fallback="keep f-string or Template based formatting",
    ),
    FeaturePolicy(
        name="deferred_annotations",
        min_version=(3, 14),
        production_action="run schema and runtime introspection regression tests",
        fallback="keep explicit typing.get_type_hints checks in compatibility layer",
    ),
    FeaturePolicy(
        name="standard_zstd",
        min_version=(3, 14),
        production_action="use compression.zstd behind a storage compatibility boundary",
        fallback="keep optional third-party zstandard adapter",
    ),
    FeaturePolicy(
        name="python_315_beta",
        min_version=(3, 15),
        production_action="test in CI as allow-failure or prerelease lane",
        fallback="ship production on latest supported stable Python",
    ),
)


def build_readiness_report(
    profile: RuntimeProfile | None = None,
    policies: tuple[FeaturePolicy, ...] = POLICIES,
) -> dict[str, Any]:
    runtime = profile or RuntimeProfile.current()
    features = []
    for policy in policies:
        available = policy.available_on(runtime)
        features.append(
            {
                "name": policy.name,
                "available": available,
                "minimum": f"{policy.min_version[0]}.{policy.min_version[1]}",
                "action": policy.production_action if available else policy.fallback,
            }
        )

    return {
        "runtime": runtime.version_label,
        "implementation": runtime.implementation,
        "supported_baseline": runtime.at_least(3, 11),
        "recommended_ci": ["3.12", "3.13", "3.14", "3.15-dev"],
        "features": features,
    }

