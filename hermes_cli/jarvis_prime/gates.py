"""Verification gates — the 8 gates from ``docs/jarvis-verification-gates.md``.

Stub: all gates pass with the note ``"stub: future-wave"`` except
OWNER_APPROVAL which surfaces ``"needs_owner"`` whenever the risk
assessment is owner-gated. Future wave PRs replace ``run_gates`` with
real evidence-driven enforcement while keeping the GateSummary shape stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .modes import Mode
    from .packets.build import BuildPacket
    from .risk import RiskAssessment
    from .session import Mission


class GateName(str, Enum):
    """Eight verification gates JARVIS Prime evaluates per mission."""

    PLANNING = "planning"
    BUILD = "build"
    REVIEW = "review"
    TEST = "test"
    SECURITY = "security"
    RELEASE = "release"
    OWNER_APPROVAL = "owner_approval"
    ROLLBACK = "rollback"


GateStatus = Literal["pass", "fail", "needs_owner", "skipped"]


@dataclass(frozen=True)
class GateOutcome:
    """The result of evaluating one gate against a mission."""

    name: GateName
    status: GateStatus
    note: str


@dataclass(frozen=True)
class GateSummary:
    """Collected outcomes for all 8 gates plus a one-line headline."""

    outcomes: tuple[GateOutcome, ...]
    headline: str


def run_gates(
    mission: "Mission",
    mode: "Mode",
    risk: "RiskAssessment",
    packet: "BuildPacket | None",
) -> GateSummary:
    """Evaluate the 8 gates against the mission.

    Stub: returns a uniformly-passing summary except OWNER_APPROVAL
    when ``risk.owner_gate`` is set.
    """
    outcomes: list[GateOutcome] = []
    for name in GateName:
        if name is GateName.OWNER_APPROVAL and risk.owner_gate:
            outcomes.append(GateOutcome(name, "needs_owner", "owner gate required by risk"))
        else:
            outcomes.append(GateOutcome(name, "pass", "stub: future-wave"))
    needs_owner = any(o.status == "needs_owner" for o in outcomes)
    headline = "needs-owner" if needs_owner else "pass"
    return GateSummary(outcomes=tuple(outcomes), headline=headline)
