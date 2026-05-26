"""AOS Council decision schema for JARVIS Prime.

Structured types capturing the output of an AOS Council deliberation:
mission brief, each seat's perspective, specialist findings, contrarian
objections, the synthesized verdict, and the final handoff bundle that
JARVIS Prime emits to Slack, Termux, and the web cockpit.

Design goals:

- **Stdlib only.** No LLM call, no third-party imports, no I/O. Importable
  in any environment where the rest of Hermes failed to load.
- **Serialize-only.** Each public type exposes ``to_dict()`` and
  ``to_markdown()``. There is intentionally no ``from_dict()`` — the
  schema is for emission, not parsing.
- **Frozen.** Decisions are records; mutating one in place is almost
  always a bug. Build new instances instead.
- **Forward-compatible.** Role names are open strings so the 233-agent
  registry under ``skills/aos-enterprise-council/`` plus future
  specialists fit without a schema bump. ``FinalRecommendation`` carries
  ``schema_version = "aos.v1"`` so the gateway/mobile consumer can
  negotiate versions later.

Layering: ``CouncilQuestion`` is the input; ``CouncilPerspective``,
``SpecialistFinding``, and ``ContrarianObjection`` are the contributions
each seat makes; ``CouncilDecision`` is the synthesized verdict; and
``FinalRecommendation`` is the top-level handoff that bundles everything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


# =============================================================================
# DecisionStatus
#
# Subclassing ``str`` is deliberate: ``json.dumps([DecisionStatus.APPROVED])``
# emits ``'["approved"]'`` directly, no custom encoder. Enum construction
# also validates value automatically — ``DecisionStatus("nonsense")`` raises
# ``ValueError`` on its own.
# =============================================================================


class DecisionStatus(str, Enum):
    """Terminal verdict on a council question."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_OWNER = "needs_owner"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


# =============================================================================
# Leaf types
# =============================================================================


@dataclass(frozen=True)
class CouncilQuestion:
    """The mission brief routed into the council.

    Attributes:
        brief: 1-3 sentence statement of what is being decided.
        context: supporting evidence pointers / facts / links, one per
            tuple entry. Rendered as a bullet list in markdown.
        requested_by: owner-of-record string (default ``"jeremiah"``).
        mode: JARVIS Prime mode this question was raised in. Open string
            mirroring ``docs/jarvis-prime-operating-system.md`` (companion,
            strategy, critic, operator, builder, mobile_voice).
        tags: routing tags such as ``"architecture"`` or ``"hazmat"``.
    """

    brief: str
    context: tuple[str, ...] = ()
    requested_by: str = "jeremiah"
    mode: str = "operator"
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "brief": self.brief,
            "context": list(self.context),
            "requested_by": self.requested_by,
            "mode": self.mode,
            "tags": list(self.tags),
        }

    def to_markdown(self) -> str:
        lines = [
            "### Question",
            f"**Brief:** {self.brief}",
            (
                f"**Requested by:** {self.requested_by}   "
                f"**Mode:** {self.mode}   "
                f"**Tags:** {', '.join(self.tags) if self.tags else '(none)'}"
            ),
        ]
        if self.context:
            lines.append("")
            lines.append("Context:")
            lines.extend(f"- {item}" for item in self.context)
        return "\n".join(lines)


