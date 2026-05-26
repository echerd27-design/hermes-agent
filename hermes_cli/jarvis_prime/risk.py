"""Risk classification helper for JARVIS Prime work packets.

JARVIS Prime needs a deterministic way to label free-text intents with a risk
class so the operator layer can decide which gates to enforce, which workers
to dispatch, and whether owner authorization is required before acting.

The five risk classes mirror the levels referenced in
``docs/jarvis-prime-operating-system.md`` and ``docs/jarvis-verification-gates.md``:

* ``RC0`` — answer only; no side effects.
* ``RC1`` — local planning, drafting, or documentation work.
* ``RC2`` — code changes confined to the working tree, no external effects.
* ``RC3`` — repo mutations, pull requests, dependency installs, network
  access, or credential-adjacent edits.
* ``RC4`` — deploys, publishing, merges, DNS changes, money, app-store
  submissions, or regulated/compliance claims. Owner-gated phrases listed
  in the operating-system doc always classify here.

Classification is intentionally simple and deterministic: a single ordered
table of :class:`RiskSignal` rows is scanned against the lowercased input
and the highest matching class wins. There is no negation handling, no
intent parsing, and no LLM call. RC4 means "deserves owner review" — it
does not mean "will execute" and it is not a substitute for an explicit
authorization gate.

Public API::

    from hermes_cli.jarvis_prime import (
        RiskClass, RiskAssessment, classify, is_owner_gated, owner_gates_for,
    )

    classify("git push origin main --force")
    # -> RiskAssessment(risk_class=RiskClass.RC4, ...)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


class RiskClass(IntEnum):
    """Five-tier risk class. Comparable via standard ``<`` / ``>`` operators."""

    RC0 = 0
    RC1 = 1
    RC2 = 2
    RC3 = 3
    RC4 = 4


@dataclass(frozen=True)
class RiskSignal:
    """One row in the classifier's signal table.

    ``pattern`` is always matched case-insensitively against the lowercased
    input. When ``whole_word`` is true, the match is anchored with regex word
    boundaries (``\\b``) so e.g. ``deploy`` does not fire on ``redeploys``.
    When false, the pattern is checked with a plain substring search so that
    multi-word phrases like ``merge to main`` and operator flags like
    ``--force`` work.
    """

    pattern: str
    risk_class: RiskClass
    label: str
    owner_gate: bool = False
    whole_word: bool = True


@dataclass(frozen=True)
class RiskAssessment:
    """Result of :func:`classify`. All fields are deterministic for a given
    input — repeated calls produce byte-identical tuples in the same order.
    """

    risk_class: RiskClass
    rationale: str
    matched_signals: tuple[str, ...]
    owner_gates: tuple[str, ...]


# Single source of truth. Rows are ordered from RC4 down to RC1 so that the
# matched_signals tuple keeps a stable, owner-first ordering. New signals
# should be inserted in their risk tier; do not reorder existing rows
# without updating the determinism test in tests/test_jarvis_prime_risk.py.
SIGNALS: tuple[RiskSignal, ...] = (
    # ------------------------------------------------------------------ RC4
    # Owner-gated escalation actions enumerated in
    # docs/jarvis-prime-operating-system.md (Owner Gates section) and
    # docs/jarvis-verification-gates.md (Owner Approval Gate section).
    RiskSignal("deploy", RiskClass.RC4, "deploy", owner_gate=True),
    RiskSignal("deployment", RiskClass.RC4, "deploy", owner_gate=True),
    RiskSignal("ship to prod", RiskClass.RC4, "deploy", owner_gate=True, whole_word=False),
    RiskSignal("production deploy", RiskClass.RC4, "deploy", owner_gate=True, whole_word=False),
    RiskSignal("prod deploy", RiskClass.RC4, "deploy", owner_gate=True, whole_word=False),
    RiskSignal("publish", RiskClass.RC4, "publish", owner_gate=True),
    RiskSignal("npm publish", RiskClass.RC4, "package publish", owner_gate=True, whole_word=False),
    RiskSignal("pypi publish", RiskClass.RC4, "package publish", owner_gate=True, whole_word=False),
    RiskSignal("twine upload", RiskClass.RC4, "package publish", owner_gate=True, whole_word=False),
    RiskSignal("cargo publish", RiskClass.RC4, "package publish", owner_gate=True, whole_word=False),
    RiskSignal("post publicly", RiskClass.RC4, "public posting", owner_gate=True, whole_word=False),
    RiskSignal("public post", RiskClass.RC4, "public posting", owner_gate=True, whole_word=False),
    RiskSignal("tweet", RiskClass.RC4, "public posting", owner_gate=True),
    RiskSignal("merge to main", RiskClass.RC4, "merge to main", owner_gate=True, whole_word=False),
    RiskSignal("merge into main", RiskClass.RC4, "merge to main", owner_gate=True, whole_word=False),
    RiskSignal("merge pr to main", RiskClass.RC4, "merge to main", owner_gate=True, whole_word=False),
    RiskSignal("merge main", RiskClass.RC4, "merge to main", owner_gate=True, whole_word=False),
    RiskSignal("force push", RiskClass.RC4, "force push", owner_gate=True, whole_word=False),
    RiskSignal("git push --force", RiskClass.RC4, "force push", owner_gate=True, whole_word=False),
    RiskSignal("--force-with-lease", RiskClass.RC4, "force push", owner_gate=True, whole_word=False),
    RiskSignal("--force", RiskClass.RC4, "force push", owner_gate=True, whole_word=False),
    RiskSignal("git reset --hard", RiskClass.RC4, "destructive git", owner_gate=True, whole_word=False),
    RiskSignal("dns change", RiskClass.RC4, "dns change", owner_gate=True, whole_word=False),
    RiskSignal("dns record", RiskClass.RC4, "dns change", owner_gate=True, whole_word=False),
    RiskSignal("domain transfer", RiskClass.RC4, "dns change", owner_gate=True, whole_word=False),
    RiskSignal("update dns", RiskClass.RC4, "dns change", owner_gate=True, whole_word=False),
    RiskSignal("change dns", RiskClass.RC4, "dns change", owner_gate=True, whole_word=False),
    RiskSignal("app store", RiskClass.RC4, "app store submission", owner_gate=True, whole_word=False),
    RiskSignal("play store", RiskClass.RC4, "app store submission", owner_gate=True, whole_word=False),
    RiskSignal("submit build", RiskClass.RC4, "app store submission", owner_gate=True, whole_word=False),
    RiskSignal("testflight", RiskClass.RC4, "app store submission", owner_gate=True),
    RiskSignal("spend money", RiskClass.RC4, "money", owner_gate=True, whole_word=False),
    RiskSignal("spend ", RiskClass.RC4, "money", owner_gate=True, whole_word=False),
    RiskSignal("purchase", RiskClass.RC4, "money", owner_gate=True),
    RiskSignal("billing", RiskClass.RC4, "money", owner_gate=True),
    RiskSignal("charge card", RiskClass.RC4, "money", owner_gate=True, whole_word=False),
    RiskSignal("buy a domain", RiskClass.RC4, "money", owner_gate=True, whole_word=False),
    RiskSignal("create account", RiskClass.RC4, "third-party account", owner_gate=True, whole_word=False),
    RiskSignal("create third-party account", RiskClass.RC4, "third-party account", owner_gate=True, whole_word=False),
    RiskSignal("third-party account", RiskClass.RC4, "third-party account", owner_gate=True, whole_word=False),
    RiskSignal("rotate secret", RiskClass.RC4, "secret rotation", owner_gate=True, whole_word=False),
    RiskSignal("rotate credentials", RiskClass.RC4, "secret rotation", owner_gate=True, whole_word=False),
    RiskSignal("oauth change", RiskClass.RC4, "credential change", owner_gate=True, whole_word=False),
    RiskSignal("change oauth", RiskClass.RC4, "credential change", owner_gate=True, whole_word=False),

    # RC4 risk surface that is not itself owner-gated but carries the same
    # severity (regulated / compliance / health / financial claims).
    RiskSignal("regulated", RiskClass.RC4, "regulated claim"),
    RiskSignal("hipaa", RiskClass.RC4, "regulated claim"),
    RiskSignal("fda", RiskClass.RC4, "regulated claim"),
    RiskSignal("49 cfr", RiskClass.RC4, "regulated claim", whole_word=False),
    RiskSignal("legal claim", RiskClass.RC4, "regulated claim", whole_word=False),
    RiskSignal("health claim", RiskClass.RC4, "regulated claim", whole_word=False),
    RiskSignal("financial claim", RiskClass.RC4, "regulated claim", whole_word=False),
    RiskSignal("compliance claim", RiskClass.RC4, "regulated claim", whole_word=False),

    # ------------------------------------------------------------------ RC3
    # Repo mutations, pull requests, dependency installs, network calls,
    # credential-adjacent edits. Not owner-gated by default.
    RiskSignal("git push", RiskClass.RC3, "git push", whole_word=False),
    RiskSignal("git commit", RiskClass.RC3, "git commit", whole_word=False),
    RiskSignal("git rebase", RiskClass.RC3, "git rebase", whole_word=False),
    RiskSignal("git merge", RiskClass.RC3, "git merge", whole_word=False),
    RiskSignal("git branch -d", RiskClass.RC3, "delete branch", whole_word=False),
    RiskSignal("git branch -D", RiskClass.RC3, "delete branch", whole_word=False),
    RiskSignal("create pr", RiskClass.RC3, "pull request", whole_word=False),
    RiskSignal("open pr", RiskClass.RC3, "pull request", whole_word=False),
    RiskSignal("open a pull request", RiskClass.RC3, "pull request", whole_word=False),
    RiskSignal("pull request", RiskClass.RC3, "pull request", whole_word=False),
    RiskSignal("draft pr", RiskClass.RC3, "pull request", whole_word=False),
    RiskSignal("pip install", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("pip uninstall", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("npm install", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("npm add", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("yarn add", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("pnpm add", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("uv add", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("uv pip install", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("pipx install", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("apt install", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("brew install", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("cargo add", RiskClass.RC3, "dependency change", whole_word=False),
    RiskSignal("curl ", RiskClass.RC3, "network call", whole_word=False),
    RiskSignal("wget ", RiskClass.RC3, "network call", whole_word=False),
    RiskSignal("http://", RiskClass.RC3, "network call", whole_word=False),
    RiskSignal("https://", RiskClass.RC3, "network call", whole_word=False),
    RiskSignal("fetch http", RiskClass.RC3, "network call", whole_word=False),
    RiskSignal("api key", RiskClass.RC3, "credentials", whole_word=False),
    RiskSignal("oauth", RiskClass.RC3, "credentials"),
    RiskSignal("secret", RiskClass.RC3, "credentials"),
    RiskSignal("token", RiskClass.RC3, "credentials"),
    RiskSignal("credential", RiskClass.RC3, "credentials"),
    RiskSignal("credentials", RiskClass.RC3, "credentials"),
    RiskSignal(".env", RiskClass.RC3, "credentials", whole_word=False),

    # ------------------------------------------------------------------ RC2
    # Local code edits that stay inside the working tree.
    RiskSignal("edit file", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("edit hermes_cli", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("refactor", RiskClass.RC2, "refactor"),
    RiskSignal("rename function", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("rename variable", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("rename method", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("fix bug", RiskClass.RC2, "fix bug", whole_word=False),
    RiskSignal("add a test", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("add test", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("write test", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("modify code", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("change function", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("update function", RiskClass.RC2, "edit code", whole_word=False),
    RiskSignal("implement function", RiskClass.RC2, "edit code", whole_word=False),

    # ------------------------------------------------------------------ RC1
    # Local planning / docs / drafting work.
    RiskSignal("/plan", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("/audit", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("/builder", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("/operator", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("/strategy", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("/critic", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("/council", RiskClass.RC1, "planning command", whole_word=False),
    RiskSignal("draft", RiskClass.RC1, "draft doc"),
    RiskSignal("outline", RiskClass.RC1, "draft doc"),
    RiskSignal("write notes", RiskClass.RC1, "draft doc", whole_word=False),
    RiskSignal("write a doc", RiskClass.RC1, "draft doc", whole_word=False),
    RiskSignal("update doc", RiskClass.RC1, "draft doc", whole_word=False),
    RiskSignal("update docs", RiskClass.RC1, "draft doc", whole_word=False),
    RiskSignal("summarize", RiskClass.RC1, "draft doc"),
    RiskSignal("summary", RiskClass.RC1, "draft doc"),
)


def _matches(text_lower: str, signal: RiskSignal) -> bool:
    """Return True if ``signal.pattern`` is present in the lowercased text."""
    pattern = signal.pattern.lower()
    if signal.whole_word:
        return re.search(r"\b" + re.escape(pattern) + r"\b", text_lower) is not None
    return pattern in text_lower


def classify(text: str | None) -> RiskAssessment:
    """Classify a free-text intent or work-packet description.

    ``None`` and the empty / whitespace-only string both return an RC0
    assessment with no matched signals. Matching is case-insensitive; the
    highest tier matched wins. ``matched_signals`` preserves the order of
    rows in :data:`SIGNALS`, which keeps RC4 owner-gated phrases at the
    front of the tuple.

    Negation is **not** parsed: "don't deploy" still classifies as RC4.
    Callers should treat RC4 as "requires owner review" — never as a safety
    oracle for whether an action will actually be executed.
    """
    if text is None:
        text = ""
    text_lower = text.lower()
    if not text_lower.strip():
        return RiskAssessment(
            risk_class=RiskClass.RC0,
            rationale="RC0: no risk signals matched.",
            matched_signals=(),
            owner_gates=(),
        )

    matched: list[RiskSignal] = [sig for sig in SIGNALS if _matches(text_lower, sig)]
    if not matched:
        return RiskAssessment(
            risk_class=RiskClass.RC0,
            rationale="RC0: no risk signals matched.",
            matched_signals=(),
            owner_gates=(),
        )

    top = max(sig.risk_class for sig in matched)
    # Dedupe by label, preserving SIGNALS order.
    seen_labels: set[str] = set()
    matched_labels: list[str] = []
    seen_gates: set[str] = set()
    gate_labels: list[str] = []
    for sig in matched:
        if sig.label not in seen_labels:
            matched_labels.append(sig.label)
            seen_labels.add(sig.label)
        if sig.owner_gate and sig.label not in seen_gates:
            gate_labels.append(sig.label)
            seen_gates.add(sig.label)

    if gate_labels:
        rationale = (
            f"RC{int(top)}: matched {', '.join(matched_labels)} "
            f"(owner gates: {', '.join(gate_labels)})."
        )
    else:
        rationale = f"RC{int(top)}: matched {', '.join(matched_labels)}."

    return RiskAssessment(
        risk_class=top,
        rationale=rationale,
        matched_signals=tuple(matched_labels),
        owner_gates=tuple(gate_labels),
    )


def is_owner_gated(text: str | None) -> bool:
    """True iff any signal flagged ``owner_gate=True`` fires for ``text``.

    This is intentionally narrower than ``classify(text).risk_class == RC4``:
    regulated / compliance claims classify as RC4 because of their severity
    but do not require the same kind of owner approval flow as a deploy or
    merge. Use this when deciding whether to halt for explicit
    "Yes, with authorization." confirmation.
    """
    return bool(owner_gates_for(text))


def owner_gates_for(text: str | None) -> tuple[str, ...]:
    """Return the unique owner-gate labels that fired for ``text``.

    Order matches :data:`SIGNALS`. Empty tuple when none fire.
    """
    return classify(text).owner_gates


def max_class_for(*labels: str) -> RiskClass:
    """Compute the highest risk class for a set of pre-categorized labels.

    Useful when a caller has already decomposed a work packet into signal
    labels (e.g. from a structured form) and wants to skip the regex pass.
    Unknown labels are ignored. Returns :data:`RiskClass.RC0` when no label
    is recognised or the call has no arguments.
    """
    label_to_class: dict[str, RiskClass] = {}
    for sig in SIGNALS:
        existing = label_to_class.get(sig.label)
        if existing is None or sig.risk_class > existing:
            label_to_class[sig.label] = sig.risk_class

    top = RiskClass.RC0
    for label in labels:
        rc = label_to_class.get(label)
        if rc is not None and rc > top:
            top = rc
    return top


__all__ = (
    "RiskClass",
    "RiskSignal",
    "RiskAssessment",
    "SIGNALS",
    "classify",
    "is_owner_gated",
    "owner_gates_for",
    "max_class_for",
)
