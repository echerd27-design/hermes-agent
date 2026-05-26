"""Hermes Native Engineer — isolated, stdlib-only authoring harness.

W14 scope: core bench only. Not wired into the router, model registry,
jarvis_prime runtime, or context/memory layers. Validate-only patches —
no disk writes from this package in W14.
"""
from __future__ import annotations

from .evaluator import Evidence, Verdict, evaluate
from .patch_engine import (
    Patch,
    PatchValidationResult,
    dry_run_diff,
    rollback_notes,
    validate,
)
from .repair_loop import RepairInstruction, derive_instructions
from .repo_map import (
    DEFAULT_IGNORE,
    FileEntry,
    RepoMap,
    classify,
    extract_python_symbols,
    scan,
)
from .sop_miner import SOPRecord, mine, to_markdown
from .test_runner import (
    TestCommand,
    TestResult,
    make_compileall_command,
    make_pytest_command,
    parse_pytest_output,
    parse_unittest_output,
    run,
)
from .work_packet import WorkPacket

__all__ = [
    "DEFAULT_IGNORE",
    "Evidence",
    "FileEntry",
    "Patch",
    "PatchValidationResult",
    "RepairInstruction",
    "RepoMap",
    "SOPRecord",
    "TestCommand",
    "TestResult",
    "Verdict",
    "WorkPacket",
    "classify",
    "derive_instructions",
    "dry_run_diff",
    "evaluate",
    "extract_python_symbols",
    "make_compileall_command",
    "make_pytest_command",
    "mine",
    "parse_pytest_output",
    "parse_unittest_output",
    "rollback_notes",
    "run",
    "scan",
    "to_markdown",
    "validate",
]