@dataclass(frozen=True)
class CouncilPerspective:
    """One council role's read on the question.

    A perspective is the opinion of a named seat at the table
    (``principal-systems-architect``, ``assurance-risk-director`` etc.).
    It carries a numeric score that feeds the decision scorecard.

    Attributes:
        role: open-string role name. Mirrors filenames under
            ``.claude/agents/`` so cross-references are grep-safe, but
            not validated — the 233-agent registry plus future seats
            must fit.
        summary: 1-3 sentence headline.
        rationale: bullet-grade reasoning lines.
        score: 1-5 integer; 1 = block, 5 = ship. Feeds the scorecard.
        confidence: 1-5 integer; 1 = low, 5 = high.
        concerns: specific worries this seat raised.
        supports: specific claims this seat endorsed.

    Raises:
        ValueError: if ``score`` or ``confidence`` is outside 1-5.
    """

    role: str
    summary: str
    rationale: tuple[str, ...] = ()
    score: int = 3
    confidence: int = 3
    concerns: tuple[str, ...] = ()
    supports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.score <= 5:
            raise ValueError(
                f"score must be between 1 and 5, got {self.score!r}"
            )
        if not 1 <= self.confidence <= 5:
            raise ValueError(
                f"confidence must be between 1 and 5, got {self.confidence!r}"
            )

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "summary": self.summary,
            "rationale": list(self.rationale),
            "score": self.score,
            "confidence": self.confidence,
            "concerns": list(self.concerns),
            "supports": list(self.supports),
        }

    def to_markdown(self) -> str:
        lines = [
            f"### Perspective: {self.role}",
            f"**Score:** {self.score}/5   **Confidence:** {self.confidence}/5",
            "",
            self.summary,
        ]
        if self.supports:
            lines += ["", "Supports:", *(f"- {item}" for item in self.supports)]
        if self.concerns:
            lines += ["", "Concerns:", *(f"- {item}" for item in self.concerns)]
        if self.rationale:
            lines += [
                "",
                "Rationale:",
                *(f"- {item}" for item in self.rationale),
            ]
        return "\n".join(lines)


@dataclass(frozen=True)
class SpecialistFinding:
    """A domain specialist's contribution.

    Specialists (HazMat, Nourish, Logistics, security-supply-chain, etc.)
    are activated only when the task touches their domain. Findings sit
    alongside perspectives at the ``FinalRecommendation`` level — a
    single finding can inform multiple seats.

    Attributes:
        specialist: open-string specialist name.
        domain: short domain label (``"49 CFR"``, ``"nutrition"``, etc.).
        finding: 1-3 sentence summary.
        evidence: supporting citations / file refs / measurements.
        confidence: 1-5 integer.
        blocking: if True, ``FinalRecommendation`` cannot be APPROVED
            without addressing this finding. Encoded as a bool rather
            than yet another enum.

    Raises:
        ValueError: if ``confidence`` is outside 1-5.
    """

    specialist: str
    domain: str
    finding: str
    evidence: tuple[str, ...] = ()
    confidence: int = 3
    blocking: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.confidence <= 5:
            raise ValueError(
                f"confidence must be between 1 and 5, got {self.confidence!r}"
            )

    def to_dict(self) -> dict:
        return {
            "specialist": self.specialist,
            "domain": self.domain,
            "finding": self.finding,
            "evidence": list(self.evidence),
            "confidence": self.confidence,
            "blocking": self.blocking,
        }

    def to_markdown(self) -> str:
        blocking_label = "yes" if self.blocking else "no"
        lines = [
            f"### Specialist: {self.specialist} — {self.domain}",
            (
                f"**Confidence:** {self.confidence}/5   "
                f"**Blocking:** {blocking_label}"
            ),
            "",
            self.finding,
        ]
        if self.evidence:
            lines += ["", "Evidence:", *(f"- {item}" for item in self.evidence)]
        return "\n".join(lines)


@dataclass(frozen=True)
class ContrarianObjection:
    """Red-team / "I disagree" output.

    The ``contrarian-reviewer`` seat produces these to challenge the
    emerging consensus. ``severity`` is an open string mirroring
    ``security_advisories.Advisory.severity`` precedent — the door is
    left open for ``"fatal"``, ``"operational"``, or domain-specific
    labels.

    Attributes:
        objection: 1-3 sentence statement of the dissent.
        severity: ``"low"`` / ``"medium"`` / ``"high"`` / ``"critical"``
            (or any other label a council uses).
        rebuttal: the synthesizer's response; empty if the objection is
            unaddressed.
        addressed: True when the council has resolved this objection.
        raised_by: which seat raised it (usually ``contrarian-reviewer``).
    """

    objection: str
    severity: str = "medium"
    rebuttal: str = ""
    addressed: bool = False
    raised_by: str = "contrarian-reviewer"

    def to_dict(self) -> dict:
        return {
            "objection": self.objection,
            "severity": self.severity,
            "rebuttal": self.rebuttal,
            "addressed": self.addressed,
            "raised_by": self.raised_by,
        }

    def to_markdown(self) -> str:
        status_label = "addressed" if self.addressed else "open"
        lines = [
            (
                f"### Objection (severity: {self.severity}, "
                f"raised by {self.raised_by})"
            ),
            self.objection,
            "",
            f"**Status:** {status_label}",
        ]
        if self.rebuttal:
            lines.append(f"**Rebuttal:** {self.rebuttal}")
        return "\n".join(lines)


