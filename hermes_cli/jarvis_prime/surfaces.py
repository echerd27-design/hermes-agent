"""Surface adapters — render a SessionResult for a delivery surface.

Today the renderer is a deterministic string template per surface. Future
wave PRs will wire real Slack blocks, Termux notifications, mobile-voice
TTS, etc. The Protocol stays stable.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .gates import GateSummary
    from .modes import Mode
    from .orchestrator import RouteDecision
    from .risk import RiskAssessment
    from .session import Mission, SessionResult


class Surface(str, Enum):
    """Delivery surfaces JARVIS Prime can render to."""

    CLI = "cli"
    SLACK = "slack"
    TERMUX = "termux"
    MOBILE_VOICE = "mobile_voice"


class SurfaceAdapter(Protocol):
    """Renders a finished SessionResult for one delivery surface."""

    def render(self, result: "SessionResult") -> str: ...  # pragma: no cover


def render_for_surface(
    surface: Surface,
    mission: "Mission",
    mode: "Mode",
    decision: "RouteDecision",
    risk: "RiskAssessment",
    summary: "GateSummary",
) -> str:
    """Render the mission outcome as a string for the given surface.

    Stub: deterministic single-string template. Mobile-voice is short
    (one line). CLI/Slack get the full multi-line block.
    """
    headline = f"[{mode.value}] {mission.text}"
    if surface is Surface.MOBILE_VOICE:
        return f"{headline} — risk={risk.level.value}, gates={summary.headline}"
    lines = [
        headline,
        f"  route: {decision.tier} -> {decision.target}",
        f"  risk:  {risk.level.value}",
        f"  gates: {summary.headline}",
    ]
    return "\n".join(lines)
