"""Tests for hermes_cli.jarvis_prime.build_packets."""

from __future__ import annotations

import pytest

from hermes_cli.jarvis_prime.build_packets import (
    BuildPacket,
    BuildPacketError,
    Worker,
)


def _valid_kwargs(**overrides):
    """Minimal kwargs that produce a packet which passes validate()."""
    kwargs = dict(
        mission="Add the build packet schema.",
        repo_root="/home/user/hermes-agent",
        branch="aci/wave-05-build-packet-schema",
        worker=Worker.CLAUDE_CODE_BUILDER,
        allowed_files=["hermes_cli/jarvis_prime/build_packets.py"],
        acceptance_criteria=["Schema validates required fields."],
    )
    kwargs.update(overrides)
    return kwargs


class TestWorkerEnum:
    def test_enum_values_match_operating_doc(self):
        assert Worker.CLAUDE_CODE_BUILDER.value == "claude_code_builder"
        assert Worker.CODEX_REVIEWER.value == "codex_reviewer"
        assert Worker.CODEX_BOUNDED_FIX.value == "codex_bounded_fix"
        assert Worker.LOCAL_TEST_RUNNER.value == "local_test_runner"

    def test_worker_constructable_from_string(self):
        assert Worker("claude_code_builder") is Worker.CLAUDE_CODE_BUILDER
        assert Worker("local_test_runner") is Worker.LOCAL_TEST_RUNNER

    def test_worker_rejects_unknown_value(self):
        with pytest.raises(ValueError):
            Worker("totally_made_up_worker")


class TestBuildPacketValidation:
    def test_minimal_valid_packet_validates(self):
        packet = BuildPacket(**_valid_kwargs())
        packet.validate()

    def test_missing_mission_raises(self):
        packet = BuildPacket(**_valid_kwargs(mission=""))
        with pytest.raises(BuildPacketError, match="mission"):
            packet.validate()

    def test_blank_mission_raises(self):
        packet = BuildPacket(**_valid_kwargs(mission="   \t  "))
        with pytest.raises(BuildPacketError, match="mission"):
            packet.validate()

    def test_missing_repo_root_raises(self):
        packet = BuildPacket(**_valid_kwargs(repo_root=""))
        with pytest.raises(BuildPacketError, match="repo_root"):
            packet.validate()

    def test_missing_branch_raises(self):
        packet = BuildPacket(**_valid_kwargs(branch=""))
        with pytest.raises(BuildPacketError, match="branch"):
            packet.validate()

    def test_empty_allowed_files_raises(self):
        packet = BuildPacket(**_valid_kwargs(allowed_files=[]))
        with pytest.raises(BuildPacketError, match="allowed_files"):
            packet.validate()

    def test_allowed_files_with_only_blanks_raises(self):
        packet = BuildPacket(**_valid_kwargs(allowed_files=["", "   "]))
        with pytest.raises(BuildPacketError, match="allowed_files"):
            packet.validate()

    def test_empty_acceptance_criteria_raises(self):
        packet = BuildPacket(**_valid_kwargs(acceptance_criteria=[]))
        with pytest.raises(BuildPacketError, match="acceptance_criteria"):
            packet.validate()

    def test_worker_not_enum_member_raises(self):
        packet = BuildPacket(**_valid_kwargs(worker="claude_code_builder"))
        with pytest.raises(BuildPacketError, match="worker"):
            packet.validate()

    def test_overlap_literal_path_raises(self):
        packet = BuildPacket(
            **_valid_kwargs(
                allowed_files=["gateway/main.py"],
                forbidden_files=["gateway/main.py"],
            )
        )
        with pytest.raises(BuildPacketError, match="overlap"):
            packet.validate()

    def test_overlap_glob_forbidden_shadows_allowed_raises(self):
        packet = BuildPacket(
            **_valid_kwargs(
                allowed_files=["gateway/main.py"],
                forbidden_files=["gateway/**"],
            )
        )
        with pytest.raises(BuildPacketError, match="overlap"):
            packet.validate()

    def test_overlap_glob_allowed_shadows_forbidden_raises(self):
        packet = BuildPacket(
            **_valid_kwargs(
                allowed_files=["gateway/**"],
                forbidden_files=["gateway/main.py"],
            )
        )
        with pytest.raises(BuildPacketError, match="overlap"):
            packet.validate()

    def test_no_overlap_passes(self):
        packet = BuildPacket(
            **_valid_kwargs(
                allowed_files=["hermes_cli/jarvis_prime/build_packets.py"],
                forbidden_files=["gateway/**", "apps/android/**"],
            )
        )
        packet.validate()

    def test_multiple_errors_combined_in_message(self):
        packet = BuildPacket(**_valid_kwargs(mission="", branch=""))
        with pytest.raises(BuildPacketError) as excinfo:
            packet.validate()
        assert "mission" in str(excinfo.value)
        assert "branch" in str(excinfo.value)


