"""Tests for hermes_cli.jarvis_prime.verification — packet shape, validation, aggregation.

Covers pass/fail/skipped entries, validation errors, packet aggregation,
JSON output shape (so the JARVIS Test Gate can consume it), the summarize_text
helper, and the acceptance guardrail that the module does not execute commands.
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.jarvis_prime import verification
from hermes_cli.jarvis_prime.verification import (
    FAILED,
    PASSED,
    SKIPPED,
    VerificationEntry,
    VerificationPacket,
    summarize_text,
)


class TestVerificationEntry:
    """VerificationEntry construction, validation, and to_dict round-trip."""

    def test_passed_entry_preserves_fields(self):
        entry = VerificationEntry(
            command="pytest tests/test_jarvis_prime_verification.py",
            cwd="/repo",
            status=PASSED,
            exit_code=0,
            duration_seconds=1.23,
            stdout_summary="3 passed",
            stderr_summary="",
            artifacts=["junit.xml"],
            timestamp="2026-05-26T12:00:00+00:00",
        )

        data = entry.to_dict()
        assert data["command"] == "pytest tests/test_jarvis_prime_verification.py"
        assert data["cwd"] == "/repo"
        assert data["status"] == PASSED
        assert data["exit_code"] == 0
        assert data["duration_seconds"] == 1.23
        assert data["stdout_summary"] == "3 passed"
        assert data["stderr_summary"] == ""
        assert data["artifacts"] == ["junit.xml"]
        assert data["skip_reason"] is None
        assert data["timestamp"] == "2026-05-26T12:00:00+00:00"

    def test_failed_entry_preserves_non_zero_exit(self):
        entry = VerificationEntry(
            command="pytest",
            cwd="/repo",
            status=FAILED,
            exit_code=1,
            stderr_summary="AssertionError: nope",
        )

        assert entry.status == FAILED
        assert entry.exit_code == 1
        assert entry.stderr_summary == "AssertionError: nope"

    def test_skipped_entry_requires_reason_and_preserves_it(self):
        entry = VerificationEntry(
            command="apk build",
            cwd="/repo/apps/android",
            status=SKIPPED,
            skip_reason="Android SDK not installed in CI",
        )

        assert entry.status == SKIPPED
        assert entry.skip_reason == "Android SDK not installed in CI"
        assert entry.exit_code is None

    def test_skipped_without_reason_raises(self):
        with pytest.raises(ValueError, match="skip_reason"):
            VerificationEntry(
                command="apk build",
                cwd="/repo/apps/android",
                status=SKIPPED,
            )

    def test_skipped_with_empty_string_reason_raises(self):
        with pytest.raises(ValueError, match="skip_reason"):
            VerificationEntry(
                command="apk build",
                cwd="/repo",
                status=SKIPPED,
                skip_reason="",
            )

    @pytest.mark.parametrize("bad_status", ["pass", "PASS", "ok", "error", "", "skip"])
    def test_invalid_status_raises(self, bad_status):
        with pytest.raises(ValueError, match="status must be one of"):
            VerificationEntry(
                command="x",
                cwd="/",
                status=bad_status,
            )

    def test_skip_reason_on_passed_entry_raises(self):
        with pytest.raises(ValueError, match="skip_reason"):
            VerificationEntry(
                command="x",
                cwd="/",
                status=PASSED,
                skip_reason="this should not be allowed",
            )

    def test_skip_reason_on_failed_entry_raises(self):
        with pytest.raises(ValueError, match="skip_reason"):
            VerificationEntry(
                command="x",
                cwd="/",
                status=FAILED,
                skip_reason="this should not be allowed",
            )

    def test_empty_timestamp_is_auto_filled_with_utc_iso(self):
        entry = VerificationEntry(command="x", cwd="/", status=PASSED)

        assert entry.timestamp != ""
        # ISO-8601 UTC datetimes end with +00:00 when produced via
        # datetime.now(timezone.utc).isoformat().
        assert entry.timestamp.endswith("+00:00")
        # 'T' separator is part of ISO-8601 datetime format.
        assert "T" in entry.timestamp

    def test_explicit_timestamp_is_preserved(self):
        entry = VerificationEntry(
            command="x",
            cwd="/",
            status=PASSED,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert entry.timestamp == "2026-01-01T00:00:00+00:00"

    def test_artifacts_default_is_independent_list(self):
        a = VerificationEntry(command="x", cwd="/", status=PASSED)
        b = VerificationEntry(command="y", cwd="/", status=PASSED)
        a.artifacts.append("a.log")
        assert b.artifacts == []


class TestVerificationPacket:
    """Packet aggregation: counts, gate_result, add/record helpers."""

    def test_empty_packet_passes_gate(self):
        packet = VerificationPacket()

        assert packet.entries == []
        assert packet.counts() == {PASSED: 0, FAILED: 0, SKIPPED: 0}
        assert packet.gate_result() == PASSED

    def test_all_passed_packet_passes_gate(self):
        packet = VerificationPacket()
        packet.record("pytest", "/repo", PASSED, exit_code=0)
        packet.record("compileall", "/repo", PASSED, exit_code=0)

        assert packet.counts() == {PASSED: 2, FAILED: 0, SKIPPED: 0}
        assert packet.gate_result() == PASSED

    def test_mixed_pass_and_skip_passes_gate(self):
        packet = VerificationPacket()
        packet.record("pytest", "/repo", PASSED, exit_code=0)
        packet.record(
            "apk build",
            "/repo/apps/android",
            SKIPPED,
            skip_reason="Android SDK not installed",
        )

        assert packet.counts() == {PASSED: 1, FAILED: 0, SKIPPED: 1}
        assert packet.gate_result() == PASSED

    def test_any_failure_fails_gate(self):
        packet = VerificationPacket()
        packet.record("pytest", "/repo", PASSED, exit_code=0)
        packet.record("ruff check .", "/repo", FAILED, exit_code=1)
        packet.record(
            "apk build",
            "/repo/apps/android",
            SKIPPED,
            skip_reason="no Android SDK",
        )

        assert packet.counts() == {PASSED: 1, FAILED: 1, SKIPPED: 1}
        assert packet.gate_result() == FAILED

    def test_record_returns_appended_entry(self):
        packet = VerificationPacket()
        returned = packet.record("pytest", "/repo", PASSED, exit_code=0)

        assert isinstance(returned, VerificationEntry)
        assert len(packet.entries) == 1
        assert packet.entries[0] is returned

    def test_add_appends_pre_built_entry(self):
        packet = VerificationPacket()
        entry = VerificationEntry(command="x", cwd="/", status=PASSED)
        returned = packet.add(entry)

        assert returned is entry
        assert packet.entries == [entry]

    def test_record_artifacts_iterable_is_materialized_to_list(self):
        packet = VerificationPacket()
        entry = packet.record(
            "build",
            "/repo",
            PASSED,
            exit_code=0,
            artifacts=iter(["a.txt", "b.txt"]),
        )

        assert entry.artifacts == ["a.txt", "b.txt"]

    def test_record_with_no_artifacts_defaults_to_empty_list(self):
        packet = VerificationPacket()
        entry = packet.record("x", "/", PASSED)

        assert entry.artifacts == []


class TestPacketJSONOutput:
    """to_dict / to_json shape matches what the JARVIS Test Gate consumes."""

    def test_to_dict_has_required_top_level_keys(self):
        packet = VerificationPacket()
        packet.record("pytest", "/repo", PASSED, exit_code=0)

        data = packet.to_dict()
        assert set(data.keys()) == {"entries", "counts", "gate_result"}
        assert set(data["counts"].keys()) == {PASSED, FAILED, SKIPPED}

    def test_to_json_round_trips(self):
        packet = VerificationPacket()
        packet.record("pytest", "/repo", PASSED, exit_code=0, duration_seconds=2.5)
        packet.record(
            "apk build",
            "/repo/apps/android",
            SKIPPED,
            skip_reason="no SDK",
        )

        parsed = json.loads(packet.to_json())
        assert parsed["gate_result"] == PASSED
        assert parsed["counts"] == {PASSED: 1, FAILED: 0, SKIPPED: 1}
        assert len(parsed["entries"]) == 2
        # Per-entry fields survive the JSON round-trip.
        first = parsed["entries"][0]
        assert first["command"] == "pytest"
        assert first["duration_seconds"] == 2.5
        assert first["skip_reason"] is None
        second = parsed["entries"][1]
        assert second["status"] == SKIPPED
        assert second["skip_reason"] == "no SDK"

    def test_to_json_is_indented_by_default(self):
        packet = VerificationPacket()
        packet.record("x", "/", PASSED)

        out = packet.to_json()
        assert "\n" in out  # indent=2 produces multi-line output


class TestSummarizeText:
    """summarize_text helper: head/tail truncation for log capture."""

    def test_empty_returns_empty(self):
        assert summarize_text("") == ""

    def test_short_text_returned_unchanged(self):
        text = "all 3 tests passed"
        assert summarize_text(text) == text

    def test_long_text_truncated_with_marker(self):
        text = "x" * 5000
        out = summarize_text(text, max_chars=200)

        assert len(out) < len(text)
        assert "…[truncated]…" in out
        assert out.startswith("x")
        assert out.endswith("x")

    def test_exact_max_chars_not_truncated(self):
        text = "y" * 100
        assert summarize_text(text, max_chars=100) == text

    def test_custom_marker_used(self):
        text = "z" * 1000
        out = summarize_text(text, max_chars=100, marker="<snip>")
        assert "<snip>" in out
        assert "…[truncated]…" not in out


class TestModuleDoesNotExecuteCommands:
    """Acceptance guardrail: the module captures evidence, it does not run anything."""

    def test_subprocess_not_imported_at_module_level(self):
        # If the module ever grows a subprocess import, this test will flag it
        # so we can add the right safeguards (or revisit the acceptance criterion).
        assert "subprocess" not in verification.__dict__
        assert "Popen" not in verification.__dict__
        assert "run" not in verification.__dict__

    def test_no_os_system_or_exec(self):
        assert "system" not in verification.__dict__
        assert "execv" not in verification.__dict__
