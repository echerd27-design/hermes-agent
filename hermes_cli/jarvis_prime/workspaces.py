"""Workspace inspection — repo state seen by JARVIS Prime.

Stub: produces a deterministic Workspace from the repo_root string with no
filesystem access. Future wave PRs replace ``detect`` with real git
inspection (branch, dirty flag, allowed/disallowed paths) while keeping
the Workspace dataclass stable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workspace:
    """A repo workspace JARVIS Prime is operating against."""

    repo_root: str
    branch: str
    dirty: bool
    allowed_files: tuple[str, ...]
    disallowed_files: tuple[str, ...]


def detect(repo_root: str | None) -> Workspace:
    """Return a Workspace for ``repo_root`` (stub: no filesystem access)."""
    return Workspace(
        repo_root=repo_root or "",
        branch="unknown",
        dirty=False,
        allowed_files=(),
        disallowed_files=(),
    )
