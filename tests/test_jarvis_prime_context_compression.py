"""Unit tests for hermes_cli.jarvis_prime.context_compression."""
from __future__ import annotations

from typing import Any

import pytest

from hermes_cli.jarvis_prime import CompressedHandoff, compress_context


def _markdown_notes() -> str:
    return """\
Mission: Ship the Wave 03 compression helper.

## Decisions
- Use stdlib only
- Frozen dataclass for determinism
- Redact secrets before classification

## Files Touched
- hermes_cli/jarvis_prime/context_compression.py
- tests/test_jarvis_prime_context_compression.py

## Unresolved Blockers
- No call sites wired yet

## Owner Gates
- Yes, with authorization.

## Verification Evidence
- pytest tests/test_jarvis_prime_context_compression.py passed

## Next Action
Wire compress_context into the Slack handoff adapter.
"""


def test_string_input_extracts_sections():
    handoff = compress_context(_markdown_notes())
    assert handoff.mission.startswith("Ship the Wave 03")
    assert "Use stdlib only" in handoff.decisions
    assert "hermes_cli/jarvis_prime/context_compression.py" in handoff.files_touched
    assert "No call sites wired yet" in handoff.unresolved_blockers
    assert handoff.owner_gates == ("Yes, with authorization.",)
    assert handoff.verification_evidence[0].startswith("pytest")
    assert handoff.next_action.startswith("Wire compress_context")
    assert handoff.truncated is False


def test_list_input_classifies_items():
    items = [
        "Mission: Build a deterministic helper.",
        "Decided: keep it pure stdlib.",
        "Blocker: nothing yet.",
        {"files_touched": ["src/a.py", "src/b.py"]},
        "Next: write the tests.",
    ]
    handoff = compress_context(items)
    assert "Build a deterministic helper." in handoff.mission
    assert "keep it pure stdlib." in handoff.decisions
    assert "nothing yet." in handoff.unresolved_blockers
    assert "src/a.py" in handoff.files_touched
    assert "src/b.py" in handoff.files_touched
    assert handoff.next_action == "write the tests."


def test_dict_input_passthrough():
    data = {
        "mission": "Compress handoffs.",
        "decisions": ["use stdlib", "frozen dataclass"],
        "files": ["hermes_cli/jarvis_prime/context_compression.py"],
        "blockers": ["nothing"],
        "gates": ["Yes, with authorization."],
        "verification": ["pytest -v"],
        "next": "ship it",
    }
    handoff = compress_context(data)
    out = handoff.as_dict()
    assert out["mission"] == "Compress handoffs."
    assert out["decisions"] == ["use stdlib", "frozen dataclass"]
    assert out["files_touched"] == [
        "hermes_cli/jarvis_prime/context_compression.py"
    ]
    assert out["unresolved_blockers"] == ["nothing"]
    assert out["owner_gates"] == ["Yes, with authorization."]
    assert out["verification_evidence"] == ["pytest -v"]
    assert out["next_action"] == "ship it"
    assert out["truncated"] is False


def test_long_input_truncated_under_char_limit():
    decisions = "\n".join(f"- decided thing number {i}" for i in range(500))
    notes = f"Mission: long mission.\n## Decisions\n{decisions}\n"
    handoff = compress_context(notes, char_limit=600)
    rendered = handoff.render()
    assert len(rendered) <= 600
    assert handoff.truncated is True
    assert handoff.mission == "long mission."


def test_redacts_openai_and_anthropic_keys():
    text = "Decided: use api token sk-abc123def456ghi789jkl for the call."
    handoff = compress_context(text)
    joined = " ".join(handoff.decisions)
    assert "sk-abc123def456ghi789jkl" not in joined
    assert "[REDACTED]" in joined


def test_redacts_github_tokens():
    text = (
        "Mission: rotate.\n"
        "Decided: rotated ghp_abcdefghijklmnopqrstuvwxyz012345 and "
        "github_pat_11ABCDEFG0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa today."
    )
    handoff = compress_context(text)
    joined = handoff.render()
    assert "ghp_abcdefghijklmnopqrstuvwxyz012345" not in joined
    assert "github_pat_11ABCDEFG" not in joined
    assert joined.count("[REDACTED]") >= 2


def test_redacts_aws_access_keys():
    text = "Decided: rotate AKIAIOSFODNN7EXAMPLE next sprint."
    handoff = compress_context(text)
    joined = " ".join(handoff.decisions)
    assert "AKIAIOSFODNN7EXAMPLE" not in joined
    assert "[REDACTED]" in joined


