"""Tests for hermes_cli.jarvis_prime.aos.

The AOS schema module is the data layer beneath every future "render an
AOS Council decision" surface (slash commands, Slack handoff cards, PR
comment templates, memory store entries). These tests exercise the
public API in isolation: no LLM call, no I/O, no real council pass.

Coverage is split between per-type unit classes (one ``TestX`` per
dataclass) and an end-to-end class that builds four realistic
``FinalRecommendation`` payloads — architecture, security, strategy,
release — and asserts the full ``to_dict`` + ``to_markdown`` contract.
"""

from __future__ import annotations

import json

import pytest

import hermes_cli.jarvis_prime.aos as aos
from hermes_cli.jarvis_prime import (  # noqa: F401  — verifies re-exports resolve
    ContrarianObjection,
    CouncilDecision,
    CouncilPerspective,
    CouncilQuestion,
    DecisionStatus,
    FinalRecommendation,
    SpecialistFinding,
)


# ---------------------------------------------------------------------------
# DecisionStatus
# ---------------------------------------------------------------------------


class TestDecisionStatus:
    def test_values_are_lowercase_strings(self):
        assert aos.DecisionStatus.APPROVED.value == "approved"
        assert aos.DecisionStatus.REJECTED.value == "rejected"
        assert aos.DecisionStatus.NEEDS_OWNER.value == "needs_owner"
        assert (
            aos.DecisionStatus.NEEDS_MORE_EVIDENCE.value
            == "needs_more_evidence"
        )

    def test_is_json_serializable_directly(self):
        # Subclassing str means json.dumps emits the bare token, no encoder.
        assert json.dumps([aos.DecisionStatus.APPROVED]) == '["approved"]'

    def test_construction_rejects_unknown_value(self):
        with pytest.raises(ValueError):
            aos.DecisionStatus("nonsense")


# ---------------------------------------------------------------------------
# CouncilQuestion
# ---------------------------------------------------------------------------


class TestCouncilQuestion:
    def test_to_dict_roundtrips_through_json(self):
        q = aos.CouncilQuestion(
            brief="Should we split the gateway monolith?",
            context=("gateway.py is 225 KB", "Windows path diverges"),
            tags=("architecture", "gateway"),
        )
        data = q.to_dict()
        json.dumps(data)  # must not raise
        assert data["brief"] == "Should we split the gateway monolith?"
        assert data["context"] == [
            "gateway.py is 225 KB",
            "Windows path diverges",
        ]
        assert data["tags"] == ["architecture", "gateway"]
        assert data["requested_by"] == "jeremiah"
        assert data["mode"] == "operator"

    def test_to_markdown_contains_brief_and_context(self):
        q = aos.CouncilQuestion(
            brief="Rotate Mistral keys?",
            context=("shai-hulud advisory", "mistralai 2.4.6 installed"),
        )
        md = q.to_markdown()
        assert "**Brief:** Rotate Mistral keys?" in md
        assert "- shai-hulud advisory" in md
        assert "- mistralai 2.4.6 installed" in md

    def test_empty_context_omits_section(self):
        q = aos.CouncilQuestion(brief="x")
        md = q.to_markdown()
        assert "Context:" not in md
        # Tags line still renders with "(none)" placeholder.
        assert "**Tags:** (none)" in md


# ---------------------------------------------------------------------------
# CouncilPerspective
# ---------------------------------------------------------------------------


class TestCouncilPerspective:
    @pytest.mark.parametrize("bad_score", [0, 6, -1])
    def test_score_out_of_range_raises(self, bad_score):
        with pytest.raises(ValueError):
            aos.CouncilPerspective(
                role="principal-systems-architect",
                summary="x",
                score=bad_score,
            )

    @pytest.mark.parametrize("bad_confidence", [0, 6, -1])
    def test_confidence_out_of_range_raises(self, bad_confidence):
        with pytest.raises(ValueError):
            aos.CouncilPerspective(
                role="principal-systems-architect",
                summary="x",
                confidence=bad_confidence,
            )

    def test_to_markdown_renders_n_of_5(self):
        p = aos.CouncilPerspective(
            role="principal-systems-architect",
            summary="Two-layer split is right",
            score=4,
            confidence=5,
        )
        md = p.to_markdown()
        assert "**Score:** 4/5" in md
        assert "**Confidence:** 5/5" in md
        assert "Two-layer split is right" in md

    def test_to_dict_preserves_concerns_and_supports(self):
        p = aos.CouncilPerspective(
            role="contrarian-reviewer",
            summary="Risk dominates",
            concerns=("regression risk", "cycle time"),
            supports=("clean boundary",),
        )
        data = p.to_dict()
        assert data["concerns"] == ["regression risk", "cycle time"]
        assert data["supports"] == ["clean boundary"]

    def test_dataclass_is_frozen(self):
        p = aos.CouncilPerspective(role="r", summary="s")
        with pytest.raises(Exception):
            # setattr routes the mutation dynamically so the type checker
            # cannot statically flag the attempt; the runtime still raises
            # because @dataclass(frozen=True) blocks all attribute writes.
            setattr(p, "score", 5)