# =============================================================================
# Verdict
# =============================================================================


@dataclass(frozen=True)
class CouncilDecision:
    """The synthesized verdict: status + reasoning + scorecard summary.

    This is the council's *answer* to the question. It is not the
    top-level handoff — that is ``FinalRecommendation``, which wraps
    one ``CouncilDecision`` together with the question, perspectives,
    specialists, and contrarians that produced it.

    Attributes:
        status: terminal verdict.
        headline: 1-line executive verdict statement.
        rationale: bullet reasoning for the verdict.
        scorecard: ordered ``((role, score), ...)`` mirroring the
            perspective order. Tuple-of-tuples rather than dict so the
            order is locked and JSON-stable.
        owner_questions: questions for the owner; rendered only when
            ``status == NEEDS_OWNER``.
        evidence_gaps: missing evidence; rendered only when
            ``status == NEEDS_MORE_EVIDENCE``.
    """

    status: DecisionStatus
    headline: str
    rationale: tuple[str, ...] = ()
    scorecard: tuple[tuple[str, int], ...] = ()
    owner_questions: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "headline": self.headline,
            "rationale": list(self.rationale),
            "scorecard": [
                {"role": role, "score": score} for role, score in self.scorecard
            ],
            "owner_questions": list(self.owner_questions),
            "evidence_gaps": list(self.evidence_gaps),
        }

    def to_markdown(self) -> str:
        lines = [
            "### Decision",
            f"**Status:** {self.status.value}",
            f"**Verdict:** {self.headline}",
        ]
        if self.rationale:
            lines += [
                "",
                "Rationale:",
                *(f"- {item}" for item in self.rationale),
            ]
        if self.scorecard:
            lines += ["", _scorecard_table(self.scorecard)]
        if self.status is DecisionStatus.NEEDS_OWNER and self.owner_questions:
            lines += [
                "",
                "Owner questions:",
                *(f"- {item}" for item in self.owner_questions),
            ]
        if (
            self.status is DecisionStatus.NEEDS_MORE_EVIDENCE
            and self.evidence_gaps
        ):
            lines += [
                "",
                "Evidence gaps:",
                *(f"- {item}" for item in self.evidence_gaps),
            ]
        return "\n".join(lines)


# =============================================================================
# Top-level handoff
# =============================================================================


