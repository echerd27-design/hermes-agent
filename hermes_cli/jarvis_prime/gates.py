"""Pending owner-gate ledger and summary formatting for JARVIS Prime.

Wraps :mod:`hermes_cli.jarvis_prime.owner_auth` with a tiny in-process
ledger so callers can register pending high-impact actions, display them
to the owner clearly, and then confirm with the canonical phrase.

The ledger is intentionally a single-process object — not a persistent
store. Subsequent waves can introduce persistence (Slack thread, kanban
task, structured log) without changing this surface.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Union

from .owner_auth import (
    AuthorizationError,
    GatedAction,
    authorize,
    resolve_action,
)

__all__ = [
    "ACTION_DESCRIPTIONS",
    "PendingGate",
    "GateLedger",
    "format_gate_summary",
]


ACTION_DESCRIPTIONS: Mapping[GatedAction, str] = {
    GatedAction.SPEND_MONEY: "charges, purchases, paid API calls, subscriptions",
    GatedAction.PUBLIC_POST: "tweets, blog posts, public PRs, public Slack messages",
    GatedAction.ACCOUNT_CREATION: "new SaaS accounts, new tenants",
    GatedAction.OAUTH_CREDENTIAL_CHANGE: (
        "OAuth grants, secret rotation, token issuance"
    ),
    GatedAction.PROD_DEPLOY: "production deploys, infra rollouts",
    GatedAction.DNS_CHANGE: "DNS record edits, domain transfers",
    GatedAction.MAIN_MERGE: "merges to main/master branches",
    GatedAction.PACKAGE_PUBLISH: "npm/PyPI/cargo publish, container push",
    GatedAction.APP_STORE_SUBMIT: "App Store / Play Store submissions",
    GatedAction.REGULATED_CLAIM: (
        "legal, compliance, security, health, financial, or regulated claims"
    ),
}

# Drift guard — if a category is added to GatedAction without a matching
# description, surface it at import time instead of producing a blank in
# the summary at runtime.
assert set(ACTION_DESCRIPTIONS) == set(GatedAction), (
    "ACTION_DESCRIPTIONS is out of sync with GatedAction"
)


@dataclass(frozen=True)
class PendingGate:
    """A gated action that has been requested but not yet confirmed."""

    action: GatedAction
    context: str = ""
    requested_at: float = field(default_factory=time.monotonic)


class GateLedger:
    """Tracks pending owner-gated actions in a single process."""

    def __init__(self) -> None:
        self._pending: list[PendingGate] = []

    def request(self, action: Union[GatedAction, str], context: str = "") -> PendingGate:
        """Register a pending gated action.

        ``action`` is coerced via :func:`resolve_action`, so unknown
        categories raise :class:`~hermes_cli.jarvis_prime.owner_auth.UnknownActionError`
        rather than silently entering the ledger.
        """
        resolved = resolve_action(action)
        entry = PendingGate(action=resolved, context=context)
        self._pending.append(entry)
        return entry

    def confirm(
        self, action: Union[GatedAction, str], phrase: object
    ) -> PendingGate:
        """Authorize and remove the first pending entry for ``action``.

        Calls :func:`authorize` to validate the phrase. If no pending
        entry exists for the resolved action, raises
        :class:`AuthorizationError` so a caller cannot accidentally
        confirm an action that was never requested.
        """
        resolved = authorize(action, phrase)
        for idx, entry in enumerate(self._pending):
            if entry.action is resolved:
                return self._pending.pop(idx)
        raise AuthorizationError(
            f"no pending owner gate for action {resolved.value!r}"
        )

    def pending(self) -> tuple[PendingGate, ...]:
        """Return a read-only snapshot of pending entries."""
        return tuple(self._pending)

    def summary(self) -> str:
        """Render a deterministic, line-oriented summary of pending gates."""
        return format_gate_summary(self._pending)


def format_gate_summary(
    pending: Union["GateLedger", Iterable[PendingGate]],
) -> str:
    """Format pending owner gates as a deterministic multi-line string.

    Accepts either a :class:`GateLedger` or any iterable of
    :class:`PendingGate` instances. Output format is line-oriented and
    safe for snapshot tests.
    """
    if isinstance(pending, GateLedger):
        entries: tuple[PendingGate, ...] = pending.pending()
    else:
        entries = tuple(pending)

    if not entries:
        return "Pending owner gates (0): none"

    lines = [f"Pending owner gates ({len(entries)}):"]
    for entry in entries:
        description = ACTION_DESCRIPTIONS[entry.action]
        lines.append(f"  - {entry.action.name}: {description}")
        if entry.context:
            lines.append(f"      context: {entry.context}")
    return "\n".join(lines)