# ---------------------------------------------------------------------------
# SpecialistFinding
# ---------------------------------------------------------------------------


class TestSpecialistFinding:
    def test_blocking_flag_renders_in_markdown(self):
        finding = aos.SpecialistFinding(
            specialist="security-supply-chain",
            domain="pypi",
            finding="mistralai 2.4.6 was installed",
            blocking=True,
        )
        md = finding.to_markdown()
        assert "**Blocking:** yes" in md

        non_blocking = aos.SpecialistFinding(
            specialist="qa-release-gate",
            domain="release",
            finding="all tests green",
            blocking=False,
        )
        assert "**Blocking:** no" in non_blocking.to_markdown()

    def test_to_dict_preserves_evidence_order(self):
        finding = aos.SpecialistFinding(
            specialist="hazmat-command",
            domain="49 CFR",
            finding="placard required",
            evidence=("cite 49 CFR 172.504", "cargo manifest line 4"),
        )
        data = finding.to_dict()
        assert data["evidence"] == [
            "cite 49 CFR 172.504",
            "cargo manifest line 4",
        ]
        assert data["blocking"] is False

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError):
            aos.SpecialistFinding(
                specialist="x",
                domain="y",
                finding="z",
                confidence=99,
            )


# ---------------------------------------------------------------------------
# ContrarianObjection
# ---------------------------------------------------------------------------


class TestContrarianObjection:
    def test_addressed_open_renders_distinctly(self):
        open_obj = aos.ContrarianObjection(objection="too broad")
        md_open = open_obj.to_markdown()
        assert "**Status:** open" in md_open

        addressed_obj = aos.ContrarianObjection(
            objection="too broad",
            addressed=True,
            rebuttal="narrowed to wave 07",
        )
        md_addressed = addressed_obj.to_markdown()
        assert "**Status:** addressed" in md_addressed
        assert "**Rebuttal:** narrowed to wave 07" in md_addressed

    def test_rebuttal_omitted_when_empty(self):
        obj = aos.ContrarianObjection(
            objection="market too small",
            severity="medium",
        )
        md = obj.to_markdown()
        assert "**Rebuttal:**" not in md

    def test_severity_is_open_string(self):
        # No enum — any string label is allowed.
        obj = aos.ContrarianObjection(objection="x", severity="operational")
        assert obj.to_dict()["severity"] == "operational"


# ---------------------------------------------------------------------------
# CouncilDecision
# ---------------------------------------------------------------------------


class TestCouncilDecision:
    def test_status_serializes_as_string(self):
        d = aos.CouncilDecision(
            status=aos.DecisionStatus.APPROVED,
            headline="ship it",
        )
        data = d.to_dict()
        assert data["status"] == "approved"
        json.dumps(data)  # confirms str-enum survives json round-trip

    def test_scorecard_markdown_is_table(self):
        d = aos.CouncilDecision(
            status=aos.DecisionStatus.APPROVED,
            headline="ship",
            scorecard=(("principal-systems-architect", 4), ("contrarian-reviewer", 2)),
        )
        md = d.to_markdown()
        assert "| Role | Score |" in md
        assert "| principal-systems-architect | 4/5 |" in md
        assert "| contrarian-reviewer | 2/5 |" in md

    def test_owner_questions_render_only_for_needs_owner(self):
        owner_decision = aos.CouncilDecision(
            status=aos.DecisionStatus.NEEDS_OWNER,
            headline="owner must approve tagline",
            owner_questions=("ship the new tagline?",),
        )
        assert "Owner questions:" in owner_decision.to_markdown()

        # Same field on an APPROVED decision is silently dropped from md.
        approved_with_owner_q = aos.CouncilDecision(
            status=aos.DecisionStatus.APPROVED,
            headline="ship",
            owner_questions=("phantom",),
        )
        assert "Owner questions:" not in approved_with_owner_q.to_markdown()

    def test_evidence_gaps_render_only_for_needs_more_evidence(self):
        gaps_decision = aos.CouncilDecision(
            status=aos.DecisionStatus.NEEDS_MORE_EVIDENCE,
            headline="need baseline",
            evidence_gaps=("coverage map",),
        )
        assert "Evidence gaps:" in gaps_decision.to_markdown()

        rejected_with_gaps = aos.CouncilDecision(
            status=aos.DecisionStatus.REJECTED,
            headline="no",
            evidence_gaps=("phantom",),
        )
        assert "Evidence gaps:" not in rejected_with_gaps.to_markdown()


