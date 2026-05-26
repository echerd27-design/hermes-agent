"""Tests for the JARVIS Prime owner-authorization gate.

Covers Wave 02 acceptance criteria:

* Exact phrase required.
* Near misses fail.
* Case/spacing behavior is documented (asserted via docstring + tests).
* Unknown gated actions fail closed.
* Tests cover all gated action categories.
* Gate summary shows pending actions clearly.

Plus a registry-drift detector that fails loudly if the canonical
phrase diverges from ``skills/aos-enterprise-council/operating-registry/registry.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.jarvis_prime import gates as gates_mod
from hermes_cli.jarvis_prime import owner_auth
from hermes_cli.jarvis_prime.gates import (
    ACTION_DESCRIPTIONS,
    GateLedger,
    PendingGate,
    format_gate_summary,
)
from hermes_cli.jarvis_prime.owner_auth import (
    OWNER_GATE_PHRASE,
    AuthorizationError,
    GatedAction,
    PhraseMismatchError,
    UnknownActionError,
    authorize,
    resolve_action,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_JSON = (
    REPO_ROOT
    / "skills"
    / "aos-enterprise-council"
    / "operating-registry"
    / "registry.json"
)


# ── Canonical phrase + enum invariants ────────────────────────────────────


def test_owner_gate_phrase_literal_is_canonical() -> None:
    """The constant must equal the exact 24-character canonical literal."""
    assert OWNER_GATE_PHRASE == "Yes, with authorization."
    assert len(OWNER_GATE_PHRASE) == 24


def test_owner_gate_phrase_matches_registry_json() -> None:
    """Drift detector: registry.json's owner_gate_phrase must match this module."""
    data = json.loads(REGISTRY_JSON.read_text())
    assert data["policies"]["owner_gate_phrase"] == OWNER_GATE_PHRASE


def test_gated_action_has_exactly_ten_members() -> None:
    assert len(GatedAction) == 10


def test_gated_action_member_names_match_documented_set() -> None:
    expected = {
        "SPEND_MONEY",
        "PUBLIC_POST",
        "ACCOUNT_CREATION",
        "OAUTH_CREDENTIAL_CHANGE",
        "PROD_DEPLOY",
        "DNS_CHANGE",
        "MAIN_MERGE",
        "PACKAGE_PUBLISH",
        "APP_STORE_SUBMIT",
        "REGULATED_CLAIM",
    }
    assert {member.name for member in GatedAction} == expected


def test_action_descriptions_cover_every_gated_action() -> None:
    assert set(ACTION_DESCRIPTIONS) == set(GatedAction)


# ── Happy path: exact phrase authorizes every category ──────────────────


@pytest.mark.parametrize("action", list(GatedAction), ids=lambda a: a.name)
def test_authorize_succeeds_for_every_category_with_exact_phrase(
    action: GatedAction,
) -> None:
    assert authorize(action, OWNER_GATE_PHRASE) is action


def test_authorize_accepts_string_value_for_action() -> None:
    assert authorize("spend_money", OWNER_GATE_PHRASE) is GatedAction.SPEND_MONEY


def test_resolve_action_returns_member_for_enum_input() -> None:
    assert resolve_action(GatedAction.PROD_DEPLOY) is GatedAction.PROD_DEPLOY


def test_resolve_action_returns_member_for_string_input() -> None:
    assert resolve_action("dns_change") is GatedAction.DNS_CHANGE


# ── Near-miss rejection ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "near_miss",
    [
        pytest.param("yes, with authorization.", id="lowercase-y"),
        pytest.param("YES, WITH AUTHORIZATION.", id="all-caps"),
        pytest.param("Yes, with Authorization.", id="title-case-last-word"),
        pytest.param("Yes, with authorization", id="missing-period"),
        pytest.param("Yes with authorization.", id="missing-comma"),
        pytest.param("Yes,  with authorization.", id="double-space-after-comma"),
        pytest.param(" Yes, with authorization.", id="leading-space"),
        pytest.param("Yes, with authorization. ", id="trailing-space"),
        pytest.param("Yes, with authorization.\n", id="trailing-newline"),
        pytest.param("\tYes, with authorization.", id="leading-tab"),
        pytest.param("Yes,with authorization.", id="no-space-after-comma"),
        pytest.param("Yes, with  authorization.", id="double-space-after-with"),
        pytest.param("Yes; with authorization.", id="semicolon-not-comma"),
        pytest.param("", id="empty-string"),
        pytest.param("yes", id="truncated"),
        pytest.param("Yes, with authorization!", id="exclamation-not-period"),
    ],
)
def test_authorize_rejects_near_miss_phrases(near_miss: str) -> None:
    with pytest.raises(PhraseMismatchError):
        authorize(GatedAction.SPEND_MONEY, near_miss)


