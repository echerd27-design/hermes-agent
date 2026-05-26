"""Tests for hermes_cli.jarvis_prime.event_spine.

Covers every public function, every documented event type, the secret
detection rules, the JSONL round-trip, and the namespace-package import
assumption.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hermes_cli.jarvis_prime import event_spine as es


# ---------------------------------------------------------------------------
# Enum & module surface
# ---------------------------------------------------------------------------

EXPECTED_EVENT_TYPES: set[str] = {
    "jarvis.message.received",
    "jarvis.message.responded",
    "jarvis.presence.changed",
    "jarvis.task.created",
    "jarvis.task.phase.changed",
    "jarvis.task.blocked",
    "jarvis.task.completed",
    "jarvis.worker.started",
    "jarvis.worker.finished",
    "jarvis.approval.requested",
    "jarvis.approval.granted",
    "jarvis.approval.denied",
    "jarvis.memory.created",
    "jarvis.memory.updated",
    "jarvis.proof.created",
    "jarvis.notification.requested",
    "jarvis.emergency_stop.triggered",
    "jarvis.gateway.connected",
    "jarvis.gateway.disconnected",
}


def test_event_type_count_is_19() -> None:
    assert len(es.EventType) == 19
    assert len(es.EVENT_TYPES) == 19


def test_event_types_match_contract() -> None:
    assert {e.value for e in es.EventType} == EXPECTED_EVENT_TYPES
    assert es.EVENT_TYPES == frozenset(EXPECTED_EVENT_TYPES)


def test_namespace_package_import_works() -> None:
    mod = importlib.import_module("hermes_cli.jarvis_prime.event_spine")
    assert mod is es
    assert hasattr(mod, "Event")
    assert hasattr(mod, "new_event")


def test_module_is_stdlib_only() -> None:
    source = Path(es.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top_level_modules.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    non_stdlib = {m for m in top_level_modules if m not in stdlib and m != "__future__"}
    assert non_stdlib == set(), f"non-stdlib imports detected: {non_stdlib}"


# ---------------------------------------------------------------------------
# Per-event-type construction
# ---------------------------------------------------------------------------


def _minimal_payload(et: es.EventType) -> dict:
    if et is es.EventType.MESSAGE_RECEIVED:
        return {"preview": "hi"}
    if et is es.EventType.MESSAGE_RESPONDED:
        return {"preview": "ok"}
    if et is es.EventType.PRESENCE_CHANGED:
        return {"state": "online"}
    if et in (es.EventType.TASK_CREATED, es.EventType.TASK_PHASE_CHANGED):
        return {"title": "do thing", "phase": "plan"}
    if et is es.EventType.TASK_BLOCKED:
        return {"reason": "needs approval"}
    if et is es.EventType.TASK_COMPLETED:
        return {"title": "done"}
    if et is es.EventType.WORKER_STARTED:
        return {"worker": "alpha"}
    if et is es.EventType.WORKER_FINISHED:
        return {"worker": "alpha", "duration_ms": 1234}
    if et is es.EventType.APPROVAL_REQUESTED:
        return {"summary": "deploy x"}
    if et in (es.EventType.APPROVAL_GRANTED, es.EventType.APPROVAL_DENIED):
        return {"decision": "yes"}
    if et in (es.EventType.MEMORY_CREATED, es.EventType.MEMORY_UPDATED):
        return {"title": "remembered"}
    if et is es.EventType.PROOF_CREATED:
        return {"kind": "screenshot"}
    if et is es.EventType.NOTIFICATION_REQUESTED:
        return {"text": "ping"}
    if et is es.EventType.EMERGENCY_STOP_TRIGGERED:
        return {"reason": "panic"}
    if et in (es.EventType.GATEWAY_CONNECTED, es.EventType.GATEWAY_DISCONNECTED):
        return {"gateway": "wss://example"}
    return {}


@pytest.mark.parametrize("et", list(es.EventType))
def test_construct_every_event_type(et: es.EventType) -> None:
    event = es.new_event(
        et,
        source="router",
        subject=f"subj-{et.name}",
        payload=_minimal_payload(et),
    )
    assert event.type == et.value
    assert event.id and len(event.id) == 32
    assert event.ts.endswith("Z")
    round_trip = es.Event.from_dict(event.to_dict())
    assert round_trip == event
    rendered = es.render_mobile(event)
    assert isinstance(rendered, str)
    assert 0 < len(rendered) <= 120
    assert "\n" not in rendered


# ---------------------------------------------------------------------------
# Validation — positives
# ---------------------------------------------------------------------------


def test_validate_payload_accepts_nested_json_types() -> None:
    payload = {
        "s": "text",
        "i": 1,
        "f": 1.5,
        "b": True,
        "n": None,
        "list": [1, 2, "three", None, [4, 5]],
        "nested": {"a": {"b": {"c": [{"d": "e"}]}}},
        "unicode": "héllo 世界",
    }
    out = es.validate_payload(payload)
    assert out == payload


def test_validate_payload_normalizes_tuples_to_lists() -> None:
    payload = {"xs": (1, 2, (3, 4))}
    out = es.validate_payload(payload)
    assert out == {"xs": [1, 2, [3, 4]]}


# ---------------------------------------------------------------------------
# Validation — negatives
# ---------------------------------------------------------------------------


def test_validate_payload_rejects_bytes() -> None:
    with pytest.raises(es.InvalidPayloadError, match="bytes"):
        es.validate_payload({"data": b"abc"})


def test_validate_payload_rejects_set() -> None:
    with pytest.raises(es.InvalidPayloadError, match="set"):
        es.validate_payload({"xs": {1, 2}})


def test_validate_payload_rejects_datetime() -> None:
    with pytest.raises(es.InvalidPayloadError, match="datetime"):
        es.validate_payload({"when": datetime.now(timezone.utc)})


def test_validate_payload_rejects_custom_class() -> None:
    class Foo:
        pass

    with pytest.raises(es.InvalidPayloadError):
        es.validate_payload({"x": Foo()})


def test_validate_payload_rejects_nan() -> None:
    with pytest.raises(es.InvalidPayloadError, match="non-finite"):
        es.validate_payload({"x": math.nan})


def test_validate_payload_rejects_inf() -> None:
    with pytest.raises(es.InvalidPayloadError, match="non-finite"):
        es.validate_payload({"x": math.inf})


def test_validate_payload_rejects_non_string_key() -> None:
    with pytest.raises(es.InvalidPayloadError, match="non-string key"):
        es.validate_payload({1: "x"})  # type: ignore[dict-item]


def test_validate_payload_rejects_oversize() -> None:
    big = {"blob": "x" * (es.MAX_PAYLOAD_BYTES + 1)}
    with pytest.raises(es.InvalidPayloadError, match="MAX_PAYLOAD_BYTES"):
        es.validate_payload(big)


def test_validate_payload_rejects_non_dict_root() -> None:
    with pytest.raises(es.InvalidPayloadError, match="payload must be a dict"):
        es.validate_payload([1, 2, 3])  # type: ignore[arg-type]


def test_error_message_names_key_path() -> None:
    with pytest.raises(es.InvalidPayloadError) as exc:
        es.validate_payload({"a": {"b": [0, b"bad"]}})
    assert "a.b[1]" in str(exc.value)


# ---------------------------------------------------------------------------
# Secret rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "token",
        "TOKEN",
        "api_key",
        "apiKey",
        "apikey",
        "password",
        "PASSWD",
        "secret",
        "client_secret",
        "bearer",
        "authorization",
        "Authorization",
        "session_key",
        "private_key",
        "refresh_token",
        "access_token",
        "user_token",  # substring match
        "my_password_field",
    ],
)
def test_validate_rejects_secret_keys(key: str) -> None:
    with pytest.raises(es.SecretInPayloadError) as exc:
        es.validate_payload({key: "abc"})
    assert "secret-shaped key" in str(exc.value)


SECRET_VALUE_SAMPLES = [
    "sk-abcdef0123456789ABCDEF",
    "Bearer abcdef0123456789ABCDEF",
    "bearer ABCDEFGHIJKLMNOP_QRSTUVWX",
    "ghp_" + "a" * 36,
    "github_pat_" + "X" * 30,
    "AKIAABCDEFGHIJKLMNOP",
    "xoxb-1234567890-abcdef",
]


@pytest.mark.parametrize("val", SECRET_VALUE_SAMPLES)
def test_validate_rejects_secret_value_patterns(val: str) -> None:
    with pytest.raises(es.SecretInPayloadError) as exc:
        es.validate_payload({"note": val})
    msg = str(exc.value)
    assert val not in msg
    assert "secret-shaped value" in msg


def test_secret_in_nested_list() -> None:
    with pytest.raises(es.SecretInPayloadError) as exc:
        es.validate_payload({"items": [{"x": "sk-abcdef0123456789ABCDEF"}]})
    assert "items[0].x" in str(exc.value)


# ---------------------------------------------------------------------------
# redact_payload
# ---------------------------------------------------------------------------


def test_redact_payload_replaces_secret_keys() -> None:
    out = es.redact_payload({"token": "xyz", "ok": "fine"})
    assert out == {"token": es.REDACTED_PLACEHOLDER, "ok": "fine"}


def test_redact_payload_replaces_secret_values() -> None:
    out = es.redact_payload({"note": "sk-abcdef0123456789ABCDEF", "ok": "fine"})
    assert out["note"] == es.REDACTED_PLACEHOLDER
    assert out["ok"] == "fine"


def test_redact_payload_handles_nested_structures() -> None:
    src = {
        "a": [{"token": "x"}, "Bearer abcdef0123456789ABCDEF", "fine"],
        "b": {"nested": {"password": "y"}, "ok": "still ok"},
    }
    out = es.redact_payload(src)
    assert out["a"][0]["token"] == es.REDACTED_PLACEHOLDER
    assert out["a"][1] == es.REDACTED_PLACEHOLDER
    assert out["a"][2] == "fine"
    assert out["b"]["nested"]["password"] == es.REDACTED_PLACEHOLDER
    assert out["b"]["ok"] == "still ok"


def test_redact_payload_does_not_mutate_input() -> None:
    src = {"token": "secret-thing", "nested": {"password": "p"}}
    snapshot = json.dumps(src, sort_keys=True)
    es.redact_payload(src)
    assert json.dumps(src, sort_keys=True) == snapshot


def test_redact_payload_requires_dict() -> None:
    with pytest.raises(es.InvalidPayloadError):
        es.redact_payload("nope")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Event / new_event / from_dict strictness
# ---------------------------------------------------------------------------


def test_event_is_frozen() -> None:
    e = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.id = "x"  # type: ignore[misc]


def test_from_dict_rejects_unknown_keys() -> None:
    e = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    d = e.to_dict()
    d["extra"] = "no"
    with pytest.raises(es.InvalidPayloadError, match="unknown top-level keys"):
        es.Event.from_dict(d)


def test_from_dict_rejects_missing_type() -> None:
    e = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    d = e.to_dict()
    del d["type"]
    with pytest.raises(es.InvalidPayloadError, match="missing required field"):
        es.Event.from_dict(d)


def test_from_dict_rejects_missing_source() -> None:
    e = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    d = e.to_dict()
    del d["source"]
    with pytest.raises(es.InvalidPayloadError, match="missing required field"):
        es.Event.from_dict(d)


def test_from_dict_rejects_unknown_type() -> None:
    e = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    d = e.to_dict()
    d["type"] = "jarvis.not.a.thing"
    with pytest.raises(es.UnknownEventTypeError):
        es.Event.from_dict(d)


def test_from_dict_rejects_newer_schema_version() -> None:
    e = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    d = e.to_dict()
    d["schema_version"] = es.SCHEMA_VERSION + 1
    with pytest.raises(es.EventSpineError, match="exceeds known SCHEMA_VERSION"):
        es.Event.from_dict(d)


def test_from_dict_requires_dict() -> None:
    with pytest.raises(es.InvalidPayloadError):
        es.Event.from_dict("oops")  # type: ignore[arg-type]


def test_from_json_rejects_bad_json() -> None:
    with pytest.raises(es.InvalidPayloadError, match="invalid JSON"):
        es.Event.from_json("{not json")


def test_event_requires_non_empty_source() -> None:
    with pytest.raises(es.InvalidPayloadError, match="source"):
        es.new_event(es.EventType.MESSAGE_RECEIVED, source="")


def test_event_rejects_bool_schema_version() -> None:
    with pytest.raises(es.InvalidPayloadError, match="schema_version"):
        es.Event(
            id="a" * 32,
            type=es.EventType.MESSAGE_RECEIVED.value,
            ts="2026-05-26T00:00:00.000000Z",
            source="router",
            schema_version=True,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# JSON determinism
# ---------------------------------------------------------------------------


def test_to_json_is_deterministic() -> None:
    fixed_id = "a" * 32
    fixed_ts = "2026-05-26T00:00:00.000000Z"
    a = es.new_event(
        es.EventType.TASK_CREATED,
        source="router",
        subject="t1",
        payload={"title": "do x", "phase": "plan"},
        id=fixed_id,
        ts=fixed_ts,
    )
    b = es.new_event(
        es.EventType.TASK_CREATED,
        source="router",
        subject="t1",
        payload={"phase": "plan", "title": "do x"},  # different insertion order
        id=fixed_id,
        ts=fixed_ts,
    )
    assert a.to_json() == b.to_json()


# ---------------------------------------------------------------------------
# JSONL round-trip
# ---------------------------------------------------------------------------


def test_jsonl_round_trip_every_event_type(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "spine.jsonl"
    written: list[es.Event] = []
    for et in es.EventType:
        ev = es.new_event(et, source="router", payload=_minimal_payload(et))
        es.append_jsonl(path, ev)
        written.append(ev)
    assert path.exists()
    read = list(es.read_jsonl(path))
    assert read == written


def test_jsonl_skips_empty_lines(tmp_path: Path) -> None:
    path = tmp_path / "spine.jsonl"
    ev = es.new_event(es.EventType.MESSAGE_RECEIVED, source="router")
    es.append_jsonl(path, ev)
    with open(path, "ab") as f:
        f.write(b"\n   \n")
    es.append_jsonl(path, ev)
    read = list(es.read_jsonl(path))
    assert len(read) == 2
    assert all(e == ev for e in read)


def test_append_jsonl_rejects_non_event(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        es.append_jsonl(tmp_path / "x.jsonl", {"not": "an event"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# render_mobile specifics
# ---------------------------------------------------------------------------


def test_render_mobile_drops_jarvis_prefix() -> None:
    ev = es.new_event(
        es.EventType.MESSAGE_RECEIVED,
        source="router",
        payload={"preview": "hi"},
        ts="2026-05-26T12:34:56.000000Z",
    )
    out = es.render_mobile(ev)
    assert "jarvis.message.received" not in out
    assert "message.received" in out
    assert "12:34:56" in out


def test_render_mobile_includes_subject_when_set() -> None:
    ev = es.new_event(
        es.EventType.TASK_BLOCKED,
        source="router",
        subject="task-42",
        payload={"reason": "needs approval"},
    )
    out = es.render_mobile(ev)
    assert "task-42" in out
    assert "needs approval" in out


def test_render_mobile_strips_control_chars() -> None:
    ev = es.new_event(
        es.EventType.NOTIFICATION_REQUESTED,
        source="router",
        payload={"text": "hello\nworld\x00!"},
    )
    out = es.render_mobile(ev)
    assert "\n" not in out
    assert "\x00" not in out


def test_render_mobile_truncates_at_120() -> None:
    ev = es.new_event(
        es.EventType.NOTIFICATION_REQUESTED,
        source="router",
        subject="s",
        payload={"text": "x" * 500},
    )
    out = es.render_mobile(ev)
    assert len(out) <= 120
    assert out.endswith("…")


def test_render_mobile_worker_finished_includes_duration() -> None:
    ev = es.new_event(
        es.EventType.WORKER_FINISHED,
        source="router",
        payload={"worker": "alpha", "duration_ms": 1500},
    )
    out = es.render_mobile(ev)
    assert "alpha" in out
    assert "1500ms" in out


def test_render_mobile_requires_event() -> None:
    with pytest.raises(TypeError):
        es.render_mobile({"not": "event"})  # type: ignore[arg-type]