class TestSerialization:
    def test_to_dict_then_from_dict_roundtrips(self):
        original = BuildPacket(
            **_valid_kwargs(
                forbidden_files=["gateway/**"],
                non_goals=["Do not touch the gateway."],
                verification_commands=["pytest tests/test_jarvis_prime_build_packets.py"],
                rollback_plan="Delete the subpackage.",
                owner_gated_actions=["push to remote"],
            )
        )
        original.validate()
        restored = BuildPacket.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_serializes_worker_as_string_value(self):
        packet = BuildPacket(**_valid_kwargs(worker=Worker.CODEX_REVIEWER))
        data = packet.to_dict()
        assert data["worker"] == "codex_reviewer"
        assert isinstance(data["worker"], str)

    def test_from_dict_accepts_string_worker(self):
        kwargs = _valid_kwargs()
        kwargs["worker"] = "codex_bounded_fix"
        packet = BuildPacket.from_dict(kwargs)
        assert packet.worker is Worker.CODEX_BOUNDED_FIX

    def test_from_dict_ignores_unknown_keys(self):
        data = _valid_kwargs()
        data["worker"] = data["worker"].value
        data["completely_new_field"] = "ignored"
        data["another_future_thing"] = 42
        packet = BuildPacket.from_dict(data)
        packet.validate()

    def test_from_dict_rejects_wrong_type_for_list_field(self):
        data = _valid_kwargs()
        data["worker"] = data["worker"].value
        data["allowed_files"] = "not-a-list"
        with pytest.raises(BuildPacketError, match="allowed_files"):
            BuildPacket.from_dict(data)

    def test_from_dict_rejects_non_string_list_entry(self):
        data = _valid_kwargs()
        data["worker"] = data["worker"].value
        data["acceptance_criteria"] = ["valid", 42]
        with pytest.raises(BuildPacketError, match="acceptance_criteria"):
            BuildPacket.from_dict(data)

    def test_from_dict_rejects_unknown_worker_value(self):
        data = _valid_kwargs()
        data["worker"] = "supreme_overlord"
        with pytest.raises(BuildPacketError, match="worker"):
            BuildPacket.from_dict(data)

    def test_from_dict_rejects_non_mapping(self):
        with pytest.raises(BuildPacketError):
            BuildPacket.from_dict(["not", "a", "mapping"])

    def test_from_dict_does_not_call_validate(self):
        data = _valid_kwargs()
        data["worker"] = data["worker"].value
        data["allowed_files"] = []
        data["acceptance_criteria"] = []
        packet = BuildPacket.from_dict(data)
        assert packet.allowed_files == []
        with pytest.raises(BuildPacketError):
            packet.validate()


class TestMarkdownRendering:
    def test_markdown_contains_all_section_headers(self):
        packet = BuildPacket(**_valid_kwargs())
        md = packet.to_markdown()
        for header in (
            "# Build Packet",
            "## Mission",
            "## Worker",
            "## Repo",
            "## Allowed Files",
            "## Forbidden Files",
            "## Non-Goals",
            "## Acceptance Criteria",
            "## Verification Commands",
            "## Rollback Plan",
            "## Owner-Gated Actions",
        ):
            assert header in md, f"missing header: {header}"

    def test_markdown_section_order_is_stable(self):
        packet = BuildPacket(**_valid_kwargs())
        md = packet.to_markdown()
        positions = [
            md.index("## Mission"),
            md.index("## Worker"),
            md.index("## Repo"),
            md.index("## Allowed Files"),
            md.index("## Forbidden Files"),
            md.index("## Non-Goals"),
            md.index("## Acceptance Criteria"),
            md.index("## Verification Commands"),
            md.index("## Rollback Plan"),
            md.index("## Owner-Gated Actions"),
        ]
        assert positions == sorted(positions)

    def test_markdown_acceptance_criteria_rendered_as_checkboxes(self):
        packet = BuildPacket(
            **_valid_kwargs(acceptance_criteria=["First done.", "Second done."])
        )
        md = packet.to_markdown()
        assert "- [ ] First done." in md
        assert "- [ ] Second done." in md

    def test_markdown_verification_commands_rendered_in_code_block(self):
        packet = BuildPacket(
            **_valid_kwargs(
                verification_commands=[
                    "pytest tests/test_jarvis_prime_build_packets.py",
                    "python -m compileall hermes_cli/jarvis_prime/build_packets.py",
                ]
            )
        )
        md = packet.to_markdown()
        assert "```\npytest tests/test_jarvis_prime_build_packets.py" in md
        assert "python -m compileall hermes_cli/jarvis_prime/build_packets.py\n```" in md

    def test_markdown_empty_optional_sections_show_none_placeholder(self):
        packet = BuildPacket(**_valid_kwargs())
        md = packet.to_markdown()
        section = md.split("## Forbidden Files", 1)[1].split("## ", 1)[0]
        assert "(none)" in section
        rollback_section = md.split("## Rollback Plan", 1)[1].split("## ", 1)[0]
        assert "(none specified)" in rollback_section

    def test_markdown_includes_repo_root_and_branch(self):
        packet = BuildPacket(**_valid_kwargs())
        md = packet.to_markdown()
        assert "- Root: /home/user/hermes-agent" in md
        assert "- Branch: aci/wave-05-build-packet-schema" in md

    def test_markdown_includes_worker_value(self):
        packet = BuildPacket(**_valid_kwargs(worker=Worker.CODEX_REVIEWER))
        md = packet.to_markdown()
        assert "codex_reviewer" in md

    def test_to_markdown_raises_when_packet_invalid(self):
        packet = BuildPacket(**_valid_kwargs(mission=""))
        with pytest.raises(BuildPacketError):
            packet.to_markdown()

    def test_to_markdown_validate_false_skips_check(self):
        packet = BuildPacket(**_valid_kwargs(mission=""))
        md = packet.to_markdown(validate=False)
        assert "# Build Packet" in md
