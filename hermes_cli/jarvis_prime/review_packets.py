"""Review packet schema + markdown renderer for Codex reviewer tasks.

Codex acts as an independent reviewer of Hermes PRs/branches. Today every
builder hand-rolls an ad-hoc markdown blob to hand off; this module replaces
that with a single, deterministic schema so any agent or human can assemble
a packet the same way and produce output Codex can consume reliably.

Design goals
------------
- **Stdlib-only.** No network, no GitHub API, no LLM. The schema is pure
  data; constructing a packet is a question of filling fields, not of
  reaching out to external services.
- **Deterministic.** Same packet in → same markdown out, byte for byte.
  This lets tests assert on exact strings and lets diffing two packets
  highlight only meaningful changes.
- **Immutable.** All dataclasses are frozen — once a packet is built it
  cannot be mutated. Callers that need a tweaked copy use
  ``dataclasses.replace``.
- **Codex-friendly markdown.** Section headings are stable, decision is
  prominent near the top, security findings get a callout, and a missing
  test-evidence block surfaces as a warning so the reviewer cannot miss
  it.

The three review decisions mirror GitHub's PR-review verbs but use
lowercase snake_case at the data layer (``approve``, ``request_changes``,
``comment``); rendering converts them to display form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# =============================================================================
# Schema
# =============================================================================

VALID_DECISIONS: tuple[str, ...] = ("approve", "request_changes", "comment")
"""Allowed values for ``ReviewPacket.decision`` (lowercase, snake_case)."""

VALID_STATUSES: tuple[str, ...] = ("pass", "fail", "todo", "n/a")
"""Allowed values for ``ChecklistItem.status``."""


@dataclass(frozen=True)
class ChecklistItem:
    """One row in a security or regression checklist.

    Attributes:
        label: short human-readable name of the check (e.g. ``"Secrets
            handling"``).
        status: one of ``pass`` / ``fail`` / ``todo`` / ``n/a``. Defaults
            to ``todo`` so a freshly-built checklist starts unanswered.
        note: optional one-line elaboration (a reason for ``fail``, a
            justification for ``n/a``, or any extra context).
    """

    label: str
    status: str = "todo"
    note: str = ""


@dataclass(frozen=True)
class TestEvidence:
    """One executed test run, with its command and result.

    Attributes:
        command: the exact shell command that was run, suitable to copy
            and re-run (e.g. ``"pytest tests/test_foo.py"``).
        passed: True if the command exited 0, False otherwise.
        summary: short result excerpt — usually the tail of pytest's
            summary line, e.g. ``"12 passed in 4.1s"``.
    """

    # Tell pytest not to try collecting this dataclass as a test class.
    __test__ = False

    command: str
    passed: bool
    summary: str = ""


@dataclass(frozen=True)
class FixRecommendation:
    """One bounded suggestion the reviewer would like the builder to apply.

    Attributes:
        file: path to the file to change. Empty string is permitted for
            cross-cutting suggestions that don't target a single file.
        change: a bounded, single-paragraph description of what to change.
            Keep it tight — a recommendation is a nudge, not a rewrite.
        rationale: optional explanation of *why* the change matters.
    """

    file: str
    change: str
    rationale: str = ""


@dataclass(frozen=True)
class ReviewPacket:
    """The full briefing a Codex reviewer needs to act on a PR/branch.

    All sequence fields are tuples so the packet is hashable and immutable.

    Attributes:
        subject: short identifier of what is under review — typically
            ``"PR #123"`` or ``"branch foo/bar"``.
        mission: 1-3 sentences explaining what this change is trying to
            accomplish.
        files_changed: tuple of repo-relative file paths.
        acceptance_criteria: tuple of one-line criteria the change must
            satisfy.
        diff_summary: a short prose summary of the diff (not the diff
            itself — Codex can fetch that separately if needed).
        test_evidence: tuple of ``TestEvidence`` rows. Empty tuple means
            "no tests were run" and triggers a warning in the rendered
            markdown.
        security_checklist: tuple of ``ChecklistItem``. A single item with
            ``status="fail"`` adds a security-finding callout at the top
            of the rendered markdown.
        regression_checklist: tuple of ``ChecklistItem`` covering
            golden-path / edge-case / performance considerations.
        decision: one of ``VALID_DECISIONS``.
        fix_recommendations: tuple of ``FixRecommendation``. If empty, the
            "Fix Recommendations" section is omitted from the render.
        reviewer_notes: free-text additional commentary from the reviewer.
    """

    subject: str
    mission: str
    files_changed: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    diff_summary: str
    test_evidence: tuple[TestEvidence, ...]
    security_checklist: tuple[ChecklistItem, ...]
    regression_checklist: tuple[ChecklistItem, ...]
    decision: str
    fix_recommendations: tuple[FixRecommendation, ...] = ()
    reviewer_notes: str = ""


# =============================================================================
# Validation
# =============================================================================


def normalize_decision(value: str) -> str:
    """Return the canonical lowercase decision string, or raise ``ValueError``.

    Accepts any casing (``"APPROVE"``, ``"Approve"``, ``"approve"``) and
    tolerates a single space in place of the underscore in
    ``"request changes"``. Anything else raises ``ValueError`` with the
    list of allowed values, so callers get a clear error rather than a
    silently-rendered bad packet.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"decision must be a str, got {type(value).__name__}"
        )
    canon = value.strip().lower().replace(" ", "_")
    if canon not in VALID_DECISIONS:
        raise ValueError(
            f"decision must be one of {VALID_DECISIONS!r}, got {value!r}"
        )
    return canon


