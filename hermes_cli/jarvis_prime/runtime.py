"""Stable handoff rendering for JARVIS Prime surfaces.

This module exposes the JARVIS Prime turn/handoff output contract used
by gateway, Slack, mobile, and CLI surfaces. Two rendering functions
are provided:

* :func:`render_handoff` — long form matching the operational handoff
  template in ``skills/jarvis-prime/SKILL.md`` plus the
  ``Remaining risk`` field from ``docs/jarvis-verification-gates.md``.
* :func:`render_handoff_compact` — mobile-safe form bounded by a line
  budget and per-line width cap, matching the short-response contract
  in ``docs/mobile-voice-development-workflow.md``.

The module is pure: no I/O, no env reads, no network. Both rendering
functions are deterministic so callers can use direct string equality
for snapshot testing and content hashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Iterable, Mapping

from hermes_cli.jarvis_prime import persona

__all__ = ["Handoff", "render_handoff", "render_handoff_compact"]


_COMPACT_MIN_LINES = 4
_COMPACT_DEFAULT_LINES = 6
_COMPACT_DEFAULT_WIDTH = 80
_TRUNCATION_SUFFIX = "…"


@dataclass(frozen=True, slots=True)
class Handoff:
    """A single JARVIS Prime turn ready to be rendered.

    Every field is keyword-constructable. ``owner_gates`` and
    ``actions`` are tuples so equal handoffs compare equal and the
    rendered output is deterministic. ``remaining_risk`` may be the
    empty string when no risk remains; the long-form renderer prints
    ``none`` in that case.
    """

    mission: str
    mode: str
    route: str
    delegate: str
    owner_gates: tuple[str, ...]
    verification: str
    next_action: str
    remaining_risk: str = ""
    actions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        persona.validate_mode(self.mode)
        if not isinstance(self.owner_gates, tuple):
            raise TypeError("owner_gates must be a tuple")
        if not isinstance(self.actions, tuple):
            raise TypeError("actions must be a tuple")

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "Handoff":
        """Build a :class:`Handoff` from a plain mapping.

        List-like values for ``owner_gates`` and ``actions`` are
        coerced to tuples. Unknown keys raise ``ValueError`` so
        upstream contract drift surfaces immediately rather than
        being silently dropped.
        """

        allowed = {f.name for f in fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(
                f"unknown Handoff field(s): {sorted(unknown)!r}"
            )
        kwargs: dict[str, object] = {}
        for key, value in data.items():
            if key in {"owner_gates", "actions"} and not isinstance(value, tuple):
                if isinstance(value, (list, tuple)):
                    kwargs[key] = tuple(value)
                else:
                    raise TypeError(
                        f"{key} must be a sequence of strings, got {type(value).__name__}"
                    )
            else:
                kwargs[key] = value
        return cls(**kwargs)  # type: ignore[arg-type]


def _join_or_none(items: Iterable[str]) -> str:
    rendered = ", ".join(items)
    return rendered if rendered else "none"


def render_handoff(handoff: Handoff) -> str:
    """Render the long-form JARVIS Prime handoff.

    The layout follows the operational handoff template in
    ``skills/jarvis-prime/SKILL.md`` with an explicit ``Remaining
    risk`` line. The output ends with a single trailing newline so it
    composes cleanly into Slack/Markdown surfaces.
    """

    lines = [
        persona.voice_intro(handoff.mode),
        f"Mission: {handoff.mission}",
        f"Route selected: {handoff.route}",
        f"Delegate: {handoff.delegate}",
        f"Actions taken: {_join_or_none(handoff.actions)}",
        f"Verification: {handoff.verification}",
        f"Owner gates: {_join_or_none(handoff.owner_gates)}",
        f"Next step: {handoff.next_action}",
        f"Remaining risk: {handoff.remaining_risk or 'none'}",
    ]
    return "\n".join(lines) + "\n"


def _truncate(value: str, max_width: int) -> str:
    if len(value) <= max_width:
        return value
    cut = max(1, max_width - len(_TRUNCATION_SUFFIX))
    return value[:cut] + _TRUNCATION_SUFFIX


def render_handoff_compact(
    handoff: Handoff,
    *,
    max_lines: int = _COMPACT_DEFAULT_LINES,
    max_width: int = _COMPACT_DEFAULT_WIDTH,
) -> str:
    """Render the mobile-safe compact JARVIS Prime handoff.

    Always preserves ``mission``, the mode tag, ``next_action`` and
    non-empty ``owner_gates``. Drops the risk line when
    ``remaining_risk`` is empty so the form stays within the line
    budget. Long fields are truncated with a trailing ``…`` so each
    line respects ``max_width``.

    Raises ``ValueError`` when ``max_lines`` is below the floor
    required to preserve the mandatory fields.
    """

    if max_lines < _COMPACT_MIN_LINES:
        raise ValueError(
            f"max_lines must be >= {_COMPACT_MIN_LINES} to preserve required fields"
        )
    if max_width < 16:
        raise ValueError("max_width must be >= 16 for usable truncation")

    persona.validate_mode(handoff.mode)

    mission_line = _truncate(
        f"[{handoff.mode}] Mission: {handoff.mission}", max_width
    )
    route_line = _truncate(
        f"Route: {handoff.route} → {handoff.delegate}", max_width
    )
    next_line = _truncate(f"Next: {handoff.next_action}", max_width)

    lines: list[str] = [mission_line, route_line]
    if handoff.owner_gates:
        lines.append(
            _truncate(f"Gates: {', '.join(handoff.owner_gates)}", max_width)
        )
    lines.append(next_line)
    if handoff.remaining_risk:
        lines.append(_truncate(f"Risk: {handoff.remaining_risk}", max_width))

    if len(lines) > max_lines:
        # Mandatory lines: mission, route, next. Optional: gates, risk.
        # Drop optional lines from the end (risk first, then gates) to
        # respect the budget while preserving required fields.
        mandatory = {mission_line, route_line, next_line}
        trimmed: list[str] = []
        for line in lines:
            if line in mandatory or len(trimmed) < max_lines:
                trimmed.append(line)
        lines = trimmed[:max_lines]

    return "\n".join(lines) + "\n"
