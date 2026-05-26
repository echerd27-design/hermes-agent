"""Owner-authorization gate primitive for JARVIS Prime.

Hardens the free-text owner phrase documented in ``AGENTS.md`` (JARVIS
Prime section) into an enforceable Python API. Every high-impact action
must be routed through :func:`authorize` with a typed :class:`GatedAction`
and the exact owner phrase. The check is byte-for-byte equality against
:data:`OWNER_GATE_PHRASE` — no normalization, no fuzzy match.

Case and spacing behavior
-------------------------
The comparison is **strict**:

* Case-sensitive. ``"yes, with authorization."`` fails.
* Whitespace-significant. A trailing newline, trailing space, leading
  tab, or double-space inside the phrase fails. The expected literal is
  ``"Yes, with authorization."`` — 24 characters, one space after the
  comma, one space after ``with``, terminating period.
* Punctuation-significant. Missing period, missing comma, or substituted
  punctuation all fail.

Fail-closed unknown actions
---------------------------
``authorize`` resolves the action argument **before** comparing the
phrase. A caller passing an unknown action string (or a non-string,
non-enum value) raises :class:`UnknownActionError` regardless of whether
the phrase is correct. Unknown gated actions never authorize.

Cross-reference
---------------
The literal :data:`OWNER_GATE_PHRASE` mirrors:

* ``skills/aos-enterprise-council/operating-registry/registry.json``
  (key ``policies.owner_gate_phrase``)
* ``skills/aos-enterprise-council/scripts/verify_registry.py``
  (constant ``OWNER_GATE_VALUE``)

The test suite asserts the JSON registry value still matches this
constant, so silent drift fails CI loudly.
"""

from __future__ import annotations

from enum import Enum
from typing import Final, Union

__all__ = [
    "OWNER_GATE_PHRASE",
    "GatedAction",
    "AuthorizationError",
    "PhraseMismatchError",
    "UnknownActionError",
    "authorize",
    "resolve_action",
]


OWNER_GATE_PHRASE: Final[str] = "Yes, with authorization."


class GatedAction(str, Enum):
    """High-impact action categories that require owner authorization."""

    SPEND_MONEY = "spend_money"
    PUBLIC_POST = "public_post"
    ACCOUNT_CREATION = "account_creation"
    OAUTH_CREDENTIAL_CHANGE = "oauth_credential_change"
    PROD_DEPLOY = "prod_deploy"
    DNS_CHANGE = "dns_change"
    MAIN_MERGE = "main_merge"
    PACKAGE_PUBLISH = "package_publish"
    APP_STORE_SUBMIT = "app_store_submit"
    REGULATED_CLAIM = "regulated_claim"


class AuthorizationError(Exception):
    """Base class for owner-authorization failures."""


class PhraseMismatchError(AuthorizationError):
    """Raised when the owner phrase does not exactly match the canonical literal."""


class UnknownActionError(AuthorizationError):
    """Raised when the gated-action argument does not resolve to a known category."""


ActionLike = Union[GatedAction, str]


def resolve_action(action: object) -> GatedAction:
    """Coerce ``action`` to a :class:`GatedAction` member or fail closed.

    Accepts a :class:`GatedAction` member or its string value. Anything
    else — including unknown strings, ``None``, integers, or other types
    — raises :class:`UnknownActionError`.
    """
    if isinstance(action, GatedAction):
        return action
    if isinstance(action, str):
        try:
            return GatedAction(action)
        except ValueError as exc:
            raise UnknownActionError(
                f"unknown gated action: {action!r}"
            ) from exc
    raise UnknownActionError(
        f"gated action must be GatedAction or str, got {type(action).__name__}"
    )


def authorize(action: ActionLike, phrase: object) -> GatedAction:
    """Validate the owner phrase for a gated action.

    Resolves ``action`` first (raises :class:`UnknownActionError` on
    unknown categories regardless of ``phrase``), then compares ``phrase``
    to :data:`OWNER_GATE_PHRASE` byte-for-byte. Raises
    :class:`PhraseMismatchError` on any mismatch — including case,
    whitespace, and punctuation differences.

    Returns the resolved :class:`GatedAction` on success so callers can
    chain into typed downstream logic.
    """
    resolved = resolve_action(action)
    if not isinstance(phrase, str) or phrase != OWNER_GATE_PHRASE:
        raise PhraseMismatchError(
            "owner authorization phrase did not match "
            "the exact canonical literal"
        )
    return resolved
