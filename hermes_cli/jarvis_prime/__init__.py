"""JARVIS Prime — runtime kernel scaffold.

Public entry point: ``route(mission) -> SessionResult``.

This package is the scaffolded foundation for the JARVIS Prime operating
layer. Today its modules return deterministic stub data so the integration
contract (6 modes, 8 gates, 3-tier routing, 13 module surfaces) is locked
into code. Subsequent wave PRs replace stub bodies with real implementations
without changing the public dataclass shapes or function signatures.

Nothing in this package is imported by ``hermes_cli/__init__.py`` — callers
must opt in explicitly via ``from hermes_cli.jarvis_prime import route``.
"""

from __future__ import annotations

from .gates import GateName, GateOutcome, GateSummary
from .modes import Mode
from .orchestrator import RouteDecision, route
from .risk import RiskAssessment, RiskClass
from .session import Mission, SessionContext, SessionResult
from .surfaces import Surface

__all__ = [
    "GateName",
    "GateOutcome",
    "GateSummary",
    "Mission",
    "Mode",
    "RiskAssessment",
    "RiskClass",
    "RouteDecision",
    "SessionContext",
    "SessionResult",
    "Surface",
    "route",
]
