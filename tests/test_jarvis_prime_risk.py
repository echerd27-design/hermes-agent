"""Tests for the JARVIS Prime risk classifier (W02).

These tests pin the deterministic behavior promised in
``hermes_cli/jarvis_prime/risk.py`` and the owner-gate alignment promised
in ``docs/aci/reports/W02_RISK_CLASS_MODEL.md``.
"""

from __future__ import annotations

import pytest

from hermes_cli.jarvis_prime import (
    RiskAssessment,
    RiskClass,
    RiskSignal,
    SIGNALS,
    classify,
    is_owner_gated,
    max_class_for,
    owner_gates_for,
)


class TestRiskClassEnum:
    """RiskClass must be a totally-ordered IntEnum so callers can compare."""

    def test_ordering(self):
        assert RiskClass.RC0 < RiskClass.RC1 < RiskClass.RC2 < RiskClass.RC3 < RiskClass.RC4

    def test_int_values(self):
        assert (int(RiskClass.RC0), int(RiskClass.RC1), int(RiskClass.RC2),
                int(RiskClass.RC3), int(RiskClass.RC4)) == (0, 1, 2, 3, 4)

    def test_max_works(self):
        assert max(RiskClass.RC0, RiskClass.RC3, RiskClass.RC2) is RiskClass.RC3


class TestRepresentativeInputs:
    """One representative input per tier — the canonical promise of W02."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("What does RC3 mean?", RiskClass.RC0),
            ("hello there", RiskClass.RC0),
            ("/plan the next feature", RiskClass.RC1),
            ("draft a release note", RiskClass.RC1),
            ("refactor the helper", RiskClass.RC2),
            ("fix bug in tests", RiskClass.RC2),
            ("git push origin foo", RiskClass.RC3),
            ("pip install requests", RiskClass.RC3),
            ("deploy to vercel", RiskClass.RC4),
            ("merge to main", RiskClass.RC4),
        ],
    )
    def test_each_tier(self, text, expected):
        assert classify(text).risk_class is expected


class TestCommonAciHermesCommands:
    """Strings the JARVIS routing layer will routinely classify."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("/builder", RiskClass.RC1),
            ("/audit", RiskClass.RC1),
            ("/operator", RiskClass.RC1),
            ("/strategy", RiskClass.RC1),
            ("/critic", RiskClass.RC1),
            ("/council", RiskClass.RC1),
            ("edit hermes_cli/foo.py", RiskClass.RC2),
            ("refactor the verification gate", RiskClass.RC2),
            ("git commit -am 'fix typo'", RiskClass.RC3),
            ("git push origin feature/foo", RiskClass.RC3),
            # --force escalates this to RC4 even though it also matches git push.
            ("git push origin main --force", RiskClass.RC4),
            ("open a pull request", RiskClass.RC3),
            ("npm install lodash", RiskClass.RC3),
            ("curl https://api.example.com/v1/healthz", RiskClass.RC3),
            ("npm publish", RiskClass.RC4),
            ("deploy to production", RiskClass.RC4),
            ("merge to main and tag a release", RiskClass.RC4),
        ],
    )
    def test_known_command(self, text, expected):
        assert classify(text).risk_class is expected


class TestOwnerGateAlignment:
    """Each owner-gated phrase named in
    docs/jarvis-prime-operating-system.md (Owner Gates section, ~lines
    293–306) and docs/jarvis-verification-gates.md (Owner Approval Gate
    section) must classify as RC4 and surface a gate label.
    """

    OWNER_GATED_INPUTS: tuple[str, ...] = (
        "spend money on this experiment",
        "purchase a new domain",
        "billing change",
        "post publicly on the company blog",
        "create a third-party account at acme.io",
        "rotate secret for the prod key",
        "rotate credentials for the deploy bot",
        "change oauth client id",
        "deploy to production",
        "production deploy of v2",
        "update dns for the docs subdomain",
        "change dns of the marketing site",
        "domain transfer to namecheap",
        "merge to main",
        "merge into main and tag",
        "git push --force-with-lease origin main",
        "force push the rebase",
        "npm publish the new version",
        "twine upload to pypi",
        "submit build to the app store",
        "submit build to play store",
        "send the testflight invite",
    )

    @pytest.mark.parametrize("text", OWNER_GATED_INPUTS)
    def test_owner_gated_phrase_is_rc4(self, text):
        result = classify(text)
        assert result.risk_class is RiskClass.RC4, (
            f"{text!r} should be RC4 but got {result.risk_class!r}; "
            f"matched={result.matched_signals}"
        )

    @pytest.mark.parametrize("text", OWNER_GATED_INPUTS)
    def test_owner_gated_phrase_fires_gate(self, text):
        assert is_owner_gated(text) is True
        assert owner_gates_for(text), f"no gate label for {text!r}"

    def test_regulated_claim_is_rc4_but_not_owner_gated(self):
        """Regulated/compliance claims are RC4 by severity but are NOT the
        same as the deploy/merge/money owner approval flow.
        """
        result = classify("ship a health claim about the supplement")
        assert result.risk_class is RiskClass.RC4
        assert result.owner_gates == ()
        assert is_owner_gated("ship a health claim about the supplement") is False


