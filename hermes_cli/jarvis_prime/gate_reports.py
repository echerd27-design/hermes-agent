"""Launch-quality gate report renderers for JARVIS Prime.

This module provides pure presentation helpers that turn JARVIS gate
results into markdown, mobile, JSON, failure-only, and owner-approval
views. The evaluator that produces gate results lives elsewhere; this
module never imports it and instead accepts duck-typed input (objects
with attributes or plain dicts), so renderer output is independent of
any specific runtime gate implementation.

Canonical gate keys (matching ``docs/jarvis-verification-gates.md``)
are ``planning``, ``build``, ``review``, ``test``, ``security``,
``release``, ``owner_approval``, and ``rollback``. Statuses are
``pass``, ``fail``, ``owner_approval``, and ``skipped``. Every report
always renders all eight canonical gates; missing gates are synthesized
as ``skipped`` with ``message="not run"`` so output shape is
deterministic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypedDict


# ── Status constants ──────────────────────────────────────────────────

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_OWNER_APPROVAL = "owner_approval"
STATUS_SKIPPED = "skipped"

VALID_STATUSES = frozenset({
    STATUS_PASS,
    STATUS_FAIL,
    STATUS_OWNER_APPROVAL,
    STATUS_SKIPPED,
})

STATUS_DISPLAY: dict[str, str] = {
    STATUS_PASS: "PASS",
    STATUS_FAIL: "FAIL",
    STATUS_OWNER_APPROVAL: "OWNER APPROVAL",
    STATUS_SKIPPED: "SKIPPED",
}


# ── Gate canonical names ──────────────────────────────────────────────

GATE_ORDER: tuple[str, ...] = (
    "planning",
    "build",
    "review",
    "test",
    "security",
    "release",
    "owner_approval",
    "rollback",
)

GATE_DISPLAY_NAMES: dict[str, str] = {
    "planning": "Planning gate",
    "build": "Build gate",
    "review": "Review gate",
    "test": "Test gate",
    "security": "Security gate",
    "release": "Release gate",
    "owner_approval": "Owner approval gate",
    "rollback": "Rollback gate",
}

NAME_ALIASES: dict[str, str] = {
    "planning": "planning",
    "planning gate": "planning",
    "planning_gate": "planning",
    "plan": "planning",
    "build": "build",
    "build gate": "build",
    "build_gate": "build",
    "review": "review",
    "review gate": "review",
    "review_gate": "review",
    "test": "test",
    "test gate": "test",
    "test_gate": "test",
    "tests": "test",
    "testing": "test",
    "security": "security",
    "security gate": "security",
    "security_gate": "security",
    "sec": "security",
    "release": "release",
    "release gate": "release",
    "release_gate": "release",
    "owner_approval": "owner_approval",
    "owner approval": "owner_approval",
    "owner approval gate": "owner_approval",
    "owner-approval": "owner_approval",
    "owner-approval gate": "owner_approval",
    "owner_approval_gate": "owner_approval",
    "approval": "owner_approval",
    "owner": "owner_approval",
    "rollback": "rollback",
    "rollback gate": "rollback",
    "rollback_gate": "rollback",
    "revert": "rollback",
}

STATUS_ALIASES: dict[str, str] = {
    "pass": STATUS_PASS,
    "passed": STATUS_PASS,
    "ok": STATUS_PASS,
    "green": STATUS_PASS,
    "fail": STATUS_FAIL,
    "failed": STATUS_FAIL,
    "fails": STATUS_FAIL,
    "red": STATUS_FAIL,
    "owner_approval": STATUS_OWNER_APPROVAL,
    "owner approval": STATUS_OWNER_APPROVAL,
    "owner-approval": STATUS_OWNER_APPROVAL,
    "owner": STATUS_OWNER_APPROVAL,
    "approval": STATUS_OWNER_APPROVAL,
    "pending": STATUS_OWNER_APPROVAL,
    "needs_approval": STATUS_OWNER_APPROVAL,
    "needs approval": STATUS_OWNER_APPROVAL,
    "skipped": STATUS_SKIPPED,
    "skip": STATUS_SKIPPED,
    "not_run": STATUS_SKIPPED,
    "not run": STATUS_SKIPPED,
    "n/a": STATUS_SKIPPED,
    "na": STATUS_SKIPPED,
}


# ── Typing protocols ──────────────────────────────────────────────────

class GateResultLike(Protocol):
    """Duck contract for a gate result object."""

    name: str
    status: str
    message: str
    owner: str


class ReportLike(Protocol):
    """Duck contract for a report object."""

    gates: Sequence[Any]
    result: str
    remaining_risk: str
    next_action: str


class GateResultDict(TypedDict, total=False):
    name: str
    status: str
    message: str
    owner: str
    evidence: str


class ReportDict(TypedDict, total=False):
    gates: Sequence[Any]
    result: str
    overall: str
    remaining_risk: str
    next_action: str
    title: str
    timestamp: str


# ── Private helpers ───────────────────────────────────────────────────

_SENTINEL = object()


def _get(obj: Any, key: str, default: Any = "") -> Any:
    """Read ``key`` from ``obj`` whether it's a Mapping or has attributes.

    Returns ``default`` when the key is absent or the value is ``None``.
    """
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        value = obj.get(key, _SENTINEL)
    else:
        value = getattr(obj, key, _SENTINEL)
    if value is _SENTINEL or value is None:
        return default
    return value


def _normalize_status(raw: Any) -> str:
    """Map a free-form status value to one of VALID_STATUSES."""
    if not isinstance(raw, str):
        return STATUS_SKIPPED
    cleaned = raw.strip().lower().replace("-", "_")
    if cleaned in VALID_STATUSES:
        return cleaned
    aliased = STATUS_ALIASES.get(cleaned)
    if aliased:
        return aliased
    alt = STATUS_ALIASES.get(raw.strip().lower())
    return alt if alt else STATUS_SKIPPED


def _normalize_name(raw: Any) -> tuple[str, str]:
    """Return ``(canonical_key, display_name)`` for a gate name.

    Unknown names keep their original display form and are tagged with
    a non-canonical key (the lowercased original) so they sort to the
    end of the report.
    """
    if not isinstance(raw, str) or not raw.strip():
        return "unknown", "Unknown gate"
    text = raw.strip()
    lower = text.lower()
    canonical = NAME_ALIASES.get(lower)
    if canonical:
        return canonical, GATE_DISPLAY_NAMES[canonical]
    return lower, text


def _normalize_gate(gate: Any) -> dict[str, str]:
    """Produce a fully-shaped, canonical gate dict.

    All five string fields are always present (empty string if missing).
    ``_key`` carries the canonical sort key.
    """
    raw_name = _get(gate, "name", "")
    key, display = _normalize_name(raw_name)
    status = _normalize_status(_get(gate, "status", ""))
    message = _get(gate, "message", "")
    owner = _get(gate, "owner", "")
    evidence = _get(gate, "evidence", "")
    return {
        "_key": key,
        "name": display,
        "status": status,
        "message": str(message) if message is not None else "",
        "owner": str(owner) if owner is not None else "",
        "evidence": str(evidence) if evidence is not None else "",
    }


def _collect_gates(report: Any) -> list[dict[str, str]]:
    """Build the canonical list of 8+ gate dicts in stable order.

    - Canonical gates appear in GATE_ORDER.
    - Missing canonical gates are synthesized as SKIPPED ("not run").
    - Unknown gate keys are appended at the end in input order.
    - If multiple input rows share a canonical key, the last non-skipped
      status wins (callers that re-emit a gate after a status change get
      the latest result).
    """
    raw_gates = _get(report, "gates", [])
    if not isinstance(raw_gates, Sequence) or isinstance(raw_gates, (str, bytes)):
        raw_gates = []

    canonical_seen: dict[str, dict[str, str]] = {}
    unknown_seen: list[dict[str, str]] = []

    for entry in raw_gates:
        norm = _normalize_gate(entry)
        key = norm["_key"]
        if key in GATE_DISPLAY_NAMES:
            prev = canonical_seen.get(key)
            if prev is None or prev["status"] == STATUS_SKIPPED:
                canonical_seen[key] = norm
            else:
                canonical_seen[key] = norm
        else:
            unknown_seen.append(norm)

    ordered: list[dict[str, str]] = []
    for key in GATE_ORDER:
        if key in canonical_seen:
            ordered.append(canonical_seen[key])
        else:
            ordered.append({
                "_key": key,
                "name": GATE_DISPLAY_NAMES[key],
                "status": STATUS_SKIPPED,
                "message": "not run",
                "owner": "",
                "evidence": "",
            })
    ordered.extend(unknown_seen)
    return ordered


def _counts(gates: Sequence[dict[str, str]]) -> dict[str, int]:
    counts = {
        STATUS_PASS: 0,
        STATUS_FAIL: 0,
        STATUS_OWNER_APPROVAL: 0,
        STATUS_SKIPPED: 0,
    }
    for gate in gates:
        status = gate["status"]
        if status in counts:
            counts[status] += 1
    return counts


def _derive_overall(gates: Sequence[dict[str, str]]) -> str:
    counts = _counts(gates)
    if counts[STATUS_FAIL]:
        return STATUS_FAIL
    if counts[STATUS_OWNER_APPROVAL]:
        return STATUS_OWNER_APPROVAL
    if counts[STATUS_PASS]:
        return STATUS_PASS
    return STATUS_SKIPPED


def _overall_result(report: Any, gates: Sequence[dict[str, str]]) -> str:
    explicit = _get(report, "result", "") or _get(report, "overall", "")
    if explicit:
        return _normalize_status(explicit)
    return _derive_overall(gates)


def _remaining_risk(report: Any) -> str:
    value = _get(report, "remaining_risk", "")
    text = str(value).strip() if value else ""
    return text or "None stated."


def _default_next_action(overall: str) -> str:
    if overall == STATUS_FAIL:
        return "Block on fail; resolve failing gates before proceeding."
    if overall == STATUS_OWNER_APPROVAL:
        return "Awaiting owner approval."
    if overall == STATUS_PASS:
        return "Proceed."
    return "No action — all gates skipped."


def _next_action(report: Any, overall: str) -> str:
    value = _get(report, "next_action", "")
    text = str(value).strip() if value else ""
    return text or _default_next_action(overall)


def _title(report: Any) -> str:
    value = _get(report, "title", "")
    text = str(value).strip() if value else ""
    return text or "JARVIS Gate Summary"


def _timestamp(report: Any) -> str:
    value = _get(report, "timestamp", "")
    return str(value).strip() if value else ""


def _truncate(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` chars, suffixing an ellipsis if cut.

    Newlines are flattened to single spaces so output stays single-line
    for mobile consumers.
    """
    if not isinstance(text, str):
        return ""
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    if limit <= 3:
        return flat[:limit]
    return flat[: limit - 3] + "..."


