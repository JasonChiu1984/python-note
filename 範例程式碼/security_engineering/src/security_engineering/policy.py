from __future__ import annotations

from dataclasses import dataclass, field


Permission = tuple[str, str]


@dataclass(frozen=True)
class RolePolicy:
    permissions: dict[str, set[Permission]] = field(
        default_factory=lambda: {
            "admin": {("read", "order"), ("write", "order"), ("delete", "order"), ("read", "audit")},
            "operator": {("read", "order"), ("write", "order")},
            "auditor": {("read", "order"), ("read", "audit")},
        }
    )

    def can(self, role: str, action: str, resource: str) -> bool:
        return (action, resource) in self.permissions.get(role, set())