class TestEdgeCases:
    """Empty input, None, whitespace, case, and code-block wrappers."""

    @pytest.mark.parametrize("text", ["", "   ", "\t\n", None])
    def test_empty_or_none_is_rc0(self, text):
        result = classify(text)
        assert result.risk_class is RiskClass.RC0
        assert result.matched_signals == ()
        assert result.owner_gates == ()
        assert result.rationale == "RC0: no risk signals matched."

    @pytest.mark.parametrize(
        "text",
        ["DEPLOY to prod", "Deploy To Prod", "  deploy  ", "DePlOy"],
    )
    def test_case_insensitive(self, text):
        assert classify(text).risk_class is RiskClass.RC4

    def test_code_block_wrapper_is_not_stripped(self):
        """A risky command inside fenced ``` blocks still classifies — the
        classifier is intent-aware, not safety-aware."""
        wrapped = "Run this:\n```\ngit push --force origin main\n```"
        assert classify(wrapped).risk_class is RiskClass.RC4

    def test_word_boundary_protects_unrelated_words(self):
        """``deploy`` is whole-word, so ``redeploys-historical-record`` does
        NOT fire on it.
        """
        # 'redeploys' contains 'deploy' as a substring but not as a whole
        # word. The "redeploys" token should not trigger.
        result = classify("the system redeploys are historical")
        # 'redeploys' won't match \bdeploy\b. Should be RC0.
        assert result.risk_class is RiskClass.RC0

    def test_negation_is_not_handled(self):
        """Documented limitation: ``don't deploy`` still classifies RC4.
        RC4 means "needs owner review", not "will execute"."""
        assert classify("don't deploy yet").risk_class is RiskClass.RC4

    def test_multi_match_takes_highest(self):
        """``git push`` is RC3, ``deploy`` is RC4 — combined input picks RC4."""
        result = classify("git push and then deploy")
        assert result.risk_class is RiskClass.RC4
        # Both signals should appear in matched_signals.
        assert "deploy" in result.matched_signals
        assert "git push" in result.matched_signals


class TestDeterminism:
    """Same input → byte-identical assessment, every time."""

    def test_repeated_calls_match(self):
        text = "git push and then deploy to vercel prod"
        first = classify(text)
        second = classify(text)
        third = classify(text)
        assert first == second == third
        # matched_signals must be tuples (immutable, comparable).
        assert isinstance(first.matched_signals, tuple)
        assert isinstance(first.owner_gates, tuple)

    def test_matched_signals_follow_table_order(self):
        """``matched_signals`` should list labels in the order they appear in
        SIGNALS, with RC4 owner-gated phrases ahead of RC3 ones."""
        result = classify("git push origin main && deploy to prod")
        # 'deploy' (RC4) comes before 'git push' (RC3) in SIGNALS, so it
        # should come first in matched_signals.
        deploy_idx = result.matched_signals.index("deploy")
        push_idx = result.matched_signals.index("git push")
        assert deploy_idx < push_idx


class TestMaxClassFor:
    """``max_class_for`` lets pre-categorized callers skip the regex pass."""

    def test_returns_highest(self):
        assert max_class_for("deploy", "git commit") is RiskClass.RC4
        assert max_class_for("git push", "edit code") is RiskClass.RC3
        assert max_class_for("edit code") is RiskClass.RC2
        assert max_class_for("planning command") is RiskClass.RC1

    def test_no_args_is_rc0(self):
        assert max_class_for() is RiskClass.RC0

    def test_unknown_labels_are_ignored(self):
        assert max_class_for("not-a-real-label") is RiskClass.RC0
        # Unknown labels alongside known ones do not pollute the result.
        assert max_class_for("not-a-real-label", "git push") is RiskClass.RC3

    def test_owner_gate_label_resolves_to_rc4(self):
        assert max_class_for("merge to main") is RiskClass.RC4
        assert max_class_for("force push") is RiskClass.RC4


class TestSignalsTable:
    """Invariants about the SIGNALS table that future contributors should
    not break without an explicit decision.
    """

    def test_table_is_non_empty_and_immutable(self):
        assert isinstance(SIGNALS, tuple)
        assert len(SIGNALS) > 0

    def test_every_signal_has_a_label(self):
        for sig in SIGNALS:
            assert sig.label, f"signal {sig.pattern!r} has empty label"

    def test_owner_gates_only_apply_to_rc4(self):
        for sig in SIGNALS:
            if sig.owner_gate:
                assert sig.risk_class is RiskClass.RC4, (
                    f"signal {sig.pattern!r} is owner-gated but classified "
                    f"as {sig.risk_class!r}"
                )

    def test_signal_dataclass_is_frozen(self):
        sig = SIGNALS[0]
        with pytest.raises((AttributeError, Exception)):
            sig.label = "tampered"  # type: ignore[misc]


class TestRationaleText:
    """Rationale strings are part of the public contract — JARVIS routing
    will surface them to the operator response slot at
    docs/jarvis-prime-operating-system.md:193.
    """

    def test_rc0_rationale(self):
        assert classify("").rationale == "RC0: no risk signals matched."

    def test_rc4_rationale_mentions_gates(self):
        rationale = classify("deploy to prod").rationale
        assert "RC4" in rationale
        assert "owner gates" in rationale

    def test_rc3_rationale_does_not_mention_gates(self):
        rationale = classify("git push origin foo").rationale
        assert "RC3" in rationale
        assert "owner gates" not in rationale
