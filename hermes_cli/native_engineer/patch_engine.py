"""Validate-only patch envelope for the Hermes Native Engineer.

W14 contract: the patch engine NEVER writes to disk. It validates a patch
against a WorkPacket allow/deny contract and renders a unified diff.
Actual application is reserved for a future sprint behind an explicit
owner-approval gate.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Iterable, Optional

from .work_packet import WorkPacket

_VALID_OPS: frozenset[str] = frozenset({"create", "modify", "delete"})


@dataclass(frozen=True)
class Patch:
    target_path: str
    operation: str  # "create" | "modify" | "delete"
    before: Optional[str] = None
    after: Optional[str] = None
    rationale: str = ""


@dataclass(frozen=True)
class PatchValidationResult:
    patch: Patch
    allowed: bool
    reason: str
    dry_run_diff: str


def dry_run_diff(patch: Patch) -> str:
    """Render a unified diff for the proposed patch."""
    before_lines = (patch.before or "").splitlines(keepends=True)
    after_lines = (patch.after or "").splitlines(keepends=True)
    fromfile = f"a/{patch.target_path}"
    tofile = f"b/{patch.target_path}"
    if patch.operation == "create":
        fromfile = "/dev/null"
    elif patch.operation == "delete":
        tofile = "/dev/null"
    diff = difflib.unified_diff(
        before_lines, after_lines, fromfile=fromfile, tofile=tofile
    )
    return "".join(diff)


def validate(patch: Patch, packet: WorkPacket) -> PatchValidationResult:
    """Check the patch against the packet contract. Pure function."""
    if patch.operation not in _VALID_OPS:
        return PatchValidationResult(
            patch=patch,
            allowed=False,
            reason=f"unknown operation: {patch.operation!r}",
            dry_run_diff="",
        )

    if not packet.is_path_allowed(patch.target_path):
        return PatchValidationResult(
            patch=patch,
            allowed=False,
            reason=f"path not in allowed_files: {patch.target_path}",
            dry_run_diff="",
        )

    if patch.operation in ("modify", "delete") and patch.before is None:
        return PatchValidationResult(
            patch=patch,
            allowed=False,
            reason=f"{patch.operation} requires 'before' content",
            dry_run_diff="",
        )

    if patch.operation in ("create", "modify") and patch.after is None:
        return PatchValidationResult(
            patch=patch,
            allowed=False,
            reason=f"{patch.operation} requires 'after' content",
            dry_run_diff="",
        )

    return PatchValidationResult(
        patch=patch,
        allowed=True,
        reason="ok",
        dry_run_diff=dry_run_diff(patch),
    )


def rollback_notes(patches: Iterable[Patch]) -> str:
    """Human-readable inverse of the given patch sequence."""
    lines: list[str] = ["Rollback plan:"]
    for patch in patches:
        if patch.operation == "create":
            lines.append(f"  - delete {patch.target_path}")
        elif patch.operation == "delete":
            lines.append(f"  - restore {patch.target_path} from prior content")
        elif patch.operation == "modify":
            lines.append(f"  - revert {patch.target_path} to prior content")
        else:
            lines.append(f"  - unknown op {patch.operation!r} on {patch.target_path}")
    if len(lines) == 1:
        lines.append("  (no patches)")
    return "\n".join(lines)
