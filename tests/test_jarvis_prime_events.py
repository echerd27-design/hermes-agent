"""Tests for hermes_cli.jarvis_prime.events (ACI Wave 08).

Coverage targets:
- Every event name in the wave spec round-trips through the envelope.
- Required fields and JSON safety are validated at construction time.
- Secrets are scrubbed by both key-name and value-shape, with a small
  allowlist to spare commit SHAs / content hashes.
- ``to_json`` is deterministic and ``Event`` is frozen.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

import pytest

from hermes_cli.jarvis_prime import Event, EventType
from hermes_cli.jarvis_prime.events import REDACTED


# Every event type required by the Wave 08 spec.
ALL_TYPES: list[str] = [
    "message.received",
    "mode.classified",
    "route.selected",
    "memory.recalled",
    "task.created",
    "worker.started",
    "worker.finished",
    "gate.failed",
    "owner.approval.required",
    "test.finished",
    "pr.created",
    "notification.sent",
    "memory.saved",
]


# ── Type coverage ─────────────────────────────────────────────────────────


def test_event_type_enum_matches_spec_exactly() -> None:
    enum_values = {t.value for t in EventType}
    assert enum_values == set(ALL_TYPES), (
        f"EventType drift: missing={set(ALL_TYPES) - enum_values}, "
        f"extra={enum_values - set(ALL_TYPES)}"
    )


@pytest.mark.parametrize("type_value", ALL_TYPES)
def test_each_event_type_constructs_and_roundtrips(type_value: str) -> None:
    e = Event.new(type_value, source="test.suite", payload={"k": "v", "n": 1})

    assert e.type == type_value
    assert e.source == "test.suite"
    assert e.payload == {"k": "v", "n": 1}
    assert e.redactions == ()

    assert re.fullmatch(r"[0-9a-f]{32}", e.event_id), e.event_id
    parsed = datetime.fromisoformat(e.timestamp)
    assert parsed.tzinfo is not None, "timestamp must be timezone-aware"

    # Dict round-trip
    assert Event.from_dict(e.to_dict()) == e
    # JSON round-trip
    assert Event.from_dict(json.loads(e.to_json())) == e


@pytest.mark.parametrize("type_value", ALL_TYPES)
def test_each_event_type_accepts_enum_or_string(type_value: str) -> None:
    enum_match = next(t for t in EventType if t.value == type_value)
    e_str = Event.new(type_value, source="t", payload={})
    e_enum = Event.new(enum_match, source="t", payload={})
    assert e_str.type == e_enum.type == type_value


# ── Required-field validation ─────────────────────────────────────────────


def test_unknown_type_rejected() -> None:
    with pytest.raises(ValueError, match="unknown event type"):
        Event.new("does.not.exist", source="t", payload={})


def test_empty_source_rejected() -> None:
    with pytest.raises(ValueError, match="source"):
        Event.new(EventType.MESSAGE_RECEIVED, source="", payload={})


def test_non_dict_payload_rejected() -> None:
    with pytest.raises(ValueError, match="payload"):
        Event.new(  # type: ignore[arg-type]
            EventType.MESSAGE_RECEIVED, source="t", payload=["not", "a", "dict"]
        )


def test_non_string_dict_key_rejected() -> None:
    with pytest.raises(ValueError, match="non-string dict key"):
        Event.new(  # type: ignore[dict-item]
            EventType.MESSAGE_RECEIVED, source="t", payload={1: "v"}
        )


def test_from_dict_requires_all_fields() -> None:
    full = Event.new(EventType.TASK_CREATED, source="t", payload={}).to_dict()
    for key in ("event_id", "type", "timestamp", "source", "payload"):
        partial = {k: v for k, v in full.items() if k != key}
        with pytest.raises(ValueError, match="missing required field"):
            Event.from_dict(partial)


def test_from_dict_rejects_non_iso_timestamp() -> None:
    e = Event.new(EventType.TASK_CREATED, source="t", payload={})
    bad = e.to_dict()
    bad["timestamp"] = "not-a-timestamp"
    with pytest.raises(ValueError, match="ISO"):
        Event.from_dict(bad)


def test_from_dict_rejects_unknown_type() -> None:
    e = Event.new(EventType.TASK_CREATED, source="t", payload={}).to_dict()
    e["type"] = "made.up.event"
    with pytest.raises(ValueError, match="unknown event type"):
        Event.from_dict(e)


# ── JSON safety ───────────────────────────────────────────────────────────


def test_payload_auto_converts_datetime_uuid_path_enum_set() -> None:
    class Color(Enum):
        BLUE = "blue"

    e = Event.new(
        EventType.WORKER_STARTED,
        source="t",
        payload={
            "dt": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "d": date(2026, 1, 2),
            "id": uuid.UUID("12345678-1234-5678-1234-567812345678"),
            "p": Path("/tmp/foo"),
            "color": Color.BLUE,
            "tags": {"a", "b"},
        },
    )

    assert e.payload["dt"].startswith("2026-01-01T00:00:00")
    assert e.payload["d"] == "2026-01-02"
    assert e.payload["id"] == "12345678-1234-5678-1234-567812345678"
    assert e.payload["p"] == "/tmp/foo"
    assert e.payload["color"] == "blue"
    assert sorted(e.payload["tags"]) == ["a", "b"]

    # Full JSON serialization round-trips
    parsed = json.loads(e.to_json())
    assert parsed["payload"]["color"] == "blue"


@pytest.mark.parametrize(
    "bad_value",
    [object(), complex(1, 2), b"bytes", lambda: None],
)
def test_non_json_safe_payload_rejected(bad_value: object) -> None:
    with pytest.raises(ValueError, match="not JSON-safe"):
        Event.new(
            EventType.MESSAGE_RECEIVED, source="t", payload={"x": bad_value}
        )


@pytest.mark.parametrize(
    "bad_float",
    [float("nan"), float("inf"), float("-inf")],
)
def test_nan_and_inf_rejected(bad_float: float) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        Event.new(
            EventType.MESSAGE_RECEIVED, source="t", payload={"x": bad_float}
        )


def test_nested_lists_and_dicts_survive_roundtrip() -> None:
    payload = {
        "task": {
            "id": "T-001",
            "subtasks": [
                {"name": "build", "ok": True},
                {"name": "test", "ok": False},
            ],
        },
        "tags": ["wave-08", "events"],
    }
    e = Event.new(EventType.TASK_CREATED, source="t", payload=payload)
    assert e.payload == payload
    assert Event.from_dict(json.loads(e.to_json())) == e


# ── Secret redaction: key-name ────────────────────────────────────────────


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "password",
        "secret",
        "token",
        "access_token",
        "client_secret",
        "private_key",
        "authorization",
        "OPENAI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "MY_OAUTH_TOKEN",
    ],
)
def test_secret_named_keys_redacted(key: str) -> None:
    e = Event.new(
        EventType.MESSAGE_RECEIVED,
        source="t",
        payload={key: "any-value-here-doesnt-matter", "user": "jeremiah"},
    )
    assert e.payload[key] == REDACTED
    assert e.payload["user"] == "jeremiah"
    assert key in e.redactions


def test_empty_value_under_secret_key_not_redacted() -> None:
    """Empty/None values under a secret key aren't redacted — nothing
    to hide, and redacting would create a misleading audit trail."""
    e = Event.new(
        EventType.MESSAGE_RECEIVED,
        source="t",
        payload={"api_key": "", "token": None, "secret": []},
    )
    assert e.payload["api_key"] == ""
    assert e.payload["token"] is None
    assert e.payload["secret"] == []
    assert e.redactions == ()


def test_nonsecret_named_keys_pass_through() -> None:
    """Words that merely contain the substring 'token' (e.g.
    'tokenization') aren't treated as credentials."""
    e = Event.new(
        EventType.MODE_CLASSIFIED,
        source="t",
        payload={
            "tokenization_method": "bpe",
            "secrets_count": 0,
            "tokens_used": 1234,
        },
    )
    assert e.payload["tokenization_method"] == "bpe"
    assert e.payload["secrets_count"] == 0
    assert e.payload["tokens_used"] == 1234
    assert e.redactions == ()


