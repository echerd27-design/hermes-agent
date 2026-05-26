"""Tests for hermes_cli.jarvis_prime.specialists — deterministic activation matrix."""

from __future__ import annotations

import re

import pytest

from hermes_cli.jarvis_prime import SPECIALISTS, Specialist, activate_specialists


# Helper: convenient access to the set of returned IDs for an input.
def _ids(text, **kwargs):
    return tuple(s.id for s in activate_specialists(text, **kwargs))


# Canonical ID list, ordered. Mirrors SPECIALISTS for ordering assertions.
EXPECTED_ORDER = (
    "hazmat-command-specialist",
    "nourish-product-specialist",
    "logistics-domain-specialist",
    "security-compliance-reviewer",
    "product-ux-reviewer",
    "qa-release-gate",
    "memory-evidence-curator",
    "career-strategy-specialist",
    "contrarian-reviewer",
)


class TestRegistry:
    """Static invariants on the SPECIALISTS tuple."""

    def test_count_is_nine(self):
        assert len(SPECIALISTS) == 9

    def test_ids_match_canonical_order(self):
        assert tuple(s.id for s in SPECIALISTS) == EXPECTED_ORDER

    def test_ids_are_unique(self):
        ids = [s.id for s in SPECIALISTS]
        assert len(ids) == len(set(ids))

    def test_ids_are_kebab_case(self):
        pattern = re.compile(r"^[a-z]+(?:-[a-z]+)+$")
        for s in SPECIALISTS:
            assert pattern.match(s.id), f"non-kebab id: {s.id!r}"

    def test_specialists_are_frozen(self):
        s = SPECIALISTS[0]
        with pytest.raises(Exception):
            s.id = "mutated"  # type: ignore[misc]

    def test_every_specialist_has_triggers(self):
        for s in SPECIALISTS:
            assert isinstance(s, Specialist)
            assert len(s.triggers) > 0, f"{s.id} has no triggers"

    def test_triggers_are_lowercase_strings(self):
        for s in SPECIALISTS:
            for trigger in s.triggers:
                assert isinstance(trigger, str)
                assert trigger == trigger.lower(), (
                    f"trigger not lowercase: {s.id} -> {trigger!r}"
                )
                assert trigger.strip() == trigger, (
                    f"trigger has surrounding whitespace: {s.id} -> {trigger!r}"
                )


class TestHazMatActivation:
    """HazMat Command Specialist activates on regulated-hazmat triggers."""

    @pytest.mark.parametrize(
        "text",
        [
            "placarding the trailer",
            "49 CFR check needed",
            "shipping papers ready",
            "ERG lookup",
            "HazMat command center request",
            "dangerous goods handling",
            "ocr provenance audit ledger",
        ],
    )
    def test_activates(self, text):
        assert "hazmat-command-specialist" in _ids(text)


class TestNourishActivation:
    """Nourish Product Specialist activates on nutrition/wellness triggers."""

    @pytest.mark.parametrize(
        "text",
        [
            "recipe library",
            "meal logging UX",
            "nutrient math",
            "health claim review",
            "Nourish onboarding flow",
            "behavior change loop",
            "food privacy policy",
        ],
    )
    def test_activates(self, text):
        # "onboarding" intentionally co-activates Product UX — only assert
        # that Nourish itself is present.
        assert "nourish-product-specialist" in _ids(text)


class TestLogisticsActivation:
    """Logistics Domain Specialist activates on Hey Jay / fleet / dispatch triggers."""

    @pytest.mark.parametrize(
        "text",
        [
            "Hey Jay, dispatch a driver",
            "LTL workflow design",
            "carrier integration",
            "fleet terminal map",
            "logistics question",
            "trucking software roadmap",
        ],
    )
    def test_activates(self, text):
        assert "logistics-domain-specialist" in _ids(text)


class TestSecurityActivation:
    """Security / Compliance Reviewer activates on secrets, compliance, authz triggers."""

    @pytest.mark.parametrize(
        "text",
        [
            "oauth secret rotation",
            "security review needed",
            "compliance posture audit",  # 'compliance' alone, not 'compliance claim'
            "CVE patch incoming",
            "trust boundary documentation",
            "authn flow change",
        ],
    )
    def test_activates(self, text):
        assert "security-compliance-reviewer" in _ids(text)


class TestReleaseActivation:
    """QA Release Gate activates on release readiness / launch / deploy triggers."""

    @pytest.mark.parametrize(
        "text",
        [
            "release readiness check",
            "go/no-go decision",
            "launch checklist",
            "production deploy plan",
            "pre-release sign-off",
            "qa gate before ship",
        ],
    )
    def test_activates(self, text):
        assert "qa-release-gate" in _ids(text)


class TestCareerActivation:
    """Career Strategy Specialist activates on resume / interview / promotion triggers."""

    @pytest.mark.parametrize(
        "text",
        [
            "resume update",
            "interview prep",
            "promotion case for staff engineer",
            "career positioning",
            "hiring negotiation",
            "leveling rubric",
        ],
    )
    def test_activates(self, text):
        assert "career-strategy-specialist" in _ids(text)


class TestContrarianUxEvidence:
    """Brief coverage for the remaining three specialists."""

    def test_contrarian_activates(self):
        assert "contrarian-reviewer" in _ids("red-team the plan")

    def test_contrarian_phrase(self):
        assert "contrarian-reviewer" in _ids("blind spot in this proposal")

    def test_product_ux_activates(self):
        # 'friction' is UX-only; 'onboarding' would also fit but is exercised
        # in TestNourishActivation. Pick a UX-only phrase here.
        result = _ids("friction in the demo flow")
        assert "product-ux-reviewer" in result

    def test_memory_evidence_activates(self):
        assert "memory-evidence-curator" in _ids("audit the evidence trail")

    def test_memory_evidence_durable_memory(self):
        assert "memory-evidence-curator" in _ids("save this to durable memory")