@pytest.mark.parametrize(
    "non_string_phrase", [None, 42, 3.14, ["Yes, with authorization."]]
)
def test_authorize_rejects_non_string_phrase(non_string_phrase: object) -> None:
    with pytest.raises(PhraseMismatchError):
        authorize(GatedAction.SPEND_MONEY, non_string_phrase)


# ── Unknown actions fail closed ───────────────────────────────────────────


def test_unknown_action_string_fails_closed_with_correct_phrase() -> None:
    """Unknown action raises UnknownActionError even with the exact phrase."""
    with pytest.raises(UnknownActionError):
        authorize("delete_universe", OWNER_GATE_PHRASE)


def test_unknown_action_string_fails_closed_with_wrong_phrase() -> None:
    """Unknown action raises UnknownActionError before the phrase is checked."""
    with pytest.raises(UnknownActionError):
        authorize("delete_universe", "wrong")


@pytest.mark.parametrize(
    "bad_action",
    [None, 42, 3.14, object(), b"spend_money", ["spend_money"], {"spend_money": True}],
)
def test_unknown_action_type_fails_closed(bad_action: object) -> None:
    with pytest.raises(UnknownActionError):
        authorize(bad_action, OWNER_GATE_PHRASE)  # type: ignore[invalid-argument-type]


def test_resolve_action_unknown_string_raises() -> None:
    with pytest.raises(UnknownActionError):
        resolve_action("not_a_real_action")


# ── Exception hierarchy ───────────────────────────────────────────────────


def test_phrase_mismatch_is_authorization_error() -> None:
    assert issubclass(PhraseMismatchError, AuthorizationError)


def test_unknown_action_is_authorization_error() -> None:
    assert issubclass(UnknownActionError, AuthorizationError)


def test_broad_except_catches_phrase_mismatch() -> None:
    with pytest.raises(AuthorizationError):
        authorize(GatedAction.SPEND_MONEY, "nope")


def test_broad_except_catches_unknown_action() -> None:
    with pytest.raises(AuthorizationError):
        authorize("unknown", OWNER_GATE_PHRASE)


# ── GateLedger behavior ──────────────────────────────────────────────────


def test_empty_ledger_summary_says_none() -> None:
    ledger = GateLedger()
    summary = ledger.summary()
    assert "Pending owner gates (0)" in summary
    assert "none" in summary


def test_ledger_request_returns_pending_gate() -> None:
    ledger = GateLedger()
    entry = ledger.request(GatedAction.PROD_DEPLOY, "deploy v2.1")
    assert entry.action is GatedAction.PROD_DEPLOY
    assert entry.context == "deploy v2.1"
    assert ledger.pending() == (entry,)


def test_ledger_request_accepts_string_action() -> None:
    ledger = GateLedger()
    entry = ledger.request("public_post", "blog post")
    assert entry.action is GatedAction.PUBLIC_POST


def test_ledger_request_rejects_unknown_action() -> None:
    ledger = GateLedger()
    with pytest.raises(UnknownActionError):
        ledger.request("delete_universe", "context")
    assert ledger.pending() == ()


def test_ledger_summary_lists_all_pending_with_context() -> None:
    ledger = GateLedger()
    ledger.request(GatedAction.PROD_DEPLOY, "deploy hermes-gateway v2.1.0")
    ledger.request(GatedAction.SPEND_MONEY, "purchase $500 OpenAI credits")
    ledger.request(GatedAction.PUBLIC_POST, "publish announcement blog post")

    summary = ledger.summary()
    assert "Pending owner gates (3):" in summary
    assert "PROD_DEPLOY" in summary
    assert "SPEND_MONEY" in summary
    assert "PUBLIC_POST" in summary
    assert "deploy hermes-gateway v2.1.0" in summary
    assert "purchase $500 OpenAI credits" in summary
    assert "publish announcement blog post" in summary
    # Descriptions render too.
    assert "production deploys, infra rollouts" in summary