# ── Public renderers ──────────────────────────────────────────────────

def markdown_report(report: Any) -> str:
    """Render a full markdown gate report.

    Output is deterministic: same input yields byte-identical output.
    Always emits all 8 canonical gates (missing → SKIPPED). Sections
    rendered: header, optional timestamp, gate table, Result,
    Remaining risk, Next action.
    """
    gates = _collect_gates(report)
    overall = _overall_result(report, gates)
    title = _title(report)
    ts = _timestamp(report)
    risk = _remaining_risk(report)
    next_act = _next_action(report, overall)

    name_w = max(len("Gate"), max(len(g["name"]) for g in gates))
    status_w = max(len("Status"), max(len(STATUS_DISPLAY.get(g["status"], g["status"])) for g in gates))

    def _row(name: str, status: str, detail: str) -> str:
        return f"| {name:<{name_w}} | {status:<{status_w}} | {detail} |"

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    if ts:
        lines.append(f"_Generated: {ts}_")
        lines.append("")
    lines.append("## Gate Summary")
    lines.append("")
    lines.append(_row("Gate", "Status", "Detail"))
    lines.append(f"| {'-' * name_w} | {'-' * status_w} | {'-' * 7} |")
    for gate in gates:
        status_display = STATUS_DISPLAY.get(gate["status"], gate["status"].upper())
        detail_parts: list[str] = []
        if gate["message"]:
            detail_parts.append(gate["message"])
        if gate["owner"]:
            detail_parts.append(f"owner: {gate['owner']}")
        if gate["evidence"]:
            detail_parts.append(f"evidence: {gate['evidence']}")
        detail = "; ".join(detail_parts)
        lines.append(_row(gate["name"], status_display, detail))
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append(STATUS_DISPLAY.get(overall, overall.upper()))
    lines.append("")
    lines.append("## Remaining risk")
    lines.append("")
    lines.append(risk)
    lines.append("")
    lines.append("## Next action")
    lines.append("")
    lines.append(next_act)
    lines.append("")
    return "\n".join(lines)


