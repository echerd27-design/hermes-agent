"""Scoped work contract for the Hermes Native Engineer.

A WorkPacket binds a mission to an explicit allow/deny path contract,
acceptance criteria, verification commands, and a rollback plan.
Stdlib only. Hashable / JSON round-trippable.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any


def _to_tuple_of_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(str(v) for v in value)


def _to_tuple_of_pairs(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if isinstance(value, dict):
        items = value.items()
    else:
        items = value
    return tuple((str(k), str(v)) for k, v in items)


def _glob_to_fnmatch(pattern: str) -> str:
    """Translate ``**`` recursive-globs to plain ``*`` for fnmatch."""
    return pattern.replace("**", "*")


@dataclass(frozen=True)
class WorkPacket:
    mission: str
    branch: str
    allowed_files: tuple[str, ...] = ()
    forbidden_files: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    verification_commands: tuple[str, ...] = ()
    rollback_plan: str = ""
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def is_path_allowed(self, path: str) -> bool:
        norm = path.replace("\\", "/")
        for pattern in self.forbidden_files:
            if fnmatch.fnmatchcase(norm, _glob_to_fnmatch(pattern)):
                return False
        for pattern in self.allowed_files:
            if fnmatch.fnmatchcase(norm, _glob_to_fnmatch(pattern)):
                return True
        return False

    def metadata_dict(self) -> dict[str, str]:
        return {k: v for k, v in self.metadata}

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission": self.mission,
            "branch": self.branch,
            "allowed_files": list(self.allowed_files),
            "forbidden_files": list(self.forbidden_files),
            "acceptance_criteria": list(self.acceptance_criteria),
            "verification_commands": list(self.verification_commands),
            "rollback_plan": self.rollback_plan,
            "metadata": [list(pair) for pair in self.metadata],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkPacket":
        return cls(
            mission=str(data.get("mission", "")),
            branch=str(data.get("branch", "")),
            allowed_files=_to_tuple_of_str(data.get("allowed_files")),
            forbidden_files=_to_tuple_of_str(data.get("forbidden_files")),
            acceptance_criteria=_to_tuple_of_str(data.get("acceptance_criteria")),
            verification_commands=_to_tuple_of_str(data.get("verification_commands")),
            rollback_plan=str(data.get("rollback_plan", "")),
            metadata=_to_tuple_of_pairs(data.get("metadata")),
        )