def test_ledger_confirm_with_correct_phrase_removes_entry() -> None:
    ledger = GateLedger()
    ledger.request(GatedAction.DNS_CHANGE, "rotate apex A record")
    assert len(ledger.pending()) == 1
    removed = ledger.confirm(GatedAction.DNS_CHANGE, OWNER_GATE_PHRASE)
    assert removed.action is GatedAction.DNS_CHANGE
    assert removed.context == "rotate apex A record"
    assert ledger.pending() == ()


def test_ledger_confirm_with_wrong_phrase_keeps_entry() -> None:
    ledger = GateLedger()
    entry = ledger.request(GatedAction.DNS_CHANGE, "rotate apex A record")
    with pytest.raises(PhraseMismatchError):
        ledger.confirm(GatedAction.DNS_CHANGE, "yes, with authorization.")
    assert ledger.pending() == (entry,)


def test_ledger_confirm_unknown_action_fails_closed() -> None:
    ledger = GateLedger()
    ledger.request(GatedAction.DNS_CHANGE, "rotate apex A record")
    with pytest.raises(UnknownActionError):
        ledger.confirm("delete_universe", OWNER_GATE_PHRASE)
    # Pending entry unchanged.
    assert len(ledger.pending()) == 1


def test_ledger_confirm_with_no_matching_pending_raises() -> None:
    ledger = GateLedger()
    with pytest.raises(AuthorizationError):
        ledger.confirm(GatedAction.MAIN_MERGE, OWNER_GATE_PHRASE)


def test_ledger_confirm_removes_only_first_match_fifo() -> None:
    ledger = GateLedger()
    first = ledger.request(GatedAction.SPEND_MONEY, "first request")
    second = ledger.request(GatedAction.SPEND_MONEY, "second request")
    removed = ledger.confirm(GatedAction.SPEND_MONEY, OWNER_GATE_PHRASE)
    assert removed is first
    assert ledger.pending() == (second,)


def test_format_gate_summary_accepts_iterable_of_pending_gates() -> None:
    pending = [
        PendingGate(action=GatedAction.PROD_DEPLOY, context="deploy", requested_at=0.0),
    ]
    summary = format_gate_summary(pending)
    assert "PROD_DEPLOY" in summary
    assert "deploy" in summary


def test_format_gate_summary_accepts_ledger() -> None:
    ledger = GateLedger()
    ledger.request(GatedAction.PROD_DEPLOY, "deploy")
    assert format_gate_summary(ledger) == ledger.summary()


def test_format_gate_summary_is_deterministic_snapshot() -> None:
    """Lock the documented format so it can't drift silently."""
    pending = [
        PendingGate(
            action=GatedAction.PROD_DEPLOY,
            context="deploy hermes-gateway v2.1.0 to prod-us-east",
            requested_at=0.0,
        ),
        PendingGate(
            action=GatedAction.SPEND_MONEY,
            context="purchase $500 OpenAI credits",
            requested_at=1.0,
        ),
        PendingGate(
            action=GatedAction.PUBLIC_POST,
            context="publish announcement blog post",
            requested_at=2.0,
        ),
    ]
    expected = (
        "Pending owner gates (3):\n"
        "  - PROD_DEPLOY: production deploys, infra rollouts\n"
        "      context: deploy hermes-gateway v2.1.0 to prod-us-east\n"
        "  - SPEND_MONEY: charges, purchases, paid API calls, subscriptions\n"
        "      context: purchase $500 OpenAI credits\n"
        "  - PUBLIC_POST: tweets, blog posts, public PRs, public Slack messages\n"
        "      context: publish announcement blog post"
    )
    assert format_gate_summary(pending) == expected


def test_format_gate_summary_omits_context_line_when_empty() -> None:
    pending = [PendingGate(action=GatedAction.MAIN_MERGE, requested_at=0.0)]
    summary = format_gate_summary(pending)
    assert "MAIN_MERGE" in summary
    assert "context:" not in summary


# ── Module surface invariants ─────────────────────────────────────────────


def test_module_exports_match_documented_public_api() -> None:
    """Catch accidental removal/renaming of public names."""
    assert set(owner_auth.__all__) == {
        "OWNER_GATE_PHRASE",
        "GatedAction",
        "AuthorizationError",
        "PhraseMismatchError",
        "UnknownActionError",
        "authorize",
        "resolve_action",
    }
    assert set(gates_mod.__all__) == {
        "ACTION_DESCRIPTIONS",
        "PendingGate",
        "GateLedger",
        "format_gate_summary",
    }
