"""JARVIS Prime CLI adapter package.

Thin Python landing pad for the JARVIS Prime skill defined at
``skills/jarvis-prime/SKILL.md``. Exposes:

- ``Mode`` — enum of the six named modes + ``AUTO``.
- ``ModeClassifier`` — heuristic free-text → ``Mode``.
- ``Router`` / ``RouteResult`` — bundles persona header + SKILL.md
  response format for a resolved mode.
- ``Persona`` — frozen dataclass pairing a mode with its header.
- ``SLASH_COMMANDS`` — slash → ``Mode`` mapping table.
- ``dispatch`` — slash-command-line → ``DispatchResult | None``.

The full REPL wiring into ``cli.py`` is deferred to a future wave;
see ``docs/aci/reports/W01_CLI_JARVIS_WIRING.md`` for the exact
follow-up.
"""

from __future__ import annotations

from .classifier import ModeClassifier
from .modes import NAMED_MODES, Mode
from .persona import (
    DEFAULT_RESPONSE_FORMAT,
    OPERATIONAL_HANDOFF_FORMAT,
    Persona,
    header_for,
)
from .router import RouteResult, Router
from .slash import SLASH_COMMANDS, DispatchResult, dispatch

__all__ = [
    "DEFAULT_RESPONSE_FORMAT",
    "DispatchResult",
    "Mode",
    "ModeClassifier",
    "NAMED_MODES",
    "OPERATIONAL_HANDOFF_FORMAT",
    "Persona",
    "RouteResult",
    "Router",
    "SLASH_COMMANDS",
    "dispatch",
    "header_for",
]
