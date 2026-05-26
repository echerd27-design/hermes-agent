"""Tests for ``hermes_cli.jarvis_prime.session``."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from hermes_cli.jarvis_prime import (
    Session,
    Surface,
    derive_session_id,
    is_valid_session_id,
)


_FIXED_TS = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)


def _make_session(surface: str = "cli", **overrides: Any) -> Session:
    fields: dict[str, Any] = {
        "user_id": "jeremiah",
        "active_job_id": "job-42",
        "last_mode": "builder",
        "created_at": _FIXED_TS,
        "updated_at": _FIXED_TS,
        "metadata": {"client": "test"},
    }
    fields.update(overrides)
    return Session(surface=surface, **fields)


class TestSurfaceEnum:
    """Surface enum exposes the six supported surfaces."""

    def test_six_values(self):
        assert Surface.CLI.value == "cli"
        assert Surface.SLACK.value == "slack"
        assert Surface.TERMUX.value == "termux"
        assert Surface.ANDROID.value == "android"
        assert Surface.GATEWAY.value == "gateway"
        assert Surface.VOICE.value == "voice"

    def test_no_extra_values(self):
        assert {s.value for s in Surface} == {
            "cli", "slack", "termux", "android", "gateway", "voice"
        }


class TestDeterministicId:
    """``derive_session_id`` is deterministic and surface-discriminating."""

    def test_same_inputs_same_id(self):
        a = derive_session_id("cli", "jeremiah", _FIXED_TS)
        b = derive_session_id("cli", "jeremiah", _FIXED_TS)
        assert a == b
        assert is_valid_session_id(a)

    @pytest.mark.parametrize(
        "surface_a, surface_b",
        [
            ("cli", "slack"),
            ("termux", "android"),
            ("voice", "gateway"),
        ],
    )
    def test_different_surfaces_different_ids(self, surface_a, surface_b):
        a = derive_session_id(surface_a, "jeremiah", _FIXED_TS)
        b = derive_session_id(surface_b, "jeremiah", _FIXED_TS)
        assert a != b

    def test_different_users_different_ids(self):
        a = derive_session_id("cli", "jeremiah", _FIXED_TS)
        b = derive_session_id("cli", "someone-else", _FIXED_TS)
        assert a != b

    def test_is_valid_session_id_rejects_garbage(self):
        assert not is_valid_session_id("not-a-uuid")
        assert not is_valid_session_id("")
        assert not is_valid_session_id(None)
        assert not is_valid_session_id(12345)


class TestSessionConstruction:
    """Session validates surface and session_id on construction."""

    def test_invalid_surface_raises(self):
        with pytest.raises(ValueError, match="invalid surface"):
            Session(surface="email")

    def test_auto_generated_session_id_is_uuid(self):
        s = Session(surface="cli")
        assert is_valid_session_id(s.session_id)

    def test_explicit_invalid_session_id_raises(self):
        with pytest.raises(ValueError, match="invalid session_id"):
            Session(surface="cli", session_id="not-a-uuid")

    def test_explicit_valid_session_id_preserved(self):
        sid = derive_session_id("cli", "jeremiah", _FIXED_TS)
        s = Session(surface="cli", session_id=sid)
        assert s.session_id == sid

    def test_naive_created_at_coerced_to_utc(self):
        naive = datetime(2026, 5, 26, 12, 0, 0)
        s = Session(surface="cli", created_at=naive)
        assert s.created_at.tzinfo is not None
        assert s.created_at.utcoffset() == timedelta(0)


class TestSerializationRoundTrip:
    """``to_dict`` / ``from_dict`` and ``to_json`` / ``from_json`` are lossless."""

    def test_dict_round_trip(self):
        original = _make_session()
        restored = Session.from_dict(original.to_dict())
        assert restored.to_dict() == original.to_dict()

    def test_json_round_trip(self):
        original = _make_session()
        restored = Session.from_json(original.to_json())
        assert restored.to_dict() == original.to_dict()

    @pytest.mark.parametrize("surface", ["termux", "android", "voice"])
    def test_mobile_surfaces_round_trip(self, surface):
        original = _make_session(surface=surface)
        restored = Session.from_json(original.to_json())
        assert restored.surface == surface
        assert restored.to_dict() == original.to_dict()

    def test_nested_metadata_round_trips(self):
        original = _make_session(
            metadata={"nested": {"a": 1, "b": [1, 2, 3]}, "flag": True}
        )
        restored = Session.from_json(original.to_json())
        assert restored.metadata == {
            "nested": {"a": 1, "b": [1, 2, 3]},
            "flag": True,
        }

    def test_from_dict_ignores_unknown_keys(self):
        payload = _make_session().to_dict()
        payload["future_field"] = "ignored"
        payload["another"] = {"deep": "value"}
        restored = Session.from_dict(payload)
        assert restored.surface == "cli"
        assert "future_field" not in restored.to_dict()

    def test_from_dict_rejects_non_dict_metadata(self):
        payload = _make_session().to_dict()
        payload["metadata"] = "not-a-dict"
        with pytest.raises(ValueError, match="metadata must be a dict"):
            Session.from_dict(payload)

    def test_from_dict_requires_surface(self):
        with pytest.raises(ValueError, match="missing required field 'surface'"):
            Session.from_dict({"session_id": "anything"})


class TestTouch:
    """``touch`` advances ``updated_at`` without mutating ``session_id``."""

    def test_touch_advances_updated_at(self):
        s = Session(surface="cli", created_at=_FIXED_TS, updated_at=_FIXED_TS)
        original_updated = s.updated_at
        s.touch()
        assert s.updated_at >= original_updated
        assert s.updated_at > _FIXED_TS

    def test_touch_preserves_session_id(self):
        s = Session(surface="cli")
        sid_before = s.session_id
        s.touch()
        assert s.session_id == sid_before