# ---------------------------------------------------------------------------
# FinalRecommendation
# ---------------------------------------------------------------------------


def _minimal_recommendation(
    status: aos.DecisionStatus = aos.DecisionStatus.APPROVED,
) -> aos.FinalRecommendation:
    """Build a bare-bones FinalRecommendation for shape tests."""
    return aos.FinalRecommendation(
        question=aos.CouncilQuestion(brief="anything"),
        decision=aos.CouncilDecision(status=status, headline="x"),
    )


class TestFinalRecommendation:
    def test_schema_version_defaults_to_aos_v1(self):
        rec = _minimal_recommendation()
        assert rec.schema_version == "aos.v1"
        assert rec.to_dict()["schema_version"] == "aos.v1"

    def test_schema_version_is_overridable(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(brief="x"),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.APPROVED,
                headline="y",
            ),
            schema_version="aos.v2-preview",
        )
        assert rec.to_dict()["schema_version"] == "aos.v2-preview"

    def test_to_dict_is_json_dumpable(self):
        rec = _minimal_recommendation()
        json.dumps(rec.to_dict())  # must not raise

    def test_to_json_emits_indented_string(self):
        rec = _minimal_recommendation()
        s = rec.to_json()
        assert s.startswith("{")
        assert "\n  " in s  # 2-space indent

    def test_tuples_become_lists_in_to_dict(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(brief="x"),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.APPROVED,
                headline="y",
            ),
            recommended_plan=("step 1", "step 2"),
        )
        data = rec.to_dict()
        assert isinstance(rec.recommended_plan, tuple)
        assert isinstance(data["recommended_plan"], list)
        assert data["recommended_plan"] == ["step 1", "step 2"]

    def test_empty_optional_sections_are_omitted(self):
        rec = _minimal_recommendation()
        md = rec.to_markdown()
        # The only mandatory section beyond the header is "Executive verdict".
        assert "## Executive verdict" in md
        for heading in (
            "## Evidence reviewed",
            "## Agent perspectives",
            "## Decision scorecard",
            "## Recommended plan",
            "## Blockers and risks",
            "## Execution checklist",
            "## Validation commands",
            "## Rollback notes",
            "## Open questions",
            "#### Specialist findings",
            "#### Contrarian objections",
        ):
            assert heading not in md, f"unexpected heading rendered: {heading}"

    def test_open_questions_section_omitted_when_empty(self):
        rec = _minimal_recommendation()
        assert "## Open questions" not in rec.to_markdown()

    def test_open_questions_section_rendered_when_populated(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(brief="x"),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.NEEDS_OWNER,
                headline="y",
            ),
            open_questions=("did we ask the owner?",),
        )
        md = rec.to_markdown()
        assert "## Open questions" in md
        assert "- did we ask the owner?" in md


# ---------------------------------------------------------------------------
# End-to-end fixtures — architecture, security, strategy, release
# ---------------------------------------------------------------------------


_CANONICAL_ORDER = (
    "## Executive verdict",
    "## Evidence reviewed",
    "## Agent perspectives",
    "## Decision scorecard",
    "## Recommended plan",
    "## Blockers and risks",
    "## Execution checklist",
    "## Validation commands",
    "## Rollback notes",
)


def _assert_canonical_heading_order(md: str) -> None:
    """Assert canonical headings that ARE rendered appear in order.

    Headings backed by empty tuples are omitted by ``to_markdown()`` per the
    empty-section policy; this helper only verifies the relative order of
    the headings that did get rendered.
    """
    assert "## Executive verdict" in md, "Executive verdict is always rendered"
    present = [h for h in _CANONICAL_ORDER if h in md]
    positions = [md.index(h) for h in present]
    assert positions == sorted(positions), (
        f"headings out of order; present={present}, positions={positions}"
    )


