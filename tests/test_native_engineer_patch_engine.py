"""Tests for hermes_cli.native_engineer.patch_engine."""
from __future__ import annotations

from hermes_cli.native_engineer.patch_engine import (
    Patch,
    dry_run_diff,
    rollback_notes,
    validate,
)
from hermes_cli.native_engineer.work_packet import WorkPacket


def _packet() -> WorkPacket:
    return WorkPacket(
        mission="m",
        branch="b",
        allowed_files=("hermes_cli/native_engineer/**", "tests/test_native_engineer_*.py"),
        forbidden_files=("apps/android/**",),
    )


def test_validate_accepts_in_scope_create():
    patch = Patch(
        target_path="hermes_cli/native_engineer/new_mod.py",
        operation="create",
        after="x = 1\n",
        rationale="add helper",
    )
    result = validate(patch, _packet())
    assert result.allowed
    assert result.reason == "ok"
    assert result.dry_run_diff != ""


def test_validate_rejects_out_of_allowlist():
    patch = Patch(
        target_path="hermes_cli/main.py",
        operation="modify",
        before="x\n",
        after="y\n",
        rationale="r",
    )
    result = validate(patch, _packet())
    assert not result.allowed
    assert "not in allowed_files" in result.reason
    assert result.dry_run_diff == ""


def test_validate_rejects_forbidden_path_even_if_pattern_overlaps():
    pkt = WorkPacket(
        mission="m",
        branch="b",
        allowed_files=("**",),
        forbidden_files=("apps/android/**",),
    )
    patch = Patch(
        target_path="apps/android/App.kt",
        operation="create",
        after="// kt\n",
        rationale="r",
    )
    result = validate(patch, pkt)
    assert not result.allowed


def test_validate_rejects_modify_without_before():
    patch = Patch(
        target_path="hermes_cli/native_engineer/repo_map.py",
        operation="modify",
        before=None,
        after="x\n",
        rationale="r",
    )
    result = validate(patch, _packet())
    assert not result.allowed
    assert "before" in result.reason


def test_validate_rejects_create_without_after():
    patch = Patch(
        target_path="hermes_cli/native_engineer/x.py",
        operation="create",
        after=None,
        rationale="r",
    )
    result = validate(patch, _packet())
    assert not result.allowed
    assert "after" in result.reason


def test_validate_rejects_unknown_operation():
    patch = Patch(
        target_path="hermes_cli/native_engineer/x.py",
        operation="frobnicate",
        rationale="r",
    )
    result = validate(patch, _packet())
    assert not result.allowed
    assert "unknown operation" in result.reason


def test_dry_run_diff_non_empty_for_modify():
    patch = Patch(
        target_path="x.py",
        operation="modify",
        before="a = 1\n",
        after="a = 2\n",
        rationale="r",
    )
    diff = dry_run_diff(patch)
    assert "a = 1" in diff
    assert "a = 2" in diff


def test_dry_run_diff_create_uses_dev_null():
    patch = Patch(
        target_path="x.py",
        operation="create",
        after="hello\n",
        rationale="r",
    )
    diff = dry_run_diff(patch)
    assert "/dev/null" in diff


def test_rollback_notes_lists_inverse_ops():
    patches = [
        Patch(target_path="a.py", operation="create", after="x\n", rationale=""),
        Patch(target_path="b.py", operation="modify", before="x\n", after="y\n", rationale=""),
        Patch(target_path="c.py", operation="delete", before="x\n", rationale=""),
    ]
    notes = rollback_notes(patches)
    assert "delete a.py" in notes
    assert "revert b.py" in notes
    assert "restore c.py" in notes
