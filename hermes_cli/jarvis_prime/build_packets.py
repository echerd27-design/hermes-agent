"""Strict build-packet schema for briefing JARVIS Prime worker tasks.

A ``BuildPacket`` is the typed contract handed from the operator (or
JARVIS Prime in Operator/Builder mode) to a downstream worker such as the
Claude Code Builder, Codex Reviewer, Codex Bounded Fix Worker, or Local
Test Runner described in ``docs/jarvis-prime-operating-system.md``.

The schema is intentionally stdlib-only so it can be imported from the
gateway, CLI, and skill layers without extra dependencies.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from typing import Any


class BuildPacketError(ValueError):
    """Raised when a build packet fails schema validation or deserialization."""


class Worker(str, Enum):
    """Worker roles that can receive a build packet.

    Values mirror the Worker list in ``docs/jarvis-prime-operating-system.md``.
    Subclassing ``str`` lets instances serialize transparently through
    ``json.dumps`` while still supporting ``Worker("claude_code_builder")``
    coercion from strings.
    """

    CLAUDE_CODE_BUILDER = "claude_code_builder"
    CODEX_REVIEWER = "codex_reviewer"
    CODEX_BOUNDED_FIX = "codex_bounded_fix"
    LOCAL_TEST_RUNNER = "local_test_runner"


_REQUIRED_STRING_FIELDS: tuple[str, ...] = (
    "mission",
    "repo_root",
    "branch",
    "rollback_plan",
)
_REQUIRED_LIST_FIELDS: tuple[str, ...] = (
    "allowed_files",
    "acceptance_criteria",
    "verification_commands",
)
_OPTIONAL_LIST_FIELDS: tuple[str, ...] = (
    "forbidden_files",
    "non_goals",
    "owner_gated_actions",
)


def _normalize_glob(pattern: str) -> str:
    """Map ``**`` to ``*`` so ``fnmatch`` can approximate recursive globs.

    ``fnmatch`` has no native ``**`` support; collapsing it to a single
    star lets ``gateway/**`` match ``gateway/main.py`` for overlap
    detection. This is a deliberate approximation, documented in the
    wave report.
    """
    return pattern.replace("**", "*")


def _patterns_overlap(a: str, b: str) -> bool:
    """True when ``a`` and ``b`` cover any common path.

    Checked in both directions so a literal path on either side conflicts
    with a glob on the other.
    """
    na, nb = _normalize_glob(a), _normalize_glob(b)
    return fnmatch.fnmatchcase(a, nb) or fnmatch.fnmatchcase(b, na)


@dataclass
class BuildPacket:
    """Typed brief for a single worker task.

    Required (non-empty) fields: ``mission``, ``repo_root``, ``branch``,
    ``worker``, ``allowed_files``, ``acceptance_criteria``. The remaining
    fields default to empty containers and are rendered as ``(none)``
    placeholders by :meth:`to_markdown` so a missing field is visibly
    considered rather than silently absent.
    """

    mission: str
    repo_root: str
    branch: str
    worker: Worker
    allowed_files: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    rollback_plan: str = ""
    forbidden_files: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    owner_gated_actions: list[str] = field(default_factory=list)

    def validate(self, strict_globs: bool = True) -> None:
        """Raise :class:`BuildPacketError` if the packet is unsafe to dispatch.

        Checks:
        - Required string fields are non-blank after ``strip()``
          (``mission``, ``repo_root``, ``branch``, ``rollback_plan``).
        - Required list fields contain at least one truthy entry
          (``allowed_files``, ``acceptance_criteria``,
          ``verification_commands``).
        - ``worker`` is a :class:`Worker` instance.
        - No ``allowed_files`` entry overlaps any ``forbidden_files``
          entry. When ``strict_globs`` is True (default), overlap is
          detected with bidirectional ``fnmatch`` (``**`` normalized to
          ``*``) so a literal path on one side conflicts with a
          matching glob on the other. When False, overlap is a pure
          literal-string set intersection.
        """
        errors: list[str] = []

        for name in _REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{name} is required and must be a non-blank string")

        for name in _REQUIRED_LIST_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, list) or not any(
                isinstance(item, str) and item.strip() for item in value
            ):
                errors.append(
                    f"{name} is required and must contain at least one non-blank entry"
                )

        if not isinstance(self.worker, Worker):
            errors.append("worker must be a Worker enum member")

        overlaps: list[str] = []
        if strict_globs:
            for allowed in self.allowed_files:
                for forbidden in self.forbidden_files:
                    if _patterns_overlap(allowed, forbidden):
                        overlaps.append(f"{allowed!r} overlaps {forbidden!r}")
        else:
            shared = set(self.allowed_files) & set(self.forbidden_files)
            overlaps = [f"{path!r} overlaps {path!r}" for path in sorted(shared)]
        if overlaps:
            errors.append(
                "allowed_files and forbidden_files must not overlap: "
                + "; ".join(overlaps)
            )

        if errors:
            raise BuildPacketError("; ".join(errors))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation with ``worker`` as its string value."""
        data = asdict(self)
        data["worker"] = (
            self.worker.value if isinstance(self.worker, Worker) else self.worker
        )
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BuildPacket":
        """Build a packet from a dict.

        Lenient on unknown keys (ignored) so future schema additions do
        not break old persisted packets. Strict on type mismatches and
        unknown worker values; both raise :class:`BuildPacketError`.

        Does *not* call :meth:`validate` — draft packets can be
        deserialized and edited before they are dispatched.
        """
        if not isinstance(data, Mapping):
            raise BuildPacketError("from_dict requires a mapping")

        known = {f.name for f in fields(cls)}
        kwargs: dict[str, Any] = {}

        for name in _REQUIRED_STRING_FIELDS + ("rollback_plan",):
            if name in data:
                value = data[name]
                if not isinstance(value, str):
                    raise BuildPacketError(f"{name} must be a string")
                kwargs[name] = value

        list_field_names = _REQUIRED_LIST_FIELDS + _OPTIONAL_LIST_FIELDS
        for name in list_field_names:
            if name in data:
                value = data[name]
                if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value
                ):
                    raise BuildPacketError(f"{name} must be a list of strings")
                kwargs[name] = list(value)

        if "worker" in data:
            raw = data["worker"]
            if isinstance(raw, Worker):
                kwargs["worker"] = raw
            elif isinstance(raw, str):
                try:
                    kwargs["worker"] = Worker(raw)
                except ValueError as exc:
                    raise BuildPacketError(f"unknown worker value: {raw!r}") from exc
            else:
                raise BuildPacketError("worker must be a string or Worker member")

        for required in ("mission", "repo_root", "branch", "worker"):
            kwargs.setdefault(required, "" if required != "worker" else None)

        unknown = set(data) - known
        # Unknown keys are intentionally dropped (forward-compat); not raised.
        del unknown

        return cls(**kwargs)

    def to_markdown(self, validate: bool = True, strict_globs: bool = True) -> str:
        """Render a prompt-ready markdown packet.

        When ``validate`` is True (default), the packet is validated
        first so a malformed brief never reaches a worker. Pass
        ``validate=False`` for draft previews. ``strict_globs`` is
        forwarded to :meth:`validate` when validation runs.
        """
        if validate:
            self.validate(strict_globs=strict_globs)

        worker_value = (
            self.worker.value if isinstance(self.worker, Worker) else str(self.worker)
        )

        def _bullets(items: list[str]) -> str:
            if not items:
                return "- (none)"
            return "\n".join(f"- {item}" for item in items)

        def _checkboxes(items: list[str]) -> str:
            if not items:
                return "(none)"
            return "\n".join(f"- [ ] {item}" for item in items)

        def _code_block(items: list[str]) -> str:
            if not items:
                return "(none)"
            body = "\n".join(items)
            return f"```\n{body}\n```"

        rollback = self.rollback_plan.strip() or "(none specified)"

        sections = [
            "# Build Packet",
            "",
            "## Mission",
            self.mission,
            "",
            "## Worker",
            worker_value,
            "",
            "## Repo",
            f"- Root: {self.repo_root}",
            f"- Branch: {self.branch}",
            "",
            "## Allowed Files",
            _bullets(self.allowed_files),
            "",
            "## Forbidden Files",
            _bullets(self.forbidden_files),
            "",
            "## Non-Goals",
            _bullets(self.non_goals),
            "",
            "## Acceptance Criteria",
            _checkboxes(self.acceptance_criteria),
            "",
            "## Verification Commands",
            _code_block(self.verification_commands),
            "",
            "## Rollback Plan",
            rollback,
            "",
            "## Owner-Gated Actions",
            _bullets(self.owner_gated_actions),
            "",
        ]
        return "\n".join(sections)
