"""Tests for hermes_cli.native_engineer.sop_miner."""
from __future__ import annotations

from hermes_cli.native_engineer.patch_engine import Patch
from hermes_cli.native_engineer.sop_miner import mine, to_markdown
from hermes_cli.native_engineer.test_runner import TestCommand, TestResult
from hermes_cli.native_engineer.work_packet import WorkPacket


def _packet() -> WorkPacket:
    return WorkPacket(
        mission="Add Hermes Native Engineer core for Jarvis Prime",
        branch="aci/jarvis-prime-14-hermes-native-engineer-core",
        allowed_files=("hermes_cli/native_engineer/**",),
        verification_commands=(
            "pytest tests/test_native_engineer_*.py -q",
            "python -m compileall hermes_cli/native_engineer",
        ),
        metadata=(("tag", "infrastructure,bench"),),
    )


def _patches() -> list[Patch]:
    return [
        Patch(target_path="hermes_cli/native_engineer/repo_map.py", operation="create", after="x\n", rationale="add repo map"),
        Patch(target_path="hermes_cli/native_engineer/work_packet.py", operation="create", after="x\n", rationale="add work packet"),
        Patch(target_path="hermes_cli/native_engineer/repo_map.py", operation="create", after="x\n", rationale="dup"),  # dup
        Patch(target_path="docs/aci/native-engineer/HERMES_NATIVE_ENGINEER.md", operation="create", after="x\n", rationale="docs"),
        Patch(target_path="tests/test_native_engineer_repo_map.py", operation="create", after="x\n", rationale="test"),
    ]


def _results() -> list[TestResult]:
    return [
        TestResult(
            command=TestCommand(argv=("pytest",)),
            returncode=0,
            stdout="ok",
            stderr="",
            duration_seconds=0.1,
            parsed={"passed": 5, "failed": 0},
        )
    ]


def test_mine_produces_sorted_unique_artifacts():
    record = mine(_packet(), _patches(), _results())
    assert record.artifacts == tuple(sorted(set(record.artifacts)))
    assert record.artifacts.count("hermes_cli/native_engineer/repo_map.py") == 1


def test_mine_title_truncates_at_80_chars():
    long = "x" * 200
    pkt = WorkPacket(mission=long, branch="b")
    record = mine(pkt, [], [])
    assert len(record.title) == 80


def test_mine_tags_include_metadata_and_heuristic():
    record = mine(_packet(), _patches(), _results())
    assert "infrastructure" in record.tags
    assert "bench" in record.tags
    assert "docs" in record.tags
    assert "tests" in record.tags
    assert "hermes_cli" in record.tags


def test_mine_steps_one_per_patch_in_order():
    record = mine(_packet(), _patches(), _results())
    assert len(record.steps) == len(_patches())
    assert record.steps[0].startswith("[create]")


def test_to_markdown_contains_title_and_verification():
    record = mine(_packet(), _patches(), _results())
    md = to_markdown(record)
    assert "Add Hermes Native Engineer" in md
    assert "pytest tests/test_native_engineer_*.py -q" in md
    assert "## Artifacts" in md