# ── Secret redaction: value-shape ─────────────────────────────────────────
#
# Fixture values below are *constructed at runtime* from split string
# fragments so that the literal credential-shaped tokens never appear
# verbatim in source. This keeps GitHub push protection / static
# secret scanners from flagging the test file while still producing
# values that match each redaction regex when assembled.

_LONG_LOWER = "abcdefghijklmnopqrstuvwxyz1234567890"   # 36 chars
_LONG_UPPER = "ABCDEFGHIJKLMNOP"                       # 16 chars [A-Z]
_LONG_ALPHA = "a" * 30                                  # 30 chars

# Anthropic / OpenAI / GitHub / AWS / Slack / JWT / Bearer / PEM
_FAKE_ANTHROPIC = "s" + "k-ant-" + _LONG_LOWER
_FAKE_OPENAI = "s" + "k-" + _LONG_LOWER
_FAKE_GITHUB_PAT = "gh" + "p_" + _LONG_LOWER
_FAKE_GITHUB_OAUTH = "gh" + "o_" + _LONG_LOWER
_FAKE_AWS = "AK" + "IA" + _LONG_UPPER
_FAKE_SLACK_BOT = "xo" + "x" + "b-" + "1234567890-" + _LONG_LOWER[:20]
_FAKE_JWT = "ey" + "Jhdr" + _LONG_ALPHA + "." + "ey" + "Jpld" + _LONG_ALPHA + "." + _LONG_ALPHA
_FAKE_BEARER = "Bea" + "rer " + _LONG_LOWER
_FAKE_PEM_HEADER = "---" + "--BEGIN RSA PRIVATE KEY-----"