# =============================================================================
# Default checklists
#
# Callers are free to override or extend these — they exist so a freshly
# minted packet starts with a sensible structure rather than an empty list.
# =============================================================================


def default_security_checklist() -> tuple[ChecklistItem, ...]:
    """Return the standard security checks every packet should consider."""
    return (
        ChecklistItem("Secrets handling — no secrets in code, logs, fixtures"),
        ChecklistItem("AuthN / AuthZ — caller identity and permissions checked"),
        ChecklistItem("Input validation — untrusted input bounded and typed"),
        ChecklistItem("Injection — SQL / shell / template inputs escaped"),
        ChecklistItem("Dependency safety — no new compromised or unpinned deps"),
    )


def default_regression_checklist() -> tuple[ChecklistItem, ...]:
    """Return the standard regression checks every packet should consider."""
    return (
        ChecklistItem("Golden path — primary use case still works"),
        ChecklistItem("Edge cases — empty / max / unicode / concurrent inputs"),
        ChecklistItem("Error paths — failures surface usefully, never silently"),
        ChecklistItem("Performance — no obvious regression in hot paths"),
        ChecklistItem("Rollback — change is revertible without data loss"),
    )


# =============================================================================
# Renderer
# =============================================================================


_DECISION_DISPLAY: dict[str, str] = {
    "approve": "APPROVE",
    "request_changes": "REQUEST CHANGES",
    "comment": "COMMENT",
}

_STATUS_BOX: dict[str, str] = {
    "pass": "[x]",
    "fail": "[ ]",
    "todo": "[ ]",
    "n/a": "[~]",
}


def _render_checklist_item(item: ChecklistItem) -> str:
    """Render one checklist row as a markdown list line."""
    box = _STATUS_BOX.get(item.status, "[ ]")
    if item.status == "fail":
        line = f"- {box} ⚠️ {item.label} — **fail**"
    elif item.status == "pass":
        line = f"- {box} {item.label} — pass"
    elif item.status == "n/a":
        line = f"- {box} {item.label} — n/a"
    else:
        line = f"- {box} {item.label} — todo"
    if item.note:
        line += f" — note: {item.note}"
    return line


def _render_checklist(items: Iterable[ChecklistItem]) -> list[str]:
    return [_render_checklist_item(it) for it in items]


def _render_test_evidence(rows: tuple[TestEvidence, ...]) -> list[str]:
    """Render the test-evidence table, or a warning blockquote if empty."""
    if not rows:
        return [
            "> ⚠️ No test evidence supplied. Reviewer should treat this packet",
            "> as incomplete unless a written reason for skipping tests is",
            "> provided in `reviewer_notes`.",
        ]
    lines = [
        "| Command | Result | Notes |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        result = "✓ pass" if row.passed else "✗ fail"
        notes = row.summary.replace("|", "\\|") if row.summary else ""
        cmd = row.command.replace("|", "\\|")
        lines.append(f"| `{cmd}` | {result} | {notes} |")
    return lines


def _has_security_finding(items: Iterable[ChecklistItem]) -> bool:
    return any(it.status == "fail" for it in items)


def render_review_packet(packet: ReviewPacket) -> str:
    """Render the packet as deterministic markdown suitable for Codex.

    The output is stable: same packet → same string, byte for byte. No
    timestamps, no random ordering. Trailing whitespace is stripped from
    each line; the document always ends with a single newline.
    """
    decision = normalize_decision(packet.decision)
    out: list[str] = []

    out.append(f"# Review Packet — {packet.subject}")
    out.append("")
    out.append(f"**Decision:** {_DECISION_DISPLAY[decision]}")
    out.append("")

    if _has_security_finding(packet.security_checklist):
        out.append("> ⚠️ Security finding present.")
        out.append("")

    out.append("## Mission")
    out.append(packet.mission.strip() if packet.mission else "_(not provided)_")
    out.append("")

    out.append("## Acceptance Criteria")
    if packet.acceptance_criteria:
        for crit in packet.acceptance_criteria:
            out.append(f"- [ ] {crit}")
    else:
        out.append("_(none provided)_")
    out.append("")

    out.append(f"## Files Changed ({len(packet.files_changed)})")
    if packet.files_changed:
        for path in packet.files_changed:
            out.append(f"- `{path}`")
    else:
        out.append("_(none provided)_")
    out.append("")

    out.append("## Diff Summary")
    out.append(
        packet.diff_summary.strip() if packet.diff_summary else "_(not provided)_"
    )
    out.append("")

    out.append("## Test Evidence")
    out.extend(_render_test_evidence(packet.test_evidence))
    out.append("")

    out.append("## Security Checklist")
    if packet.security_checklist:
        out.extend(_render_checklist(packet.security_checklist))
    else:
        out.append("_(none provided)_")
    out.append("")

    out.append("## Regression Checklist")
    if packet.regression_checklist:
        out.extend(_render_checklist(packet.regression_checklist))
    else:
        out.append("_(none provided)_")
    out.append("")

    if packet.fix_recommendations:
        out.append("## Fix Recommendations")
        for i, rec in enumerate(packet.fix_recommendations, start=1):
            target = f"`{rec.file}`" if rec.file else "_(cross-cutting)_"
            line = f"{i}. {target} — {rec.change}"
            if rec.rationale:
                line += f" (rationale: {rec.rationale})"
            out.append(line)
        out.append("")

    if packet.reviewer_notes:
        out.append("## Reviewer Notes")
        out.append(packet.reviewer_notes.strip())
        out.append("")

    return "\n".join(line.rstrip() for line in out).rstrip() + "\n"