def mobile_report(report: Any) -> str:
    """Render a compact short report (Slack/SMS-sized, ASCII only).

    Output is bounded (target ≤400 chars) so it fits in a mobile preview.
    Always includes the overall verdict, per-status counts, the first
    fail or owner-approval gate (when present), and truncated
    ``Risk:`` and ``Next:`` lines.
    """
    gates = _collect_gates(report)
    overall = _overall_result(report, gates)
    counts = _counts(gates)
    risk = _remaining_risk(report)
    next_act = _next_action(report, overall)

    verdict = STATUS_DISPLAY.get(overall, overall.upper())
    summary_line = (
        f"JARVIS: {verdict}  "
        f"pass={counts[STATUS_PASS]} "
        f"fail={counts[STATUS_FAIL]} "
        f"owner={counts[STATUS_OWNER_APPROVAL]} "
        f"skip={counts[STATUS_SKIPPED]}"
    )

    callout = ""
    first_fail = next((g for g in gates if g["status"] == STATUS_FAIL), None)
    first_owner = next(
        (g for g in gates if g["status"] == STATUS_OWNER_APPROVAL), None
    )
    highlight = first_fail or first_owner
    if highlight is not None:
        label = "First fail" if first_fail else "Owner needed"
        message = highlight["message"] or "(no detail)"
        callout = _truncate(
            f"{label}: {highlight['name']} - {message}", 120
        )

    lines = [summary_line]
    if callout:
        lines.append(callout)
    lines.append("Risk: " + _truncate(risk, 80))
    lines.append("Next: " + _truncate(next_act, 80))
    return "\n".join(lines)