@pytest.mark.parametrize(
    "secret_value",
    [
        _FAKE_ANTHROPIC,
        _FAKE_OPENAI,
        _FAKE_GITHUB_PAT,
        _FAKE_GITHUB_OAUTH,
        _FAKE_AWS,
        _FAKE_SLACK_BOT,
        _FAKE_JWT,
        _FAKE_BEARER,
        _FAKE_PEM_HEADER,
    ],
)
def test_secret_shaped_values_redacted_under_innocuous_key(
    secret_value: str,
) -> None:
    e = Event.new(
        EventType.NOTIFICATION_SENT,
        source="t",
        payload={"note": secret_value},
    )
    assert e.payload["note"] == REDACTED, f"shape leak: {secret_value!r}"
    assert "note" in e.redactions


def test_nested_secret_redacted_with_dotted_path() -> None:
    e = Event.new(
        EventType.NOTIFICATION_SENT,
        source="t",
        payload={
            "request": {
                "headers": {"Authorization": _FAKE_BEARER},
                "method": "POST",
            }
        },
    )
    assert e.payload["request"]["headers"]["Authorization"] == REDACTED
    assert e.payload["request"]["method"] == "POST"
    assert "request.headers.Authorization" in e.redactions


def test_secret_inside_list_redacted_with_index_path() -> None:
    e = Event.new(
        EventType.WORKER_FINISHED,
        source="t",
        payload={
            "args": ["--user", "jeremiah", "--token", _FAKE_GITHUB_PAT]
        },
    )
    assert e.payload["args"][3] == REDACTED
    assert "args[3]" in e.redactions
    assert e.payload["args"][0] == "--user"
    assert e.payload["args"][1] == "jeremiah"


def test_high_entropy_string_under_unknown_key_redacted() -> None:
    e = Event.new(
        EventType.NOTIFICATION_SENT,
        source="t",
        payload={"opaque": "A" * 50},
    )
    assert e.payload["opaque"] == REDACTED
    assert "opaque" in e.redactions


# ── Allowlist ─────────────────────────────────────────────────────────────


def test_event_id_top_level_field_never_redacted() -> None:
    """The Event.event_id is a top-level field, not in the payload, so
    it must never be touched by the payload-only redactor."""
    e = Event.new(EventType.PR_CREATED, source="t", payload={})
    assert e.event_id != REDACTED
    j = json.loads(e.to_json())
    assert j["event_id"] == e.event_id


@pytest.mark.parametrize(
    "key,value",
    [
        ("commit_sha", "abcdef1234567890abcdef1234567890abcdef12"),
        ("sha", "deadbeef" * 5),
        ("content_hash", "a" * 64),
        ("event_id", "f" * 32),
        ("trace_id", "9e2b" * 10),
    ],
)
def test_allowlisted_keys_preserved_even_when_high_entropy(
    key: str, value: str
) -> None:
    e = Event.new(EventType.PR_CREATED, source="t", payload={key: value})
    assert e.payload[key] == value
    assert e.redactions == ()


# ── Determinism ───────────────────────────────────────────────────────────


def test_explicit_event_id_and_timestamp_honored() -> None:
    e = Event.new(
        EventType.GATE_FAILED,
        source="t",
        payload={"reason": "tests failed"},
        event_id="fixed1234567890",
        timestamp="2026-05-26T18:48:00+00:00",
    )
    assert e.event_id == "fixed1234567890"
    assert e.timestamp == "2026-05-26T18:48:00+00:00"


def test_to_json_uses_sorted_top_level_keys() -> None:
    e = Event.new(
        EventType.MODE_CLASSIFIED,
        source="t",
        payload={"z": 1, "a": 2, "m": 3},
        event_id="x",
        timestamp="2026-05-26T18:48:00+00:00",
    )
    out = e.to_json()
    expected_order = [
        '"event_id"',
        '"payload"',
        '"redactions"',
        '"source"',
        '"timestamp"',
        '"type"',
    ]
    positions = [out.find(k) for k in expected_order]
    assert all(p >= 0 for p in positions), f"missing key in JSON: {out}"
    assert positions == sorted(positions), f"to_json keys not sorted: {out}"


def test_to_json_is_stable_across_calls() -> None:
    e = Event.new(
        EventType.OWNER_APPROVAL_REQUIRED,
        source="t",
        payload={"task": "deploy", "owner": "jeremiah"},
        event_id="x",
        timestamp="2026-05-26T18:48:00+00:00",
    )
    assert e.to_json() == e.to_json()


# ── Frozen-ness ───────────────────────────────────────────────────────────


def test_event_is_frozen() -> None:
    e = Event.new(EventType.TASK_CREATED, source="t", payload={})
    with pytest.raises(FrozenInstanceError):
        e.event_id = "different"  # type: ignore[misc]


def test_event_payload_is_independent_copy() -> None:
    """Mutating the input dict after construction must not affect the
    stored payload (the JSON-safety pass builds a fresh dict)."""
    src = {"k": "v"}
    e = Event.new(EventType.TASK_CREATED, source="t", payload=src)
    src["k"] = "mutated"
    assert e.payload == {"k": "v"}
