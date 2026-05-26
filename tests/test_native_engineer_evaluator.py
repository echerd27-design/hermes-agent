"""Tests for hermes_cli.native_engineer.evaluator."""
from __future__ import annotations

from hermes_cli.native_engineer.evaluator import Evidence, evaluate
from hermes_cli.native_engineer.patch_engine import Patch, validate
from hermes_cli.native_engineer.test_runner import TestCommand, TestResult
from hermes_cli.native_engineer.work_packet import WorkPacket


def _packet(**overrides) -> WorkPacket:
    defaults = dict(
        mission="m",
        branch="b",
        allowed_files=("hermes_cli/native_engineer/**",),
        forbidden_files=(),
        acceptance_criteria=("add repo map", "add work packet"),
        verification_commands=("pytest -q",),
        rollback_plan="git rm",
        metadata=(),
    )
    defaults.update(overrides)
    return WorkPacket(**defaults)


def _green_result() -> TestResult:
    return TestResult(
        command=TestCommand(argv=("pytest",)),
        returncode=0,
        stdout="2 passed",
        stderr="",
        duration_seconds=0.1,
        parsed={"passed": 2, "failed": 0, "errors": 0},
    )


def _red_result() -> TestResult:
    return TestResult(
        command=TestCommand(argv=("pytest",)),
        returncode=1,
        stdout="FAILED tests/x.py::test_y",
        stderr="",
        duration_seconds=0.1,
        parsed={"passed": 0, "failed": 1, "errors": 0},
    )


def test_evaluate_passes_when_all_validations_allowed_and_green_and_criteria_referenced():
    packet = _packet()
    patches = [
        Patch(target_path="hermes_cli/native_engineer/repo_map.py", operation="create",
              after="x", rationale="add repo map"),
        Patch(target_path="hermes_cli/native_engineer/work_packet.py", operation="create",
              after="x", rationale="add work packet"),
    ]
    validations = tuple(validate(p, packet) for p in patches)
    evidence = Evidence(
        patches=tuple(patches), validations=validations, test_results=(_green_result(),)
    )
    verdict = evaluate(packet, evidence)
    assert verdict.passed is True
    assert verdict.reasons == ()
    assert verdict.missing == ()


def test_evaluate_fails_on_rejected_validation():
    packet = _packet()
    bad = Patch(target_path="hermes_cli/main.py", operation="create",
                after="x", rationale="add repo map; add work packet")
    val = validate(bad, packet)
    evidence = Evidence(patches=(bad,), validations=(val,), test_results=(_green_result(),))
    verdict = evaluate(packet, evidence)
    assert verdict.passed is False
    assert any("validation rejected" in r for r in verdict.reasons)


def test_evaluate_fails_without_green_and_without_skip_reason():
    packet = _packet()
    good = Patch(target_path="hermes_cli/native_engineer/x.py", operation="create",
                 after="x", rationale="add repo map; add work packet")
    val = validate(good, packet)
    evidence = Evidence(patches=(good,), validations=(val,), test_results=(_red_result(),))
    verdict = evaluate(packet, evidence)
    assert verdict.passed is False
    assert any("no green test result" in r for r in verdict.reasons)


def test_evaluate_passes_with_skip_reason_when_no_green_run():
    packet = _packet(metadata=(("test_skip_reason", "no executable env"),))
    good = Patch(target_path="hermes_cli/native_engineer/x.py", operation="create",
                 after="x", rationale="add repo map; add work packet")
    val = validate(good, packet)
    evidence = Evidence(patches=(good,), validations=(val,), test_results=())
    verdict = evaluate(packet, evidence)
    assert verdict.passed is True


def test_evaluate_reports_missing_criteria():
    packet = _packet(acceptance_criteria=("ship rocket fuel",))
    good = Patch(target_path="hermes_cli/native_engineer/x.py", operation="create",
                 after="x", rationale="unrelated change")
    val = validate(good, packet)
    evidence = Evidence(patches=(good,), validations=(val,), test_results=(_green_result(),))
    verdict = evaluate(packet, evidence)
    assert verdict.passed is False
    assert "ship rocket fuel" in verdict.missing
