"""JARVIS Prime operating modes.

Encodes the six modes from ``docs/jarvis-prime-operating-system.md``. The
classifier today is a deterministic keyword table; future wave PRs replace
``classify`` with an LLM-driven router while keeping the return type stable.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .session import Mission


class Mode(str, Enum):
    """Six operating modes JARVIS Prime can run a mission under."""

    COMPANION = "companion"
    STRATEGY = "strategy"
    CRITIC = "critic"
    OPERATOR = "operator"
    BUILDER = "builder"
    MOBILE_VOICE = "mobile_voice"


_BUILDER_TERMS = ("build", "ship", "pr ", " pr", "implement", "scaffold", "code ")
_CRITIC_TERMS = ("review", "critique", "audit ", "red team", "find bugs")
_MOBILE_TERMS = ("mobile", "voice", "walk", "jog", "driving", "termux")
_STRATEGY_TERMS = ("strategy", "roadmap", "price ", "pricing", "positioning", "market ")
_OPERATOR_TERMS = ("route", "plan ", "issue ", "delegate", "dispatch")


def classify(mission: "Mission") -> Mode:
    """Classify a mission into one of the six modes.

    Deterministic keyword routing. Default is COMPANION.
    """
    text = (mission.text or "").lower()
    if any(term in text for term in _BUILDER_TERMS):
        return Mode.BUILDER
    if any(term in text for term in _CRITIC_TERMS):
        return Mode.CRITIC
    if any(term in text for term in _MOBILE_TERMS):
        return Mode.MOBILE_VOICE
    if any(term in text for term in _STRATEGY_TERMS):
        return Mode.STRATEGY
    if any(term in text for term in _OPERATOR_TERMS):
        return Mode.OPERATOR
    return Mode.COMPANION