class TestDeterminismAndBounds:
    """Empty input, no over-activation, ordering, idempotence, force/exclude."""

    @pytest.mark.parametrize("text", ["", "   ", "\t\n", "    \t  "])
    def test_empty_or_whitespace_returns_nothing(self, text):
        assert activate_specialists(text) == ()

    @pytest.mark.parametrize(
        "text",
        [
            "good morning, hope you're well",
            "what is the weather today",
            "thanks, talk later",
            "let me think about that",
        ],
    )
    def test_conversational_text_does_not_activate(self, text):
        assert activate_specialists(text) == ()

    def test_multi_domain_text_preserves_canonical_order(self):
        text = "HazMat shipping papers and release readiness review"
        result = _ids(text)
        assert result == ("hazmat-command-specialist", "qa-release-gate")

    def test_order_is_canonical_regardless_of_input_order(self):
        # Mention QA-release first in the text; canonical order still wins.
        text = "release readiness, then circle back on hazmat placarding"
        result = _ids(text)
        assert result.index("hazmat-command-specialist") < result.index("qa-release-gate")

    def test_repeated_calls_are_idempotent(self):
        text = "release readiness for the nourish meal logging launch"
        first = activate_specialists(text)
        for _ in range(9):
            assert activate_specialists(text) == first

    def test_case_insensitive(self):
        upper = _ids("HAZMAT PLACARDING")
        lower = _ids("hazmat placarding")
        mixed = _ids("HazMat PlaCarDing")
        assert upper == lower == mixed
        assert "hazmat-command-specialist" in upper

    def test_force_adds_specialist_even_when_text_is_empty(self):
        result = _ids("", context={"force": ["contrarian-reviewer"]})
        assert result == ("contrarian-reviewer",)

    def test_force_with_multiple_ids_keeps_canonical_order(self):
        result = _ids(
            "",
            context={"force": ["contrarian-reviewer", "hazmat-command-specialist"]},
        )
        assert result == ("hazmat-command-specialist", "contrarian-reviewer")

    def test_exclude_drops_a_matched_specialist(self):
        text = "hazmat placarding review"
        baseline = _ids(text)
        assert "hazmat-command-specialist" in baseline
        filtered = _ids(text, context={"exclude": ["hazmat-command-specialist"]})
        assert "hazmat-command-specialist" not in filtered

    def test_exclude_overrides_force(self):
        # Spec: exclusion wins when an ID appears in both lists. Loop skips
        # excluded IDs before the force check.
        result = _ids(
            "release readiness review",
            context={
                "force": ["qa-release-gate"],
                "exclude": ["qa-release-gate"],
            },
        )
        assert "qa-release-gate" not in result

    def test_unknown_force_ids_are_ignored(self):
        result = _ids("", context={"force": ["does-not-exist", "also-fake"]})
        assert result == ()

    def test_unknown_exclude_ids_are_ignored(self):
        result = _ids("hazmat placarding", context={"exclude": ["nope"]})
        assert "hazmat-command-specialist" in result

    def test_no_duplicates(self):
        # 'release' and 'release readiness' both target the same specialist.
        text = "release release readiness release gate ship launch"
        result = _ids(text)
        assert result.count("qa-release-gate") == 1

    def test_non_string_input_is_handled(self):
        assert activate_specialists(None) == ()  # type: ignore[arg-type]


class TestSmallestUsefulSet:
    """Activation must stay minimal: only return specialists whose triggers actually fire."""

    def test_unrelated_prompt_returns_empty(self):
        assert activate_specialists("what's the weather?") == ()

    @pytest.mark.parametrize(
        "text,expected_id",
        [
            ("dispatch the next driver", "logistics-domain-specialist"),
            ("CVE patch tonight", "security-compliance-reviewer"),
            ("update my resume", "career-strategy-specialist"),
            ("red-team this proposal", "contrarian-reviewer"),
            ("nutrient math review", "nourish-product-specialist"),
            ("placarding update", "hazmat-command-specialist"),
        ],
    )
    def test_single_domain_returns_exactly_one(self, text, expected_id):
        result = _ids(text)
        assert result == (expected_id,), (
            f"expected exactly ({expected_id!r},), got {result!r}"
        )

    def test_word_boundary_prevents_substring_false_positive(self):
        # 'ship' is a QA-release trigger, but 'shipping' should NOT fire it
        # on its own — and a HazMat phrase 'shipping paper' should still hit
        # HazMat without dragging QA-release in.
        result = _ids("shipping container update")
        assert result == ()

    def test_cv_does_not_fire_inside_cve(self):
        # 'cv' is a Career trigger; 'cve' is a Security trigger. They must
        # not collide.
        result = _ids("CVE patch")
        assert "career-strategy-specialist" not in result
        assert "security-compliance-reviewer" in result

    def test_full_bench_only_when_every_domain_named(self):
        # Construct one prompt that mentions every required trigger family.
        text = (
            "hazmat placarding, nutrition recipe, logistics dispatch, "
            "security oauth, ux onboarding, release readiness, "
            "evidence audit, career promotion, red-team contrarian"
        )
        result = _ids(text)
        assert result == EXPECTED_ORDER

    def test_two_unrelated_domains_returns_exactly_two(self):
        text = "nutrient math meets resume coaching"
        result = _ids(text)
        assert result == (
            "nourish-product-specialist",
            "career-strategy-specialist",
        )
