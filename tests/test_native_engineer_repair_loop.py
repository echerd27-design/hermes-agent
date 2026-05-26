"""Tests for hermes_cli.native_engineer.repair_loop."""
from __future__ import annotations

from hermes_cli.native_engineer.repair_loop import derive_instructions
from hermes_cli.native_engineer.test_runner import TestCommand, TestResult


def _result(
    *,
    returncode: int | None,
    stdout: str = "",
    stderr: str = "",
    parsed: dict | None = None,
) -> TestResult:
    return TestResult(
        command=TestCommand(argv=("python", "-m", "pytest", "tests/")),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=0.01,
        parsed=parsed or {"passed": 0, "failed": 0, "errors": 0, "failed_tests": []},
    )


def test_empty_on_green_run():
    result = _result(
        returncode=0,
        parsed={"passed": 3, "failed": 0, "errors": 0, "failed_tests": []},
    )
    assert derive_instructions(result) == ()


def test_import_error_produces_high_severity_instruction():
    result = _result(
        returncode=1,
        stderr="ModuleNotFoundError: No module named 'widget_lib'",
        parsed={"passed": 0, "failed": 0, "errors": 1, "failed_tests": []},
    )
    insts = derive_instructions(result)
    assert any(i.severity == "high" and "widget_lib" in i.rationale for i in insts)


def test_failed_lines_become_medium_instructions():
    stdout = (
        "FAILED tests/test_a.py::test_one - AssertionError: 1 != 2\n"
        "FAILED tests/test_b.py::test_two - ValueError: bad\n"
    )
    result = _result(
        returncode=1,
        stdout=stdout,
        parsed={"passed": 0, "failed": 2, "errors": 0, "failed_tests": []},
    )
    insts = derive_instructions(result)
    targets = [i.target_path for i in insts]
    assert "tests/test_a.py" in targets
    assert "tests/test_b.py" in targets
    for i in insts:
        if i.target_path.startswith("tests/"):
            assert i.severity == "medium"
            assert i.hint  # non-empty


def test_timeout_produces_medium_instruction():
    result = _result(returncode=None, parsed={"timed_out": True})
    insts = derive_instructions(result)
    assert len(insts) == 1
    assert insts[0].severity == "medium"
    assert "timeout" in insts[0].hint.lower() or "timeout" in insts[0].rationale.lower()


def test_nonzero_without_failed_lines_emits_fallback():
    result = _result(
        returncode=1,
        stdout="weird output\n",
        parsed={"passed": 0, "failed": 1, "errors": 0, "failed_tests": []},
    )
    insts = derive_instructions(result)
    assert insts  # at least one instruction