class TestEndToEnd:
    def test_architecture_decision(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(
                brief=(
                    "Split the 225 KB hermes_cli/gateway.py monolith into a "
                    "transport layer and a session layer so transports can "
                    "swap without touching session logic."
                ),
                context=(
                    "gateway.py is 225 KB across one file",
                    "gateway_windows.py has diverged",
                    "mobile transport is the next consumer",
                ),
                mode="builder",
                tags=("architecture", "gateway", "refactor"),
            ),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.NEEDS_MORE_EVIDENCE,
                headline=(
                    "Two-layer split is the right shape; need a regression "
                    "baseline before committing."
                ),
                rationale=(
                    "transport / session is a clean boundary",
                    "no current coverage map to anchor a safe refactor",
                ),
                scorecard=(
                    ("principal-systems-architect", 4),
                    ("delivery-scope-controller", 3),
                    ("contrarian-reviewer", 2),
                ),
                evidence_gaps=(
                    "gateway.py test coverage map",
                    "Windows transport divergence inventory",
                ),
            ),
            perspectives=(
                aos.CouncilPerspective(
                    role="principal-systems-architect",
                    summary="Two-layer split is the right shape",
                    score=4,
                    confidence=4,
                    supports=("clean transport/session boundary",),
                ),
                aos.CouncilPerspective(
                    role="delivery-scope-controller",
                    summary="Scope is large; sequence carefully",
                    score=3,
                    confidence=4,
                    concerns=("cycle time during refactor",),
                ),
                aos.CouncilPerspective(
                    role="contrarian-reviewer",
                    summary="Regression risk > benefit unless tests land first",
                    score=2,
                    confidence=3,
                    concerns=("no baseline regression suite",),
                ),
            ),
            contrarian_objections=(
                aos.ContrarianObjection(
                    objection=(
                        "Refactor cost dwarfs current pain point; ship a "
                        "thin transport adapter instead."
                    ),
                    severity="high",
                    addressed=False,
                ),
            ),
            recommended_plan=(
                "Land a gateway.py test baseline with measured coverage.",
                "Define the transport / session interface as a thin shim.",
                "Migrate one transport behind the shim and verify parity.",
            ),
            blockers=("no coverage baseline exists today",),
            rollback_notes=(
                "Revert the shim commits; no public surface area changed.",
            ),
        )
        data = rec.to_dict()
        json.dumps(data)
        assert data["schema_version"] == "aos.v1"
        assert data["decision"]["status"] == "needs_more_evidence"
        # every perspective role survives serialization
        roles_in_dict = {p["role"] for p in data["perspectives"]}
        assert roles_in_dict == {
            "principal-systems-architect",
            "delivery-scope-controller",
            "contrarian-reviewer",
        }
        md = rec.to_markdown()
        _assert_canonical_heading_order(md)
        assert "needs_more_evidence" in md
        # evidence_gaps must render under the decision when status matches
        assert "gateway.py test coverage map" in md
        # contrarian text appears
        assert "Refactor cost dwarfs current pain point" in md

    def test_security_decision(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(
                brief=(
                    "Apply the Mini Shai-Hulud remediation: uninstall "
                    "mistralai 2.4.6, rotate every API key touched by "
                    "Hermes, ack shai-hulud-2026-05, confirm no exfil."
                ),
                context=(
                    "advisory: shai-hulud-2026-05 in hermes_cli/security_advisories.py",
                    "mistralai 2.4.6 was installed for 6 hours",
                    "no outbound webhook traffic observed",
                ),
                mode="operator",
                tags=("security", "supply-chain", "rotation"),
            ),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.APPROVED,
                headline=(
                    "Rotate keys, uninstall the package, then ack the advisory."
                ),
                rationale=(
                    "exposure window confirmed by the cache fingerprint",
                    "rotation is cheap relative to credential loss",
                ),
                scorecard=(
                    ("assurance-risk-director", 5),
                    ("evidence-architect", 5),
                    ("contrarian-reviewer", 5),
                ),
            ),
            perspectives=(
                aos.CouncilPerspective(
                    role="assurance-risk-director",
                    summary="Rotate immediately; ack only after the audit.",
                    score=5,
                    confidence=5,
                    supports=("standard supply-chain payload steals credentials",),
                ),
                aos.CouncilPerspective(
                    role="evidence-architect",
                    summary="Cache file confirms exposure window.",
                    score=5,
                    confidence=4,
                    supports=("~/.hermes/cache/advisory_banner_seen evidence",),
                ),
                aos.CouncilPerspective(
                    role="contrarian-reviewer",
                    summary="No counter — uncontroversial remediation.",
                    score=5,
                    confidence=3,
                ),
            ),
            specialist_findings=(
                aos.SpecialistFinding(
                    specialist="security-supply-chain",
                    domain="pypi",
                    finding=(
                        "mistralai 2.4.6 was installed on this host for "
                        "6 hours; credential exfil is the standard payload; "
                        "rotation is mandatory."
                    ),
                    evidence=(
                        "Socket advisory URL",
                        "importlib.metadata.version('mistralai') == '2.4.6'",
                    ),
                    confidence=5,
                    blocking=True,
                ),
            ),
            contrarian_objections=(
                aos.ContrarianObjection(
                    objection="Rotation churn could break the gateway start.",
                    severity="low",
                    addressed=True,
                    rebuttal=(
                        "Audit confirmed no outbound webhook traffic; "
                        "rotation will not race a live worm."
                    ),
                ),
            ),
            recommended_plan=(
                "pip uninstall -y mistralai",
                "Rotate API keys in ~/.hermes/.env (Anthropic, OpenAI, "
                "OpenRouter, Mistral, Nous, GitHub, AWS, Google).",
                "Audit ~/.npmrc, ~/.pypirc, ~/.aws/credentials.",
                "hermes doctor --ack shai-hulud-2026-05",
            ),
            validation_commands=(
                "hermes doctor",
                "pip show mistralai || echo 'uninstalled'",
            ),
            rollback_notes=(
                "Re-installing mistralai is NOT a rollback; the rollback is "
                "to keep the rotated keys.",
            ),
        )
        data = rec.to_dict()
        json.dumps(data)
        assert data["decision"]["status"] == "approved"
        assert any(
            "security-supply-chain" == f["specialist"]
            for f in data["specialist_findings"]
        )
        md = rec.to_markdown()
        _assert_canonical_heading_order(md)
        assert "shai-hulud" in md
        # blocking specialist finding shows blocking=yes
        assert "**Blocking:** yes" in md
        # the validation block stays inside a fenced code block
        assert "```" in md
        assert "pip uninstall -y mistralai" in md

    def test_strategy_decision(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(
                brief=(
                    "Lock the public positioning: Hermes is a local-first AI "
                    "cockpit. Differentiate vs. GitHub Copilot / Cursor / "
                    "Cody on owner-controlled provider routing, on-device "
                    "memory, and the AOS Council deliberation layer."
                ),
                context=(
                    "current README tagline emphasizes terminal chat",
                    "recent investor thread asks about moat",
                    "competitor messaging is crowded around 'AI pair programmer'",
                ),
                mode="strategy",
                tags=("strategy", "positioning", "marketing"),
            ),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.NEEDS_OWNER,
                headline=(
                    "Positioning is sound; owner must approve the messaging "
                    "shift before the website and README change."
                ),
                rationale=(
                    "local-first is a real moat",
                    "onboarding does not demonstrate the moat in 60s",
                ),
                scorecard=(
                    ("commercial-strategist", 4),
                    ("product-experience-architect", 3),
                    ("contrarian-reviewer", 2),
                ),
                owner_questions=(
                    "Do we ship the new tagline this wave?",
                    "Do we keep the GitHub-Copilot comparison visible or soften it?",
                ),
            ),
            perspectives=(
                aos.CouncilPerspective(
                    role="commercial-strategist",
                    summary="Local-first is a real moat; lean into it.",
                    score=4,
                    confidence=4,
                    supports=("owner-controlled routing is unique today",),
                ),
                aos.CouncilPerspective(
                    role="product-experience-architect",
                    summary="Positioning is correct but onboarding lags.",
                    score=3,
                    confidence=3,
                    concerns=("60s demo does not show the moat",),
                ),
                aos.CouncilPerspective(
                    role="contrarian-reviewer",
                    summary=(
                        "Local-first audience is small; cloud bridge needed "
                        "to grow."
                    ),
                    score=2,
                    confidence=4,
                    concerns=("market size",),
                ),
            ),
            contrarian_objections=(
                aos.ContrarianObjection(
                    objection="Local-first market is too small to ride.",
                    severity="medium",
                    addressed=False,
                ),
                aos.ContrarianObjection(
                    objection="Messaging landscape is crowded; you blur in.",
                    severity="low",
                    addressed=True,
                    rebuttal=(
                        "The moat language differentiates from generic "
                        "pair-programmer pitch."
                    ),
                ),
            ),
            recommended_plan=(
                "Draft the new tagline and the comparison section.",
                "Ship to owner for approval.",
                "Update README + website only after owner approval.",
            ),
            open_questions=(
                "Do we ship the new tagline this wave?",
                "Do we soften the GitHub-Copilot comparison?",
            ),
        )
        data = rec.to_dict()
        json.dumps(data)
        assert data["decision"]["status"] == "needs_owner"
        assert data["decision"]["owner_questions"]  # populated
        md = rec.to_markdown()
        _assert_canonical_heading_order(md)
        # NEEDS_OWNER → owner_questions surface in the decision section
        assert "Owner questions:" in md
        # Open questions section is rendered separately when populated
        assert "## Open questions" in md
        assert "ship the new tagline" in md.lower()

    def test_release_decision(self):
        rec = aos.FinalRecommendation(
            question=aos.CouncilQuestion(
                brief=(
                    "Cut hermes-cli 0.15 with the JARVIS Prime + AOS Council "
                    "schema additions. Gate the release on a one-click "
                    "rollback path because the new schema module is consumed "
                    "by gateway and mobile."
                ),
                context=(
                    "previous release: RELEASE_v0.14.0.md",
                    "wave 07 schema module landed",
                    "no mobile consumer wired yet",
                ),
                mode="builder",
                tags=("release", "versioning", "rollback"),
            ),
            decision=aos.CouncilDecision(
                status=aos.DecisionStatus.APPROVED,
                headline="Cut 0.15 with the verified rollback pin.",
                rationale=(
                    "scope is tight",
                    "rollback is a one-line pip install",
                    "codex review came back clean",
                ),
                scorecard=(
                    ("delivery-scope-controller", 4),
                    ("assurance-risk-director", 4),
                    ("codex-dispatch-governor", 5),
                ),
            ),
            perspectives=(
                aos.CouncilPerspective(
                    role="delivery-scope-controller",
                    summary="Scope is tight; cut it Tuesday.",
                    score=4,
                    confidence=5,
                ),
                aos.CouncilPerspective(
                    role="assurance-risk-director",
                    summary="Rollback is verified.",
                    score=4,
                    confidence=4,
                    supports=("pip install hermes-cli==0.14.0 rolls back cleanly",),
                ),
                aos.CouncilPerspective(
                    role="codex-dispatch-governor",
                    summary="Codex review came back clean on the schema.",
                    score=5,
                    confidence=4,
                ),
            ),
            specialist_findings=(
                aos.SpecialistFinding(
                    specialist="qa-release-gate",
                    domain="release",
                    finding=(
                        "All targeted tests green on Linux + Termux; "
                        "Windows transport untested but unchanged in this wave."
                    ),
                    blocking=False,
                ),
            ),
            contrarian_objections=(
                aos.ContrarianObjection(
                    objection=(
                        "Mobile consumer is not wired; release ships "
                        "dead schema code."
                    ),
                    severity="medium",
                    addressed=True,
                    rebuttal=(
                        "Schema is forward-compat (aos.v1); mobile lights "
                        "it up in wave 08."
                    ),
                ),
            ),
            recommended_plan=(
                "Bump hermes_cli/__init__.py version to 0.15.0.",
                "Tag the release commit.",
                "Publish to PyPI via the existing release workflow.",
            ),
            execution_checklist=(
                "Bump version",
                "Run scripts/run_tests.sh",
                "Tag v0.15.0",
                "Publish to PyPI",
            ),
            validation_commands=(
                "scripts/run_tests.sh",
                "python -c 'import hermes_cli; print(hermes_cli.__version__)'",
            ),
            rollback_notes=(
                "pip install hermes-cli==0.14.0",
                "Then: hermes doctor",
            ),
        )
        data = rec.to_dict()
        json.dumps(data)
        assert data["decision"]["status"] == "approved"
        md = rec.to_markdown()
        _assert_canonical_heading_order(md)
        # verbatim rollback pin
        assert "pip install hermes-cli==0.14.0" in md
        # execution checklist rendered as checkboxes
        assert "- [ ] Bump version" in md
        # validation commands inside a fenced code block
        assert "scripts/run_tests.sh" in md
