"""Router — bundles persona header + response format for a resolved mode.

The Router never calls an LLM or external service. It returns a
``RouteResult`` carrying the SKILL.md format block (default or
operational, depending on mode) plus the mode-specific persona header,
so the caller can render it however they like.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modes import Mode
from .persona import DEFAULT_RESPONSE_FORMAT, OPERATIONAL_HANDOFF_FORMAT, header_for


_OPERATIONAL_MODES: frozenset[Mode] = frozenset({Mode.OPERATOR, Mode.BUILDER})


@dataclass(frozen=True)
class RouteResult:
    mode: Mode
    persona_header: str
    response_format: str


class Router:
    def route(self, mode: Mode, text: str) -> RouteResult:
        if mode is Mode.AUTO:
            raise ValueError("Router cannot route AUTO; resolve via ModeClassifier first.")
        fmt = OPERATIONAL_HANDOFF_FORMAT if mode in _OPERATIONAL_MODES else DEFAULT_RESPONSE_FORMAT
        return RouteResult(
            mode=mode,
            persona_header=header_for(mode),
            response_format=fmt,
        )
