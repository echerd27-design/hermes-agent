"""Risk model — classify a mission into a risk class.

Stub: keyword-driven owner-gating. Future wave PRs swap this for diff-aware
heuristics (touched paths, secret-shaped strings, irreversibility markers)
without changing the return type.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .modes import Mode
    from .session import Mission


class RiskClass(str, Enum):
    """Risk classification for a mission."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    OWNER_GATED = "owner_gated"


@dataclass(frozen=True)
class RiskAssessment:
    """Result of classifying a mission against the risk model."""

    level: RiskClass
    reasons: tuple[str, ...]
    owner_gate: bool


_OWNER_GATED_TERMS = (
    "deploy", "merge", "publish", "secret", " prod", "production",
    "spend", "purchase", "delete repo", "force push", "rotate key",
)


def classify_risk(mission: "Mission", mode: "Mode") -> RiskAssessment:
    """Assign a risk class to the mission.

    Owner-gated terms trip the OWNER_GATED class with a recorded reason.
    Otherwise default to LOW; future waves will populate MEDIUM/HIGH from
    real diff inspection.
    """
    text = (mission.text or "").lower()
    matched = tuple(term.strip() for term in _OWNER_GATED_TERMS if term in text)
    if matched:
        return RiskAssessment(
            level=RiskClass.OWNER_GATED,
            reasons=matched,
            owner_gate=True,
        )
    return RiskAssessment(level=RiskClass.LOW, reasons=(), owner_gate=False)
