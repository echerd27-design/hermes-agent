"""Tests for hermes_cli.context.context_packet."""

import dataclasses
import json

import pytest

from hermes_cli.context import ContextPacket


class TestContextPacket:
    def _sample(self) -> ContextPacket:
        return ContextPacket(
            source_type="text",
            payload="compressed body",
            original_length=400,
            compressed_length=15,
            preserved_evidence=(
                ("file_path", "hermes_cli/foo.py"),
                ("line_ref", "hermes_cli/foo.py:42"),
            ),
            warnings=("redacted 1 secret-like tokens",),
            artifact_ref="stash://abc",
        )

    def test_frozen_dataclass_immutable(self):
        p = self._sample()
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.payload = "tampered"  # type: ignore[misc]

    def test_compression_ratio_normal_case(self):
        p = self._sample()
        assert p.compression_ratio == pytest.approx(15 / 400)

    def test_compression_ratio_empty_input_returns_one(self):
        p = ContextPacket(
            source_type="text",
            payload="",
            original_length=0,
            compressed_length=0,
        )
        assert p.compression_ratio == 1.0

    def test_compression_ratio_handles_zero_compressed(self):
        p = ContextPacket(
            source_type="text",
            payload="",
            original_length=100,
            compressed_length=0,
        )
        assert p.compression_ratio == 0.0

    def test_to_dict_serializes_preserved_evidence_as_list_of_pairs(self):
        p = self._sample()
        d = p.to_dict()
        assert d["preserved_evidence"] == [
            ["file_path", "hermes_cli/foo.py"],
            ["line_ref", "hermes_cli/foo.py:42"],
        ]
        # round-trip through JSON to confirm the shape is wire-safe.
        parsed = json.loads(json.dumps(d))
        assert parsed["source_type"] == "text"
        assert parsed["artifact_ref"] == "stash://abc"

    def test_from_dict_round_trip(self):
        p = self._sample()
        d = p.to_dict()
        restored = ContextPacket.from_dict(d)
        assert restored == p

    def test_from_dict_tolerates_missing_optional_fields(self):
        minimal = {
            "source_type": "log",
            "payload": "x",
            "original_length": 1,
            "compressed_length": 1,
        }
        p = ContextPacket.from_dict(minimal)
        assert p.preserved_evidence == ()
        assert p.warnings == ()
        assert p.artifact_ref is None

    def test_source_type_and_evidence_kinds_are_closed_tuples(self):
        from hermes_cli.context import EVIDENCE_KINDS, SOURCE_TYPES

        assert isinstance(SOURCE_TYPES, tuple)
        assert isinstance(EVIDENCE_KINDS, tuple)
        # No accidental overlap between the two registries.
        assert not (set(SOURCE_TYPES) & set(EVIDENCE_KINDS))
