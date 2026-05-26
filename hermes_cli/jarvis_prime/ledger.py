"""Decision ledger — append-only record of routed missions.

Future wave PRs replace the in-memory list with a JSONL file at
``~/.hermes/jarvis/ledger.jsonl``; the LedgerEntry shape and append/tail
signatures stay stable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gates import GateSummary
    from .modes import Mode
    from .orchestrator import RouteDecision
    from .risk import RiskAssessment
    from .session import Mission


@dataclass(frozen=True)
class LedgerEntry:
    """A persisted decision record for a single mission."""

    id: str
    ts: float
    mission_id: str
    mode: str
    route: str
    risk: str
    gate_result: str


_LEDGER: list[LedgerEntry] = []


def append(
    mission: "Mission",
    mode: "Mode",
    decision: "RouteDecision",
    risk: "RiskAssessment",
    summary: "GateSummary",
    mission_id: str,
) -> LedgerEntry:
    """Persist a ledger entry for the routed mission."""
    entry = LedgerEntry(
        id=f"led-{len(_LEDGER):06d}",
        ts=time.time(),
        mission_id=mission_id,
        mode=mode.value,
        route=f"{decision.tier}:{decision.target}",
        risk=risk.level.value,
        gate_result=summary.headline,
    )
    _LEDGER.append(entry)
    return entry


def tail(n: int = 10) -> tuple[LedgerEntry, ...]:
    """Return the most recent ``n`` ledger entries (oldest-first)."""
    if n <= 0:
        return ()
    return tuple(_LEDGER[-n:])
