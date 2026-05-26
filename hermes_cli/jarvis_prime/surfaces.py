"""Surface adapters for JARVIS Prime turn results.

This module defines the shared contract that CLI, Slack, Android, Termux,
and voice surfaces use to render a single JARVIS Prime turn. It is pure
stdlib: no network calls, no third-party dependencies, no I/O.

The lower-level Codex transport defines its own ``TurnResult`` at
``agent/transports/codex_app_server_session.py``. That type models one
user->assistant->tool runtime cycle. ``JarvisTurn`` below models the
operating-layer turn that sits above routing and verification, and is
intentionally distinct.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


SLACK_MAX = 600
TERMUX_MAX = 280
VOICE_MAX = 240


@dataclass(frozen=True)
class JarvisTurn:
    """JARVIS Prime operating-layer turn.

    Fields mirror the documented response formats in
    ``docs/jarvis-prime-operating-system.md`` and the verification gate
    vocabulary in ``docs/jarvis-verification-gates.md``.
    """

    mission: str
    summary: str = ""
    route: str = "direct"
    mode: str = "operator"
    actions: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    rollback: str = ""
    task_packet: Mapping[str, Any] | None = field(default=None)


def _truncate(text: str, limit: int, ellipsis: str = "...") -> str:
    if len(text) <= limit:
        return text
    if limit <= len(ellipsis):
        return ellipsis[:limit]
    cut = text[: limit - len(ellipsis)]
    space = cut.rfind(" ")
    if space > 0:
        cut = cut[:space].rstrip()
    return cut + ellipsis


def _ascii_safe(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii")


def _strip_markdown(text: str) -> str:
    out = text
    for ch in ("*", "_", "`", "#", ">"):
        out = out.replace(ch, "")
    return out


def _bullets(items: tuple[str, ...], prefix: str = "- ") -> str:
    return "\n".join(f"{prefix}{item}" for item in items)


def to_cli(turn: JarvisTurn) -> str:
    """Full Coding/Operator Mode block. Always includes Route and Verification."""
    actions = _bullets(turn.actions) if turn.actions else "  (none)"
    verification = _bullets(turn.verification) if turn.verification else "  (none)"
    risks = _bullets(turn.risks) if turn.risks else "  (none)"
    summary = turn.summary if turn.summary else "(no summary)"
    rollback = turn.rollback if turn.rollback else "(none stated)"
    lines = [
        f"Mission: {turn.mission}",
        f"Route: {turn.route}",
        f"Mode: {turn.mode}",
        "",
        "Summary:",
        f"  {summary}",
        "",
        "Actions:",
        actions,
        "",
        "Verification:",
        verification,
        "",
        "Risks:",
        risks,
        "",
        f"Rollback: {rollback}",
    ]
    return "\n".join(lines)


def to_slack(turn: JarvisTurn) -> str:
    """Compact Slack mrkdwn (single-asterisk bold)."""
    parts = [f"*{turn.mission}*"]
    if turn.summary:
        parts.append(turn.summary)
    if turn.actions:
        parts.append("*Next:* " + "; ".join(turn.actions))
    if turn.verification:
        parts.append(f"_verified: {len(turn.verification)} check(s)_")
    text = "\n".join(parts)
    return _truncate(text, SLACK_MAX, ellipsis="…")


def to_android(turn: JarvisTurn) -> dict[str, Any]:
    """JSON-ready dict mirroring JarvisTurn fields with snake_case keys."""
    return {
        "mission": turn.mission,
        "summary": turn.summary,
        "route": turn.route,
        "mode": turn.mode,
        "actions": list(turn.actions),
        "verification": list(turn.verification),
        "risks": list(turn.risks),
        "rollback": turn.rollback,
        "task_packet": dict(turn.task_packet) if turn.task_packet is not None else None,
    }


def to_termux(turn: JarvisTurn) -> str:
    """ASCII-only, no Unicode box-drawing, no ANSI codes."""
    next_action = turn.actions[0] if turn.actions else "(no next action)"
    verified = f"verified={len(turn.verification)}" if turn.verification else "verified=0"
    text = f"[{turn.route}] {turn.mission} | next: {next_action} | {verified}"
    text = _ascii_safe(text)
    return _truncate(text, TERMUX_MAX, ellipsis="...")


def to_voice(turn: JarvisTurn) -> str:
    """Short spoken-friendly text. Mobile Voice Mode shape."""
    title = _strip_markdown(turn.mission).strip()
    short_summary = _strip_markdown(turn.summary).strip()
    next_action = _strip_markdown(turn.actions[0]).strip() if turn.actions else ""
    sentences = [f"Task: {title}."]
    if short_summary:
        sentences.append(f"{short_summary}.")
    if next_action:
        sentences.append(f"Next, {next_action}.")
    text = " ".join(sentences)
    return _truncate(text, VOICE_MAX, ellipsis="...")


SURFACES: Mapping[str, Callable[[JarvisTurn], Any]] = {
    "cli": to_cli,
    "slack": to_slack,
    "android": to_android,
    "termux": to_termux,
    "voice": to_voice,
}


def render(surface: str, turn: JarvisTurn) -> Any:
    """Dispatch to the named surface adapter. Raises ValueError on unknown."""
    try:
        adapter = SURFACES[surface]
    except KeyError as exc:
        known = ", ".join(sorted(SURFACES))
        raise ValueError(f"unknown surface {surface!r}; known: {known}") from exc
    return adapter(turn)


__all__ = [
    "JarvisTurn",
    "SLACK_MAX",
    "TERMUX_MAX",
    "VOICE_MAX",
    "SURFACES",
    "render",
    "to_android",
    "to_cli",
    "to_slack",
    "to_termux",
    "to_voice",
]
