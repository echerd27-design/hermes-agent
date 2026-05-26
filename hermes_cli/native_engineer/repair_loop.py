"""Deterministic test-failure → repair-instruction translator.

No model calls. Pure-function mapping from ``TestResult`` to a tuple of
``RepairInstruction`` records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .test_runner import TestResult

_FAILED_LINE_RE = re.compile(r"^FAILED\s+(?P<target>\S+)(?:\s+-\s+(?P<msg>.*))?$")
_IMPORT_ERR_RE = re.compile(
    r"(?:ImportError|ModuleNotFoundError):\s*(?:No module named\s+)?['\"]?([\w\.]+)['\"]?"
)


@dataclass(frozen=True)
class RepairInstruction:
    target_path: str
    rationale: str
    hint: str
    severity: str  # "low" | "medium" | "high"


def _target_path_from_nodeid(nodeid: str) -> str:
    if "::" in nodeid:
        return nodeid.split("::", 1)[0]
    return nodeid


def _find_import_error(text: str) -> Optional[str]:
    match = _IMPORT_ERR_RE.search(text or "")
    if match:
        return match.group(1)
    return None


def derive_instructions(test_result: TestResult) -> tuple[RepairInstruction, ...]:
    instructions: list[RepairInstruction] = []
    parsed = test_result.parsed or {}

    if test_result.returncode is None:
        instructions.append(
            RepairInstruction(
                target_path=test_result.command.argv[-1] if test_result.command.argv else "",
                rationale="test run timed out",
                hint="increase timeout_seconds or split the test selection",
                severity="medium",
            )
        )
        return tuple(instructions)

    failed_count = int(parsed.get("failed", 0) or 0)
    error_count = int(parsed.get("errors", 0) or 0)
    if test_result.returncode == 0 and failed_count == 0 and error_count == 0:
        return ()

    combined = (test_result.stdout or "") + "\n" + (test_result.stderr or "")
    missing_mod = _find_import_error(combined)
    if missing_mod:
        instructions.append(
            RepairInstruction(
                target_path=missing_mod.replace(".", "/") + ".py",
                rationale=f"missing import: {missing_mod}",
                hint=f"install or create module '{missing_mod}', or fix the import path",
                severity="high",
            )
        )

    for line in (test_result.stdout or "").splitlines():
        match = _FAILED_LINE_RE.match(line.strip())
        if not match:
            continue
        nodeid = match.group("target")
        msg = (match.group("msg") or "").strip()
        target = _target_path_from_nodeid(nodeid)
        hint = msg[:200] if msg else "inspect failing test output for assertion details"
        instructions.append(
            RepairInstruction(
                target_path=target,
                rationale=f"test failed: {nodeid}",
                hint=hint,
                severity="medium",
            )
        )

    if not instructions and (failed_count or error_count):
        instructions.append(
            RepairInstruction(
                target_path="",
                rationale=f"non-zero return with failed={failed_count} errors={error_count}",
                hint="inspect stdout/stderr; no FAILED lines parsed",
                severity="medium",
            )
        )

    return tuple(instructions)
