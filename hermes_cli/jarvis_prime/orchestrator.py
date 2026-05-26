"""Orchestrator — single entry point for JARVIS Prime routing.

``route(mission) -> SessionResult`` drives the full mission → mode → route →
risk → build packet → gates → surface → events → ledger pipeline. The
function shape is stable; future wave PRs swap stub call-sites for real
implementations without changing this signature.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from . import events, gates, ledger, modes, risk, surfaces
from .events import EventKind
from .modes import Mode
from .packets.build import BuildPacket, from_mission as build_from_mission
from .session import Mission, SessionResult

RouteTier = Literal["jarvis_prime", "aos_council", "specialists", "workers"]


@dataclass(frozen=True)
class RouteDecision:
    """Which tier (and which target inside it) gets the mission."""

    tier: RouteTier
    target: str
    reason: str


def _decide_route(mode: Mode, mission: Mission) -> RouteDecision:
    """Pick a routing tier + target for the mode.

    Stub: deterministic table. Builder/operator escalate to workers via
    specialists; critic/strategy stop at the council; companion stays on
    JARVIS Prime.
    """
    if mode is Mode.BUILDER:
        return RouteDecision("workers", "codex_dispatch_governor", "builder mode dispatches a worker")
    if mode is Mode.OPERATOR:
        return RouteDecision("specialists", "delivery_scope_controller", "operator routes via delivery")
    if mode is Mode.CRITIC:
        return RouteDecision("specialists", "contrarian_reviewer", "critic engages contrarian")
    if mode is Mode.STRATEGY:
        return RouteDecision("aos_council", "aos_council_director", "strategy escalates to council")
    if mode is Mode.MOBILE_VOICE:
        return RouteDecision("jarvis_prime", "mobile_surface", "voice handled on-device")
    return RouteDecision("jarvis_prime", "companion_thread", "companion stays local")


def _mission_id(mission: Mission, started_at: float) -> str:
    """Deterministic-per-call mission id derived from start time."""
    return f"msn-{int(started_at * 1000):013d}"


def route(mission: Mission) -> SessionResult:
    """Run the mission through the full JARVIS Prime pipeline.

    Returns a SessionResult capturing every stage's output. The function is
    pure-over in-memory stub stores; future wave PRs replace internals while
    keeping this signature stable.
    """
    started_at = time.time()
    mission_id = _mission_id(mission, started_at)

    mode = modes.classify(mission)
    decision = _decide_route(mode, mission)
    assessment = risk.classify_risk(mission, mode)

    packet: BuildPacket | None = None
    if mode in (Mode.BUILDER, Mode.OPERATOR):
        packet = build_from_mission(mission, mode, assessment, mission_id)

    summary = gates.run_gates(mission, mode, assessment, packet)

    rendered = surfaces.render_for_surface(
        mission.surface, mission, mode, decision, assessment, summary
    )

    routed = events.emit(
        EventKind.ROUTED,
        {"mission_id": mission_id, "mode": mode.value, "tier": decision.tier},
    )
    gated = events.emit(
        EventKind.GATED,
        {"mission_id": mission_id, "headline": summary.headline},
    )
    rendered_ev = events.emit(
        EventKind.SURFACE_RENDERED,
        {"mission_id": mission_id, "surface": mission.surface.value},
    )

    entry = ledger.append(mission, mode, decision, assessment, summary, mission_id)
    events.emit(EventKind.LEDGER_APPENDED, {"mission_id": mission_id, "ledger_id": entry.id})

    return SessionResult(
        mission=mission,
        mode=mode,
        route=decision,
        risk=assessment,
        build_packet=packet,
        gate_summary=summary,
        surface_output=rendered,
        ledger_entry=entry,
        events=(routed, gated, rendered_ev),
    )