def as_dict(report: Any) -> dict[str, Any]:
    """Return a JSON-safe dict representation of the report.

    Every value is ``str``, ``int``, ``list``, or ``dict``. The output
    is guaranteed to round-trip through ``json.dumps`` /
    ``json.loads``.
    """
    gates = _collect_gates(report)
    overall = _overall_result(report, gates)
    risk = _remaining_risk(report)
    next_act = _next_action(report, overall)

    gates_payload: list[dict[str, str]] = []
    for gate in gates:
        gates_payload.append({
            "name": gate["name"],
            "status": gate["status"],
            "message": gate["message"],
            "owner": gate["owner"],
            "evidence": gate["evidence"],
        })

    return {
        "title": _title(report),
        "timestamp": _timestamp(report),
        "gates": gates_payload,
        "counts": _counts(gates),
        "result": overall,
        "remaining_risk": risk,
        "next_action": next_act,
    }


def failure_summary(report: Any) -> str:
    """Render a compact summary of failed gates only.

    When no gates failed, returns a single-line "no failures" header.
    Always includes ``Remaining risk:`` and ``Next action:`` lines.
    """
    gates = _collect_gates(report)
    overall = _overall_result(report, gates)
    risk = _remaining_risk(report)
    next_act = _next_action(report, overall)
    failures = [g for g in gates if g["status"] == STATUS_FAIL]

    lines: list[str] = []
    if not failures:
        lines.append("No failed gates.")
    else:
        lines.append(f"Failed gates ({len(failures)}):")
        for gate in failures:
            detail = gate["message"] or "(no detail)"
            lines.append(f"  - {gate['name']}: {detail}")
    lines.append("")
    lines.append(f"Remaining risk: {risk}")
    lines.append(f"Next action: {next_act}")
    return "\n".join(lines)


def owner_approval_summary(report: Any) -> str:
    """Render a compact summary of owner-approval gates only.

    When no gates need owner approval, returns a "none pending" header.
    Always includes ``Remaining risk:`` and ``Next action:`` lines.
    """
    gates = _collect_gates(report)
    overall = _overall_result(report, gates)
    risk = _remaining_risk(report)
    next_act = _next_action(report, overall)
    pending = [g for g in gates if g["status"] == STATUS_OWNER_APPROVAL]

    lines: list[str] = []
    if not pending:
        lines.append("No owner-approval gates pending.")
    else:
        lines.append(f"Owner approval needed ({len(pending)}):")
        for gate in pending:
            owner = f" ({gate['owner']})" if gate["owner"] else ""
            detail = gate["message"] or "(no detail)"
            lines.append(f"  - {gate['name']}{owner}: {detail}")
    lines.append("")
    lines.append(f"Remaining risk: {risk}")
    lines.append(f"Next action: {next_act}")
    return "\n".join(lines)


__all__ = (
    "markdown_report",
    "mobile_report",
    "as_dict",
    "failure_summary",
    "owner_approval_summary",
    "GATE_ORDER",
    "GATE_DISPLAY_NAMES",
    "STATUS_PASS",
    "STATUS_FAIL",
    "STATUS_OWNER_APPROVAL",
    "STATUS_SKIPPED",
    "VALID_STATUSES",
    "GateResultLike",
    "ReportLike",
    "GateResultDict",
    "ReportDict",
)
