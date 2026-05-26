"""Secret-like content redaction for context payloads.

Standalone — does NOT import from ``agent/redact.py``. That module is for
log-display redaction (preserves head/tail chars for debuggability). This
module is for payload redaction: every match is fully replaced by a typed
placeholder ``[REDACTED:<kind>]`` so downstream evidence extractors can
pattern-match the placeholder shape instead of accidentally capturing a
secret.

Mirror lag: if ``agent/redact.py`` gains a new vendor prefix, a follow-up
wave should mirror it here.
"""

from __future__ import annotations

import re
from typing import Pattern


def _placeholder(kind: str) -> str:
    return f"[REDACTED:{kind}]"


# (kind, compiled_pattern, replacement-builder)
# Each replacement is either a fixed placeholder (`lambda m: _placeholder(...)`)
# or a callable that preserves non-secret prefix/suffix groups around the
# secret (e.g. keep ``Authorization: Bearer`` prefix, replace token only).

def _full(kind: str):
    return lambda _m: _placeholder(kind)


def _bearer(_m: re.Match[str]) -> str:
    prefix = _m.group(0).split(_m.group(1))[0]
    return prefix + _placeholder("auth_bearer")


def _env_assign(m: re.Match[str]) -> str:
    name = m.group(1)
    quote = m.group(2) or ""
    return f"{name}={quote}{_placeholder('env_assign_secret')}{quote}"


def _json_field(m: re.Match[str]) -> str:
    key = m.group(1)
    return f'{key}: "{_placeholder("json_field_secret")}"'


def _db_connstr(m: re.Match[str]) -> str:
    return f"{m.group(1)}{_placeholder('db_connstr')}{m.group(3)}"


_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"
)
_AUTH_BEARER_RE = re.compile(
    r"(?i)Authorization:\s*Bearer\s+(\S+)"
)
_ENV_ASSIGN_RE = re.compile(
    r"([A-Z][A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH))\s*=\s*"
    r"(['\"]?)([^\s'\"]+)\2"
)
_JSON_FIELD_RE = re.compile(
    r'("(?:api_?key|access_token|refresh_token|auth_token|bearer|token|secret|password)")'
    r'\s*:\s*"([^"]+)"',
    re.IGNORECASE,
)
_DB_CONNSTR_RE = re.compile(
    r"((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:]+:)([^@\s]+)(@)",
    re.IGNORECASE,
)


# Vendor-prefix patterns mirror the subset of ``agent/redact.py`` most likely
# to appear in model/tool payloads. Phone numbers, Discord mentions, Telegram
# bot tokens are intentionally omitted — payload-irrelevant bloat.
_VENDOR_PREFIX_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    ("openai_sk", re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b")),
    ("github_pat_classic", re.compile(r"\bghp_[A-Za-z0-9]{10,}\b")),
    ("github_pat_fine_grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{10,}\b")),
    ("github_oauth", re.compile(r"\bgh[ousr]_[A-Za-z0-9]{10,}\b")),
    ("slack_token", re.compile(r"\b(?:xox[baprs]|xapp)-[A-Za-z0-9-]{10,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    ("gcp_api_key", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_=-]{4,}){0,2}\b")),
)


# The public ordering matters: structured matchers (private keys, bearer
# headers, env-assign, json-field, db connection strings) run before the
# vendor-prefix scanners so a secret embedded in a structured context is
# replaced once and only once, never double-substituted.
SECRET_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
    ("private_key_block", _PRIVATE_KEY_RE),
    ("auth_bearer", _AUTH_BEARER_RE),
    ("env_assign_secret", _ENV_ASSIGN_RE),
    ("json_field_secret", _JSON_FIELD_RE),
    ("db_connstr", _DB_CONNSTR_RE),
) + _VENDOR_PREFIX_PATTERNS


_STRUCTURED_REPLACERS = {
    "private_key_block": _full("private_key_block"),
    "auth_bearer": _bearer,
    "env_assign_secret": _env_assign,
    "json_field_secret": _json_field,
    "db_connstr": _db_connstr,
}


def scrub(text: str) -> tuple[str, int]:
    """Replace every secret-like match with a typed placeholder.

    Returns ``(cleaned_text, count_redacted)``. The count totals every
    individual match across every pattern. Callers can record the count in
    a packet warning to keep an audit trail without re-running the scanner.
    """

    if not text:
        return text, 0

    total = 0
    out = text
    for kind, pattern in SECRET_PATTERNS:
        if kind in _STRUCTURED_REPLACERS:
            replacer = _STRUCTURED_REPLACERS[kind]
        else:
            replacer = _full(kind)
        out, n = pattern.subn(replacer, out)
        total += n
    return out, total


def reject(text: str) -> str | None:
    """Return the kind of the first secret seen, or ``None`` if clean.

    Designed for callers who would rather refuse the payload than redact
    it (e.g. an upstream surface that pre-validates user-supplied tool
    output before handing it to the compressor).
    """

    if not text:
        return None
    for kind, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return kind
    return None
