"""Specialist roster + activation rules.

Mirrors the council bench named in ``AGENTS.md`` §"JARVIS Prime Operating
Layer" and ``CLAUDE.md`` §"Project Agents". The activation table here is a
deterministic stub; future wave PRs will replace it with an LLM-driven
relevance scorer that respects the same Specialist enum.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum


class Specialist(str, Enum):
    """The default AOS Council bench."""

    ARCHITECT = "principal_systems_architect"
    PRODUCT = "product_experience_architect"
    COMMERCIAL = "commercial_strategist"
    ASSURANCE = "assurance_risk_director"
    DELIVERY = "delivery_scope_controller"
    CONTRARIAN = "contrarian_reviewer"
    EVIDENCE = "evidence_architect"
    DISPATCH = "codex_dispatch_governor"
    DIRECTOR = "aos_council_director"


ACTIVATION_RULES: Mapping[Specialist, tuple[str, ...]] = {
    Specialist.ARCHITECT: ("architecture", "system", "boundary", "integration"),
    Specialist.PRODUCT: ("ux", "flow", "demo", "adoption"),
    Specialist.COMMERCIAL: ("price", "market", "positioning", "buyer"),
    Specialist.ASSURANCE: ("security", "reliability", "compliance", "release"),
    Specialist.DELIVERY: ("scope", "phase", "bound", "execution order"),
    Specialist.CONTRARIAN: ("assumption", "evidence", "critique", "risk"),
    Specialist.EVIDENCE: ("repo", "log", "doc", "fact", "source"),
    Specialist.DISPATCH: ("acceptance", "validation", "task brief"),
    Specialist.DIRECTOR: ("plan", "governance", "council", "review"),
}


def activate_for(text: str) -> tuple[Specialist, ...]:
    """Return specialists whose keyword set matches the mission text."""
    low = (text or "").lower()
    matched: list[Specialist] = []
    for specialist, terms in ACTIVATION_RULES.items():
        if any(term in low for term in terms):
            matched.append(specialist)
    return tuple(matched)
