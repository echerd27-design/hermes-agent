"""Build packet — the implementation brief handed to a builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..modes import Mode
    from ..risk import RiskAssessment
    from ..session import Mission


@dataclass(frozen=True)
class BuildPacket:
    """The contract a builder receives for a single mission."""

    mission_id: str
    allowed_paths: tuple[str, ...]
    disallowed_paths: tuple[str, ...]
    verification_plan: tuple[str, ...]
    rollback: str


def from_mission(
    mission: "Mission",
    mode: "Mode",
    risk: "RiskAssessment",
    mission_id: str,
) -> BuildPacket:
    """Construct a build packet for the mission (stub: conservative defaults)."""
    return BuildPacket(
        mission_id=mission_id,
        allowed_paths=("hermes_cli/jarvis_prime/**", "tests/**", "docs/aci/**"),
        disallowed_paths=("gateway/**", "apps/**", "platforms/**", "AGENTS.md", "CLAUDE.md"),
        verification_plan=(
            "python -m compileall hermes_cli/jarvis_prime",
            "python -m pytest tests/test_jarvis_prime_integration.py -x -q",
        ),
        rollback="revert PR; subpackage is additive and safe to delete wholesale",
    )
