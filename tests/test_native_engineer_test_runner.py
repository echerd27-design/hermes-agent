"""Tests for hermes_cli.native_engineer.test_runner."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from hermes_cli.native_engineer.test_runner import (
    TestCommand,
    make_compileall_command,
    make_pytest_command,
    parse_pytest_output,
    parse_unittest_output,
    run,
)


PYTEST_SUMMARY_SAMPLE = """\
============================= test session starts ==============================
collected 3 items

tests/test_one.py::test_a PASSED                                          [ 33%]
tests/test_one.py::test_b PASSED                                          [ 66%]
tests/test_two.py::test_c FAILED                                          [100%]

=================================== FAILURES ===================================
FAILED tests/test_two.py::test_c - AssertionError: expected 1, got 2
========================= 2 passed, 1 failed in 0.42s ==========================
"""

PYTEST_NO_TESTS_SAMPLE = """\
============================= test session starts ==============================
collected 0 items

============================ no tests ran in 0.01s =============================
"""

UNITTEST_OK_SAMPLE = """\
test_a (mod.TestX) ... ok
test_b (mod.TestX) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.001s

OK
"""

UNITTEST_FAIL_SAMPLE = """\
test_a (mod.TestX) ... FAIL

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (failures=1, errors=0)
"""


def test_parse_pytest_summary_counts():
    parsed = parse_pytest_output(PYTEST_SUMMARY_SAMPLE)
    assert parsed["passed"] == 2
    assert parsed["failed"] == 1
    assert parsed["errors"] == 0
    assert parsed["failed_tests"] == ["tests/test_two.py::test_c - AssertionError: expected 1, got 2"]
    assert parsed["no_tests"] is False


def test_parse_pytest_handles_no_tests():
    parsed = parse_pytest_output(PYTEST_NO_TESTS_SAMPLE)
    assert parsed["passed"] == 0
    assert parsed["failed"] == 0
    assert parsed["no_tests"] is True


def test_parse_unittest_ok():
    parsed = parse_unittest_output(UNITTEST_OK_SAMPLE)
    assert parsed["ran"] == 2
    assert parsed["failures"] == 0
    assert parsed["ok"] is True


def test_parse_unittest_failures():
    parsed = parse_unittest_output(UNITTEST_FAIL_SAMPLE)
    assert parsed["ran"] == 1
    assert parsed["failures"] == 1
    assert parsed["ok"] is False


def test_run_executes_inline_python_command():
    cmd = TestCommand(argv=(sys.executable, "-c", "print('hi-from-runner')"))
    result = run(cmd)
    assert result.returncode == 0
    assert "hi-from-runner" in result.stdout


def test_run_captures_nonzero_exit():
    cmd = TestCommand(argv=(sys.executable, "-c", "import sys; sys.exit(2)"))
    result = run(cmd)
    assert result.returncode == 2


def test_run_timeout_returns_none_returncode():
    cmd = TestCommand(argv=(sys.executable, "-c", "pass"), timeout_seconds=1)
    # Mock subprocess.run inside the test_runner module to raise
    # TimeoutExpired without actually spawning a sleeping subprocess. This
    # also avoids the project's live-system kill-guard in conftest.py.
    with patch(
        "hermes_cli.native_engineer.test_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=list(cmd.argv), timeout=1),
    ):
        result = run(cmd)
    assert result.returncode is None
    assert result.parsed.get("timed_out") is True


def test_make_pytest_command_shape():
    cmd = make_pytest_command(["tests/test_native_engineer_repo_map.py"], extra_args=("-q",))
    assert cmd.argv[0] == sys.executable
    assert "pytest" in cmd.argv
    assert "tests/test_native_engineer_repo_map.py" in cmd.argv
    assert "-q" in cmd.argv


def test_make_compileall_command_shape():
    cmd = make_compileall_command("hermes_cli/native_engineer")
    assert cmd.argv[:3] == (sys.executable, "-m", "compileall")
    assert cmd.argv[-1] == "hermes_cli/native_engineer"
