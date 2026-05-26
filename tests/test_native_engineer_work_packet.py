"""Tests for hermes_cli.native_engineer.work_packet."""
from __future__ import annotations

import json

from hermes_cli.native_engineer.work_packet import WorkPacket


def _sample() -> WorkPacket:
    return WorkPacket(
        mission="add native engineer",
        branch="aci/test",
        allowed_files=("hermes_cli/native_engineer/**", "tests/test_native_engineer_*.py"),
        forbidden_files=("apps/android/**", "hermes_cli/model_router.py", ".github/**"),
        acceptance_criteria=("stdlib only", "tests cover repo map"),
        verification_commands=("pytest tests/test_native_engineer_*.py -q",),
        rollback_plan="git rm -r hermes_cli/native_engineer",
        metadata=(("test_skip_reason", ""), ("tag", "infrastructure")),
    )


def test_to_dict_from_dict_round_trip():
    packet = _sample()
    raw = json.dumps(packet.to_dict())
    restored = WorkPacket.from_dict(json.loads(raw))
    assert restored == packet


def test_is_path_allowed_accepts_in_scope():
    packet = _sample()
    assert packet.is_path_allowed("hermes_cli/native_engineer/repo_map.py")
    assert packet.is_path_allowed("tests/test_native_engineer_repo_map.py")


def test_is_path_allowed_rejects_out_of_scope():
    packet = _sample()
    assert not packet.is_path_allowed("hermes_cli/main.py")
    assert not packet.is_path_allowed("README.md")


def test_forbidden_wins_over_allowed():
    packet = WorkPacket(
        mission="m",
        branch="b",
        allowed_files=("foo/**",),
        forbidden_files=("foo/secret.py",),
    )
    assert packet.is_path_allowed("foo/bar.py")
    assert not packet.is_path_allowed("foo/secret.py")


def test_forbidden_recursive_glob():
    packet = WorkPacket(
        mission="m",
        branch="b",
        allowed_files=("**",),
        forbidden_files=("apps/android/**",),
    )
    assert not packet.is_path_allowed("apps/android/App.kt")
    assert not packet.is_path_allowed("apps/android/sub/dir/File.kt")
    assert packet.is_path_allowed("hermes_cli/x.py")


def test_metadata_dict_helper():
    packet = _sample()
    assert packet.metadata_dict()["tag"] == "infrastructure"


def test_packet_is_hashable():
    # frozen dataclass with all-tuple fields should hash.
    {_sample()}
