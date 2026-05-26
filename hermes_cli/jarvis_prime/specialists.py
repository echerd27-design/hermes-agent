"""Deterministic specialist activation matrix for JARVIS Prime.

This module exposes a small, pure-stdlib helper that maps a piece of
free-form mission text (plus optional context hints) to the set of
JARVIS Prime specialists that should be in scope.

Source of truth for the specialist roster and activation triggers is
``docs/jarvis-prime-operating-system.md`` ("Operating Hierarchy" and
"Specialist Activation Rules") and the active subagent files in
``.claude/agents/`` for the council-side roles.

Design contract:

* Pure function. No I/O, no global state mutation, no randomness.
* Deterministic order. Results always come back in the canonical
  ``SPECIALISTS`` order regardless of how triggers happened to fire.
* Smallest useful set. A specialist is only included when one of its
  triggers actually appears in the input (or it is forced via
  ``context['force']``).
* Word-boundary matching. Triggers match on whole-word/phrase
  boundaries so ``"ship"`` does not fire inside ``"shipping"``.

The router that consumes this matrix lives in a sibling module added
by a later wave. This file intentionally does not import it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Specialist:
    """One JARVIS Prime specialist entry.

    Attributes:
        id: stable kebab-case identifier (e.g. ``"hazmat-command-specialist"``).
        name: human-readable display name.
        triggers: lowercase phrases. A specialist activates when any of
            its triggers appears in the input with word boundaries.
    """

    id: str
    name: str
    triggers: FrozenSet[str]


SPECIALISTS: Tuple[Specialist, ...] = (
    Specialist(
        id="hazmat-command-specialist",
        name="HazMat Command Specialist",
        triggers=frozenset({
            "hazmat",
            "dangerous goods",
            "49 cfr",
            "tdg",
            "erg",
            "placard",
            "placarding",
            "shipping paper",
            "shipping papers",
            "ocr provenance",
            "audit ledger",
            "compliance claim",
            "compliance claims",
            "driver safety",
            "safety workflow",
        }),
    ),
    Specialist(
        id="nourish-product-specialist",
        name="Nourish Product Specialist",
        triggers=frozenset({
            "nourish",
            "nutrition",
            "recipe",
            "recipes",
            "meal log",
            "meal logging",
            "behavior change",
            "food privacy",
            "nutrient math",
            "health claim",
            "health claims",
        }),
    ),
    Specialist(
        id="logistics-domain-specialist",
        name="Logistics Domain Specialist",
        triggers=frozenset({
            "logistics",
            "hey jay",
            "trucking",
            "dispatch",
            "fleet",
            "terminal",
            "terminals",
            "driver workflow",
            "driver workflows",
            "ltl",
            "carrier",
            "carriers",
        }),
    ),
    Specialist(
        id="security-compliance-reviewer",
        name="Security / Compliance Reviewer",
        triggers=frozenset({
            "security",
            "compliance",
            "secret",
            "secrets",
            "credential",
            "credentials",
            "oauth",
            "vulnerability",
            "vulnerabilities",
            "cve",
            "regulated",
            "trust boundary",
            "authz",
            "authn",
        }),
    ),
    Specialist(
        id="product-ux-reviewer",
        name="Product UX Reviewer",
        triggers=frozenset({
            "ux",
            "user experience",
            "onboarding",
            "demo",
            "demo flow",
            "user journey",
            "usability",
            "friction",
            "adoption",
        }),
    ),
    Specialist(
        id="qa-release-gate",
        name="QA Release Gate",
        triggers=frozenset({
            "release",
            "release readiness",
            "release gate",
            "go/no-go",
            "pre-release",
            "ship",
            "launch",
            "deploy",
            "production deploy",
            "qa gate",
            "test coverage",
        }),
    ),
    Specialist(
        id="memory-evidence-curator",
        name="Memory Evidence Curator",
        triggers=frozenset({
            "evidence",
            "audit",
            "citation",
            "citations",
            "memory",
            "durable memory",
            "source of truth",
            "fact verification",
        }),
    ),
    Specialist(
        id="career-strategy-specialist",
        name="Career Strategy Specialist",
        triggers=frozenset({
            "career",
            "career strategy",
            "promotion",
            "resume",
            "cv",
            "interview",
            "job offer",
            "hiring negotiation",
            "leveling",
            "career positioning",
        }),
    ),
    Specialist(
        id="contrarian-reviewer",
        name="Contrarian Reviewer",
        triggers=frozenset({
            "contrarian",
            "red team",
            "red-team",
            "devil's advocate",
            "critique",
            "challenge assumption",
            "blind spot",
            "weak assumption",
            "push back",
            "push-back",
        }),
    ),
)


# Index for O(1) ID lookup. Built once at import; never mutated.
_BY_ID: Mapping[str, Specialist] = {s.id: s for s in SPECIALISTS}


def _trigger_pattern(trigger: str) -> re.Pattern[str]:
    # ``re.escape`` handles the few punctuation characters present in
    # triggers like ``"devil's advocate"`` or ``"go/no-go"``. ``\b`` is
    # only a real word-boundary when the adjacent character is alnum, so
    # for triggers that start or end with punctuation we fall back to a
    # lookaround that treats any non-alnum / start / end as the boundary.
    body = re.escape(trigger)
    left = r"(?:^|(?<=[^0-9a-z]))" if not trigger[0].isalnum() else r"\b"
    right = r"(?:(?=[^0-9a-z])|$)" if not trigger[-1].isalnum() else r"\b"
    return re.compile(left + body + right)


# Precompile all trigger patterns once at import.
_PATTERNS: Mapping[str, Tuple[re.Pattern[str], ...]] = {
    s.id: tuple(_trigger_pattern(t) for t in sorted(s.triggers))
    for s in SPECIALISTS
}


def _normalize_ids(ids: Optional[Iterable[object]]) -> FrozenSet[str]:
    if not ids:
        return frozenset()
    out = set()
    for value in ids:
        if isinstance(value, str):
            out.add(value)
    return frozenset(out)


def activate_specialists(
    text: str,
    *,
    context: Optional[Mapping[str, object]] = None,
) -> Tuple[Specialist, ...]:
    """Return the smallest useful specialist set for ``text``.

    Args:
        text: free-form mission / request text. Matching is
            case-insensitive and uses word/phrase boundaries.
        context: optional mapping. Recognized keys:

            * ``"force"``   — iterable of specialist IDs to always
              include. Unknown IDs are ignored.
            * ``"exclude"`` — iterable of specialist IDs to drop from
              the result even if a trigger fires. Unknown IDs are
              ignored.

    Returns:
        Tuple of :class:`Specialist` in canonical :data:`SPECIALISTS`
        order. Empty tuple when nothing applies.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    lowered = text.lower()

    forced = _normalize_ids((context or {}).get("force"))
    excluded = _normalize_ids((context or {}).get("exclude"))

    selected = []
    for specialist in SPECIALISTS:
        if specialist.id in excluded:
            continue
        if specialist.id in forced:
            selected.append(specialist)
            continue
        if not lowered:
            continue
        for pattern in _PATTERNS[specialist.id]:
            if pattern.search(lowered):
                selected.append(specialist)
                break

    return tuple(selected)


__all__ = ["Specialist", "SPECIALISTS", "activate_specialists"]
