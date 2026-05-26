"""Mode registry and tone labels for JARVIS Prime.

JARVIS Prime operates in six modes (companion, strategy, critic,
operator, builder, mobile_voice) defined in
``docs/jarvis-prime-operating-system.md`` and
``skills/jarvis-prime/SKILL.md``. This module is the single source of
truth for that mode set plus the short human-readable tone labels
used when rendering a handoff. It contains no I/O and no side
effects so it is safe to import from any surface (gateway, mobile,
tests, CI).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

__all__ = [
    "MODES",
    "TONE_LABELS",
    "validate_mode",
    "tone_label",
    "voice_intro",
]


MODES: frozenset[str] = frozenset(
    {
        "companion",
        "strategy",
        "critic",
        "operator",
        "builder",
        "mobile_voice",
    }
)


_TONE_LABELS: dict[str, str] = {
    "companion": "Companion Mode — human-like support",
    "strategy": "Strategy Mode — leverage and tradeoffs",
    "critic": "Critic Mode — contrarian review",
    "operator": "Operator Mode — routing and execution",
    "builder": "Builder Mode — repo work",
    "mobile_voice": "Mobile Voice — short capture",
}

TONE_LABELS: Mapping[str, str] = MappingProxyType(_TONE_LABELS)


def validate_mode(mode: str) -> str:
    """Return ``mode`` unchanged if it is a known JARVIS Prime mode.

    Raises ``ValueError`` listing the allowed set otherwise. The error
    message intentionally names every allowed mode so callers can
    surface it to operators without re-deriving the registry.
    """

    if mode in MODES:
        return mode
    allowed = ", ".join(sorted(MODES))
    raise ValueError(
        f"unknown JARVIS Prime mode {mode!r}; allowed modes: {allowed}"
    )


def tone_label(mode: str) -> str:
    """Return the short tone label for ``mode``."""

    return _TONE_LABELS[validate_mode(mode)]


def voice_intro(mode: str) -> str:
    """Return the one-line intro used at the top of a long-form handoff."""

    return tone_label(mode)
