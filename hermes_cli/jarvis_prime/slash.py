"""Slash command dispatcher for JARVIS Prime in the CLI.

Maps a slash command line (e.g. ``"/builder ship the PR"``) to a
``DispatchResult`` carrying the resolved mode, the payload after the
command, and the ``RouteResult`` ready for rendering.

Returns ``None`` (no exception) when:

- the input is not a slash command,
- the slash command is not a JARVIS slash,
- ``/voice`` is followed by a subcommand token (``on``, ``off``,
  ``tts``, ``status``) — those defer to the existing voice handler
  registered in ``hermes_cli/commands.py``.

This ``None`` contract is what allows the future REPL wiring in
``cli.py`` (Wave 02) to fall through to the existing slash dispatcher
without changing unknown-command behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from .classifier import ModeClassifier
from .modes import Mode
from .router import RouteResult, Router


SLASH_COMMANDS: dict[str, Mode] = {
    "/jarvis": Mode.AUTO,
    "/jp": Mode.AUTO,
    "/jarvis-prime": Mode.AUTO,
    "/builder": Mode.BUILDER,
    "/operator": Mode.OPERATOR,
    "/strategy": Mode.STRATEGY,
    "/critic": Mode.CRITIC,
    "/companion": Mode.COMPANION,
    "/voice": Mode.MOBILE_VOICE,
    "/mobile-voice": Mode.MOBILE_VOICE,
}


_VOICE_SUBCOMMANDS: frozenset[str] = frozenset({"on", "off", "tts", "status"})


@dataclass(frozen=True)
class DispatchResult:
    mode: Mode
    payload: str
    route: RouteResult


def _split(command_line: str) -> tuple[str, str]:
    parts = command_line.strip().split(maxsplit=1)
    head = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return head, rest


def dispatch(command_line: str) -> DispatchResult | None:
    if not isinstance(command_line, str):
        return None
    stripped = command_line.strip()
    if not stripped.startswith("/"):
        return None

    head, payload = _split(stripped)
    head_lower = head.lower()
    mode = SLASH_COMMANDS.get(head_lower)
    if mode is None:
        return None

    if head_lower == "/voice":
        first_token = payload.split(maxsplit=1)[0].lower() if payload else ""
        if first_token in _VOICE_SUBCOMMANDS:
            return None

    if mode is Mode.AUTO:
        mode = ModeClassifier().classify(payload)

    route = Router().route(mode, payload)
    return DispatchResult(mode=mode, payload=payload, route=route)