def test_redacts_slack_tokens():
    text = (
        "Decided: keep xoxb-1234567890-abcdefg and "
        "xoxp-9876543210-zyxwvut out of logs."
    )
    handoff = compress_context(text)
    joined = " ".join(handoff.decisions)
    assert "xoxb-1234567890" not in joined
    assert "xoxp-9876543210" not in joined


def test_redacts_bearer_auth_header():
    text = "Decided: header Authorization: Bearer abcdef1234567890ZZZ used."
    handoff = compress_context(text)
    joined = " ".join(handoff.decisions)
    assert "abcdef1234567890ZZZ" not in joined
    assert "[REDACTED]" in joined


def test_redacts_url_with_credentials():
    text = "Decided: hit https://alice:s3cret@example.com/api for the probe."
    handoff = compress_context(text)
    joined = " ".join(handoff.decisions)
    assert "alice:s3cret" not in joined
    assert "https://[REDACTED]@example.com" in joined


def test_redacts_generic_key_value_pairs():
    text = "Decided: set API_KEY=supersecretvalue123 in env."
    handoff = compress_context(text)
    joined = " ".join(handoff.decisions)
    assert "supersecretvalue123" not in joined
    assert "API_KEY" in joined
    assert "[REDACTED]" in joined


def test_redaction_disabled_preserves_input():
    text = "Decided: use api token sk-abc123def456ghi789jkl for the call."
    handoff = compress_context(text, redact_secrets=False)
    joined = " ".join(handoff.decisions)
    assert "sk-abc123def456ghi789jkl" in joined


def test_deterministic_same_input_same_output():
    notes = _markdown_notes()
    a = compress_context(notes)
    b = compress_context(notes)
    assert a == b
    assert a.render() == b.render()
    assert a.as_dict() == b.as_dict()


def test_dedupes_repeated_items():
    text = (
        "Decisions:\n"
        "- use stdlib\n"
        "- use stdlib\n"
        "- use stdlib\n"
        "- frozen dataclass\n"
    )
    handoff = compress_context(text)
    assert handoff.decisions == ("use stdlib", "frozen dataclass")


def test_empty_input_returns_empty_handoff():
    for empty in ("", [], {}):
        handoff = compress_context(empty)
        assert handoff.mission == ""
        assert handoff.decisions == ()
        assert handoff.files_touched == ()
        assert handoff.unresolved_blockers == ()
        assert handoff.owner_gates == ()
        assert handoff.verification_evidence == ()
        assert handoff.next_action == ""
        assert handoff.truncated is False
        rendered = handoff.render()
        assert "# JARVIS Handoff" in rendered
        assert "- (none)" in rendered


def test_invalid_input_type_raises_type_error():
    bad_int: Any = 42
    bad_float: Any = 3.14
    with pytest.raises(TypeError):
        compress_context(bad_int)
    with pytest.raises(TypeError):
        compress_context(bad_float)


def test_export_in_init():
    from hermes_cli.jarvis_prime import (
        CompressedHandoff as Exported,
        compress_context as exported_fn,
    )

    assert Exported is CompressedHandoff
    assert exported_fn is compress_context


def test_no_secrets_after_truncation():
    bulk = "\n".join(f"- routine decision {i}" for i in range(400))
    notes = (
        "Mission: rotate creds.\n"
        "## Decisions\n"
        f"{bulk}\n"
        "- leaked sk-abc123def456ghi789jkl somewhere in here\n"
    )
    handoff = compress_context(notes, char_limit=500)
    rendered = handoff.render()
    assert len(rendered) <= 500
    assert handoff.truncated is True
    assert "sk-abc123def456ghi789jkl" not in rendered


def test_char_limit_zero_returns_truncated_minimum():
    handoff = compress_context("Mission: anything", char_limit=0)
    assert handoff.truncated is True
    assert isinstance(handoff.render(), str)


def test_files_touched_dedups_and_normalizes():
    text = (
        "Files:\n"
        "- ./hermes_cli/jarvis_prime/context_compression.py\n"
        "- hermes_cli/jarvis_prime/context_compression.py\n"
        "- tests/test_jarvis_prime_context_compression.py\n"
    )
    handoff = compress_context(text)
    assert handoff.files_touched == (
        "hermes_cli/jarvis_prime/context_compression.py",
        "tests/test_jarvis_prime_context_compression.py",
    )


def test_compressed_handoff_is_hashable():
    h = compress_context("Mission: be hashable.")
    assert hash(h) == hash(compress_context("Mission: be hashable."))


def test_compressed_handoff_render_ends_with_newline():
    h = compress_context("Mission: hi.")
    assert h.render().endswith("\n")


def test_negative_char_limit_raises_value_error():
    with pytest.raises(ValueError):
        compress_context("Mission: x", char_limit=-1)