@dataclass(frozen=True)
class FinalRecommendation:
    """Top-level bundle handed off to the gateway / mobile consumer.

    This is what JARVIS Prime emits to Slack, Termux, and the web
    cockpit when the AOS Council finishes deliberating. Markdown
    rendering follows ``CLAUDE.md``'s Output Standard heading order:
    Executive verdict → Evidence reviewed → Agent perspectives →
    Decision scorecard → Recommended plan → Blockers and risks →
    Execution checklist → Validation commands → Rollback notes →
    Open questions.

    Attributes:
        question: the council question being answered.
        decision: the synthesized verdict.
        perspectives: each seat's read.
        specialist_findings: domain specialist contributions (HazMat,
            Nourish, etc.).
        contrarian_objections: red-team output.
        recommended_plan: ordered step list for the "Recommended plan"
            section.
        blockers: the "Blockers and risks" content.
        execution_checklist: the "Execution checklist" content
            (rendered as ``- [ ]`` checkboxes).
        validation_commands: the "Validation commands" content
            (rendered inside a fenced code block).
        rollback_notes: the "Rollback notes" content.
        open_questions: rendered as the "Open questions" section only
            when non-empty.
        schema_version: future-proofs the gateway/mobile consumer.
            Override if you need to emit a pre-release schema.
        generated_at: opaque string (caller supplies ISO-8601 if it
            wants); kept as a string so the module stays timezone-
            agnostic and JSON-clean.

    Note: inputs are not escaped in ``to_markdown()`` — this module
    assumes council-authored, internal content. If a perspective's
    summary contains a literal ``|`` it will visually break a scorecard
    cell, but that is a copy/paste hazard, not a security issue.
    """

    question: CouncilQuestion
    decision: CouncilDecision
    perspectives: tuple[CouncilPerspective, ...] = ()
    specialist_findings: tuple[SpecialistFinding, ...] = ()
    contrarian_objections: tuple[ContrarianObjection, ...] = ()
    recommended_plan: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    execution_checklist: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()
    rollback_notes: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    schema_version: str = "aos.v1"
    generated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "question": self.question.to_dict(),
            "decision": self.decision.to_dict(),
            "perspectives": [p.to_dict() for p in self.perspectives],
            "specialist_findings": [
                f.to_dict() for f in self.specialist_findings
            ],
            "contrarian_objections": [
                o.to_dict() for o in self.contrarian_objections
            ],
            "recommended_plan": list(self.recommended_plan),
            "blockers": list(self.blockers),
            "execution_checklist": list(self.execution_checklist),
            "validation_commands": list(self.validation_commands),
            "rollback_notes": list(self.rollback_notes),
            "open_questions": list(self.open_questions),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        parts: list[str] = []
        parts.append("# Final Recommendation")
        parts.append(
            f"*schema: {self.schema_version} — generated: {self.generated_at}*"
        )
        parts.append(f"*Question: {self.question.brief}*")

        parts.append("")
        parts.append("## Executive verdict")
        parts.append(
            f"{self.decision.headline}  "
            f"(status: {self.decision.status.value})"
        )

        if (
            self.decision.status is DecisionStatus.NEEDS_OWNER
            and self.decision.owner_questions
        ):
            parts.append("")
            parts.append("Owner questions:")
            parts.extend(f"- {item}" for item in self.decision.owner_questions)

        if (
            self.decision.status is DecisionStatus.NEEDS_MORE_EVIDENCE
            and self.decision.evidence_gaps
        ):
            parts.append("")
            parts.append("Evidence gaps:")
            parts.extend(f"- {item}" for item in self.decision.evidence_gaps)

        if self.question.context:
            parts.append("")
            parts.append("## Evidence reviewed")
            parts.extend(f"- {item}" for item in self.question.context)

        if self.perspectives:
            parts.append("")
            parts.append("## Agent perspectives")
            for p in self.perspectives:
                parts.append("")
                parts.append(p.to_markdown())

        if self.specialist_findings:
            parts.append("")
            parts.append("#### Specialist findings")
            for f in self.specialist_findings:
                parts.append("")
                parts.append(f.to_markdown())

        if self.contrarian_objections:
            parts.append("")
            parts.append("#### Contrarian objections")
            for o in self.contrarian_objections:
                parts.append("")
                parts.append(o.to_markdown())

        if self.decision.scorecard:
            parts.append("")
            parts.append("## Decision scorecard")
            parts.append(_scorecard_table(self.decision.scorecard))

        if self.recommended_plan:
            parts.append("")
            parts.append("## Recommended plan")
            parts.extend(
                f"{i}. {step}"
                for i, step in enumerate(self.recommended_plan, start=1)
            )

        if self.blockers:
            parts.append("")
            parts.append("## Blockers and risks")
            parts.extend(f"- {item}" for item in self.blockers)

        if self.execution_checklist:
            parts.append("")
            parts.append("## Execution checklist")
            parts.extend(f"- [ ] {item}" for item in self.execution_checklist)

        if self.validation_commands:
            parts.append("")
            parts.append("## Validation commands")
            parts.append("```")
            parts.extend(self.validation_commands)
            parts.append("```")

        if self.rollback_notes:
            parts.append("")
            parts.append("## Rollback notes")
            parts.extend(f"- {item}" for item in self.rollback_notes)

        if self.open_questions:
            parts.append("")
            parts.append("## Open questions")
            parts.extend(f"- {item}" for item in self.open_questions)

        return "\n".join(parts)


# =============================================================================
# Private markdown helpers
# =============================================================================


def _scorecard_table(rows: Iterable[tuple[str, int]]) -> str:
    """Render an ordered ``(role, score)`` sequence as a markdown table."""
    lines = ["| Role | Score |", "| --- | --- |"]
    lines.extend(f"| {role} | {score}/5 |" for role, score in rows)
    return "\n".join(lines)
