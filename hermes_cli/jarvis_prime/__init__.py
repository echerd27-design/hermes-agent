"""JARVIS Prime operating-layer runtime types and surface adapters.

This package is the runtime counterpart to the JARVIS Prime spec at
``docs/jarvis-prime-operating-system.md``. Wave 04 introduces the
``JarvisTurn`` shape and the per-surface adapters used by CLI, Slack,
Android, Termux, and voice flows.
"""

from .surfaces import (
    SLACK_MAX,
    SURFACES,
    TERMUX_MAX,
    VOICE_MAX,
    JarvisTurn,
    render,
    to_android,
    to_cli,
    to_slack,
    to_termux,
    to_voice,
)

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
