"""Tests for hermes_cli.jarvis_prime.review_packets.

The module is pure data + markdown — no network, no LLM, no filesystem.
These tests exercise the public surface in isolation: dataclass shape,
decision validation, default checklists, and the deterministic markdown
output across every interesting branch (approve / request_changes /
comment, missing test evidence, security finding present).
"""

from __future__ import annotations

import pytest

from hermes_cli.jarvis_prime.review_packets import (
    VALID_DECISIONS,
    ChecklistItem,
    FixRecommendation,
    ReviewPacket,
    TestEvidence,
    default_regression_checklist,
    default_security_checklist,
    normalize_decision,
    render_review_packet,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def baseline_packet() -> ReviewPacket:
    """A clean, all-passing packet that tests can mutate via dataclasses.replace."""
    return ReviewPacket(
        subject="PR #42",
        mission="Add a `--dry-run` flag to the deploy command.",
        files_changed=("deploy.py", "tests/test_deploy.py"),
        acceptance_criteria=(
            "Flag is documented in --help.",
            "Dry-run path does not write to disk.",
        ),
        diff_summary="2 files changed, +48 / -3.",
        test_evidence=(
            TestEvidence(
                command="pytest tests/test_deploy.py",
                passed=True,
                summary="6 passed in 0.8s",
            ),
        ),
        security_checklist=(
            ChecklistItem("Secrets handling", status="pass"),
            ChecklistItem("Input validation", status="pass"),
        ),
        regression_checklist=(
            ChecklistItem("Golden path", status="pass"),
            ChecklistItem("Rollback", status="pass"),
        ),
        decision="approve",
    )


# ---------------------------------------------------------------------------
# normalize_decision
# ---------------------------------------------------------------------------


class TestDecisionValidation:
    def test_lowercase_passes(self):
        for d in VALID_DECISIONS:
            assert normalize_decision(d) == d

    def test_uppercase_is_normalized(self):
        assert normalize_decision("APPROVE") == "approve"
        assert normalize_decision("Request_Changes") == "request_changes"
        assert normalize_decision("Comment") == "comment"

    def test_space_in_request_changes_is_tolerated(self):
        assert normalize_decision("request changes") == "request_changes"
        assert normalize_decision("REQUEST CHANGES") == "request_changes"

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError) as exc:
            normalize_decision("merge")
        assert "merge" in str(exc.value)
        # Error message must list the valid options so the caller can fix it.
        for d in VALID_DECISIONS:
            assert d in str(exc.value)

    def test_non_string_raises(self):
        with pytest.raises(ValueError):
            normalize_decision(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# render_review_packet — decision branches
# ---------------------------------------------------------------------------


class TestRenderApprove:
    def test_header_and_decision(self, baseline_packet):
        md = render_review_packet(baseline_packet)
        assert md.startswith("# Review Packet — PR #42\n")
        assert "**Decision:** APPROVE" in md

    def test_no_security_callout_when_all_pass(self, baseline_packet):
        md = render_review_packet(baseline_packet)
        assert "Security finding present" not in md

    def test_fix_recommendations_section_absent_when_empty(self, baseline_packet):
        md = render_review_packet(baseline_packet)
        assert "## Fix Recommendations" not in md

    def test_trailing_newline(self, baseline_packet):
        md = render_review_packet(baseline_packet)
        assert md.endswith("\n")
        assert not md.endswith("\n\n")

    def test_determinism(self, baseline_packet):
        # Same packet → same bytes, twice.
        assert render_review_packet(baseline_packet) == render_review_packet(
            baseline_packet
        )


class TestRenderRequestChanges:
    def test_header_displays_request_changes(self, baseline_packet):
        from dataclasses import replace

        packet = replace(
            baseline_packet,
            decision="request_changes",
            fix_recommendations=(
                FixRecommendation(
                    file="deploy.py",
                    change="Guard the dry-run branch with an explicit `if`.",
                    rationale="Avoids the truthiness pitfall on numeric flags.",
                ),
            ),
        )
        md = render_review_packet(packet)
        assert "**Decision:** REQUEST CHANGES" in md

    def test_fix_recommendations_section_rendered(self, baseline_packet):
        from dataclasses import replace

        rec = FixRecommendation(
            file="deploy.py",
            change="Guard the dry-run branch with an explicit `if`.",
            rationale="Avoids the truthiness pitfall on numeric flags.",
        )
        packet = replace(
            baseline_packet,
            decision="request_changes",
            fix_recommendations=(rec,),
        )
        md = render_review_packet(packet)
        assert "## Fix Recommendations" in md
        assert "`deploy.py`" in md
        assert rec.change in md
        assert "rationale:" in md
        assert rec.rationale in md

    def test_cross_cutting_fix_has_no_file_path(self, baseline_packet):
        from dataclasses import replace

        rec = FixRecommendation(
            file="",
            change="Document the dry-run flag in the release notes.",
        )
        packet = replace(
            baseline_packet,
            decision="request_changes",
            fix_recommendations=(rec,),
        )
        md = render_review_packet(packet)
        assert "_(cross-cutting)_" in md
        assert rec.change in md


class TestRenderComment:
    def test_header_displays_comment(self, baseline_packet):
        from dataclasses import replace

        packet = replace(baseline_packet, decision="comment")
        md = render_review_packet(packet)
        assert "**Decision:** COMMENT" in md

    def test_no_fix_recommendations_section_when_empty(self, baseline_packet):
        from dataclasses import replace

        packet = replace(baseline_packet, decision="comment")
        md = render_review_packet(packet)
        assert "## Fix Recommendations" not in md

    def test_reviewer_notes_rendered_when_present(self, baseline_packet):
        from dataclasses import replace

        packet = replace(
            baseline_packet,
            decision="comment",
            reviewer_notes="Nice work — wanted to leave a note on the test naming.",
        )
        md = render_review_packet(packet)
        assert "## Reviewer Notes" in md
        assert packet.reviewer_notes in md


# ---------------------------------------------------------------------------
# Missing test evidence
# ---------------------------------------------------------------------------


class TestMissingTestEvidence:
    def test_warning_blockquote_when_no_evidence(self, baseline_packet):
        from dataclasses import replace

        packet = replace(baseline_packet, test_evidence=())
        md = render_review_packet(packet)
        assert "## Test Evidence" in md
        assert "> ⚠️ No test evidence supplied." in md
        assert "`reviewer_notes`" in md

    def test_table_rendered_when_evidence_present(self, baseline_packet):
        md = render_review_packet(baseline_packet)
        assert "| Command | Result | Notes |" in md
        assert "| `pytest tests/test_deploy.py` | ✓ pass | 6 passed in 0.8s |" in md
        assert "> ⚠️ No test evidence supplied." not in md

    def test_failed_test_row_marked(self, baseline_packet):
        from dataclasses import replace

        packet = replace(
            baseline_packet,
            test_evidence=(
                TestEvidence(
                    command="pytest tests/test_deploy.py",
                    passed=False,
                    summary="1 failed, 5 passed",
                ),
            ),
        )
        md = render_review_packet(packet)
        assert "✗ fail" in md


# ---------------------------------------------------------------------------
# Security finding
# ---------------------------------------------------------------------------


class TestSecurityFinding:
    def test_callout_added_when_any_item_fails(self, baseline_packet):
        from dataclasses import replace

        packet = replace(
            baseline_packet,
            security_checklist=(
                ChecklistItem("Secrets handling", status="pass"),
                ChecklistItem(
                    "Input validation",
                    status="fail",
                    note="missing length check in deploy.py",
                ),
            ),
            decision="request_changes",
        )
        md = render_review_packet(packet)
        assert "> ⚠️ Security finding present." in md
        # And the offending row is marked **fail** with its note.
        assert "⚠️ Input validation — **fail**" in md
        assert "missing length check in deploy.py" in md

    def test_pass_items_render_with_pass_marker(self, baseline_packet):
        md = render_review_packet(baseline_packet)
        assert "[x] Secrets handling — pass" in md


# ---------------------------------------------------------------------------
# Default checklists
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_security_defaults_non_empty_all_todo(self):
        items = default_security_checklist()
        assert len(items) >= 3
        for it in items:
            assert isinstance(it, ChecklistItem)
            assert it.status == "todo"
            assert it.label

    def test_regression_defaults_non_empty_all_todo(self):
        items = default_regression_checklist()
        assert len(items) >= 3
        for it in items:
            assert isinstance(it, ChecklistItem)
            assert it.status == "todo"
            assert it.label

    def test_defaults_render_cleanly_in_packet(self):
        packet = ReviewPacket(
            subject="branch foo",
            mission="Trivial change.",
            files_changed=("foo.py",),
            acceptance_criteria=("Compiles.",),
            diff_summary="1 file changed.",
            test_evidence=(
                TestEvidence(command="pytest tests/test_foo.py", passed=True),
            ),
            security_checklist=default_security_checklist(),
            regression_checklist=default_regression_checklist(),
            decision="comment",
        )
        md = render_review_packet(packet)
        # Default items render as todo (unchecked, no warning callout).
        assert "Security finding present" not in md
        assert "[ ] Secrets handling" in md
        assert "[ ] Golden path" in md


# ---------------------------------------------------------------------------
# Pipe-escaping in evidence table
# ---------------------------------------------------------------------------


class TestEvidenceTableEscaping:
    def test_pipe_in_command_is_escaped(self, baseline_packet):
        from dataclasses import replace

        packet = replace(
            baseline_packet,
            test_evidence=(
                TestEvidence(
                    command="pytest -k 'foo|bar'",
                    passed=True,
                    summary="2 passed | 0 failed",
                ),
            ),
        )
        md = render_review_packet(packet)
        # Pipes inside cells are escaped so the markdown table stays valid.
        assert "foo\\|bar" in md
        assert "2 passed \\| 0 failed" in md
