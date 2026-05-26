"""Context-window compression.

Stub: deterministic character-budget truncation. Future wave PRs replace
``compress`` with a real summarizer; the ContextWindow shape stays stable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextWindow:
    """A bounded slice of conversation context."""

    tokens: int
    messages: tuple[str, ...]
    budget: int


def compress(window: ContextWindow) -> ContextWindow:
    """Truncate messages so the joined size fits ``window.budget`` chars."""
    budget = max(window.budget, 0)
    remaining = budget
    kept: list[str] = []
    for msg in window.messages:
        if remaining <= 0:
            break
        kept.append(msg[:remaining])
        remaining -= len(kept[-1])
    return ContextWindow(tokens=window.tokens, messages=tuple(kept), budget=budget)
