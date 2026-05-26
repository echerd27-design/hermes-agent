"""Session schema — Mission, SessionContext, SessionResult."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .surfaces import Surface

if TYPE_CHECKING:
    from .events import Event
    from .gates import GateSummary
    from .ledger import LedgerEntry
    from .modes import Mode
    from .orchestrator import RouteDecision
    from .packets.build import BuildPacket
    from .risk import RiskAssessment


@dataclass(frozen=True)
class Mission:
    """Input mission to be routed through JARVIS Prime."""

    text: str
    surface: Surface
    repo_root: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionContext:
    """Runtime context attached to a single routing decision."""

    mission_id: str
    started_at: float
    context_budget: int = 16_000


@dataclass(frozen=True)
class SessionResult:
    """End-to-end output of ``route(mission)``."""

    mission: Mission
    mode: "Mode"
    route: "RouteDecision"
    risk: "RiskAssessment"
    build_packet: "BuildPacket | None"
    gate_summary: "GateSummary"
    surface_output: str
    ledger_entry: "LedgerEntry"
    events: tuple["Event", ...]
