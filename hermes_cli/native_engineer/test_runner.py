"""Bounded test dispatch + output parser for the Hermes Native Engineer.

The runner does not execute arbitrary user-provided commands. The caller
must build a TestCommand explicitly via one of the small set of builders
(or the dataclass constructor) and pass it to ``run``.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class TestCommand:
    argv: tuple[str, ...]
    cwd: Optional[str] = None
    env_overlay: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    timeout_seconds: int = 600

    # Pytest sees the leading "Test" and tries to collect this dataclass as
    # a test class. Opt out — this is a domain object, not a test suite.
    __test__ = False


@dataclass(frozen=True)
class TestResult:
    command: TestCommand
    returncode: Optional[int]
    stdout: str
    stderr: str
    duration_seconds: float
    parsed: dict[str, Any]

    __test__ = False


_PYTEST_SUMMARY_RE = re.compile(
    r"(?P<count>\d+)\s+(?P<label>passed|failed|errors?|skipped|xfailed|xpassed|warnings?)",
    re.IGNORECASE,
)

_UNITTEST_RAN_RE = re.compile(r"^Ran\s+(\d+)\s+tests?", re.MULTILINE)
_UNITTEST_FAIL_RE = re.compile(r"failures=(\d+)")
_UNITTEST_ERR_RE = re.compile(r"errors=(\d+)")


def parse_pytest_output(text: str) -> dict[str, Any]:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    failed_tests: list[str] = []
    if not text:
        return {**counts, "failed_tests": failed_tests, "no_tests": True}

    no_tests = "no tests ran" in text.lower()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("FAILED "):
            failed_tests.append(stripped[len("FAILED "):])

    for match in _PYTEST_SUMMARY_RE.finditer(text):
        label = match.group("label").lower()
        count = int(match.group("count"))
        if label.startswith("error"):
            counts["errors"] = count
        elif label.startswith("warning"):
            continue
        elif label in counts:
            counts[label] = count

    return {**counts, "failed_tests": failed_tests, "no_tests": no_tests}


def parse_unittest_output(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"ran": 0, "failures": 0, "errors": 0, "ok": False}
    if not text:
        return result
    ran = _UNITTEST_RAN_RE.search(text)
    if ran:
        result["ran"] = int(ran.group(1))
    fail = _UNITTEST_FAIL_RE.search(text)
    if fail:
        result["failures"] = int(fail.group(1))
    err = _UNITTEST_ERR_RE.search(text)
    if err:
        result["errors"] = int(err.group(1))
    result["ok"] = "\nOK" in text or text.strip().endswith("OK")
    return result


def run(command: TestCommand) -> TestResult:
    """Execute the given TestCommand. Captures stdout/stderr, enforces timeout.

    Catches ``subprocess.TimeoutExpired`` and surfaces ``returncode=None``.
    """
    env = os.environ.copy()
    for k, v in command.env_overlay:
        env[k] = v

    start = time.monotonic()
    try:
        completed = subprocess.run(
            list(command.argv),
            cwd=command.cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=command.timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - start
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        parsed = parse_pytest_output(stdout + "\n" + stderr)
        return TestResult(
            command=command,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            parsed=parsed,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        parsed = parse_pytest_output(stdout + "\n" + stderr)
        parsed["timed_out"] = True
        return TestResult(
            command=command,
            returncode=None,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            parsed=parsed,
        )


def make_pytest_command(
    test_paths: Iterable[str],
    extra_args: Iterable[str] = (),
    cwd: Optional[str] = None,
    timeout_seconds: int = 600,
) -> TestCommand:
    argv: tuple[str, ...] = (
        sys.executable,
        "-m",
        "pytest",
        *tuple(test_paths),
        *tuple(extra_args),
    )
    return TestCommand(argv=argv, cwd=cwd, timeout_seconds=timeout_seconds)


def make_compileall_command(
    target: str,
    cwd: Optional[str] = None,
    timeout_seconds: int = 300,
) -> TestCommand:
    argv: tuple[str, ...] = (sys.executable, "-m", "compileall", "-q", target)
    return TestCommand(argv=argv, cwd=cwd, timeout_seconds=timeout_seconds)
