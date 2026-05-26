"""Regression tests for ``hermes_cli.jarvis_prime.gates``.

Every gate has at least one passing and one failing scenario. Eight
realistic ACI build packets (clean docs-only, code+tests, dependency
change, secret added, publish attempt, missing rollback, concurrent
editors, no-tests-with-reason) are exercised end-to-end through
``run_all_gates`` and ``overall_status``.
"""

from __future__ import annotations

import dataclasses

import pytest

from hermes_cli.jarvis_prime.gates import (
    ALL_GATES,
    GateResult,
    OWNER_APPROVAL_PHRASE,
    Packet,
    build_gate,
    overall_status,
    owner_approval_gate,
    planning_gate,
    release_gate,
    review_gate,
    rollback_gate,
    run_all_gates,
    security_gate,
)
# Aliased because pytest auto-collects any top-level ``test_*`` symbol in
# a ``test_*.py`` file as a test function.
from hermes_cli.jarvis_prime.gates import test_gate as run_test_gate


# ── helpers ──────────────────────────────────────────────────────────────────


def _base_packet(**overrides) -> Packet:
    """A happy-path packet that passes every gate.

    Models a clean docs-only PR with full planning, review, test, release,
    and rollback metadata. Tests construct each scenario by passing only
    the deltas as keyword overrides. Construction goes through ``Packet``
    directly (rather than ``Packet(**dict)``) so each field's annotated
    type is visible to the type checker.
    """

    base = Packet(
        repo="echerd27-design/hermes-agent",
        branch="aci/wave-09-gate-regression-tests",
        working_tree="clean",
        mission="Harden JARVIS verification gates",
        goal="Add gate runtime and regression tests",
        allowed_files=[
            "hermes_cli/jarvis_prime/gates.py",
            "tests/test_jarvis_prime_gates.py",
            "docs/aci/reports/W09_GATE_REGRESSION_TESTS.md",
        ],
        disallowed_files=["pyproject.toml", "uv.lock", "README.md"],
        protected_files=[".env", "uv.lock"],
        protected_edit_approved=False,
        non_goals=["wiring gates into orchestration"],
        acceptance_criteria=[
            "Every gate has pass and fail tests",
            "Owner approval gate requires exact phrase",
        ],
        owner_gates_identified=True,
        changed_files=["docs/aci/reports/W09_GATE_REGRESSION_TESTS.md"],
        concurrent_editors=["claude"],
        docs_only_stage=True,
        diff_text="+ harmless docs line\n",
        review_findings=[
            {"severity": "low", "kind": "improvement", "note": "wording"},
        ],
        contrarian_objection="docs may drift if not re-verified each wave",
        tests_run=True,
        tests_passed=True,
        test_skip_reason="",
        unverified_risk_named=False,
        git_diff_check_passed=True,
        is_dependency_change=False,
        dependency_review_separate=False,
        credential_files_edited=[],
        credential_edits_approved=False,
        network_calls_added=False,
        is_publish_or_deploy=False,
        pr_summary="Wave 09 hardens JARVIS gates with regression tests",
        pr_body_ready=True,
        commits_scoped=True,
        verification_summary="pytest + compileall green",
        remaining_risks=["wheel does not yet ship jarvis_prime subpackage"],
        owner_approval="",
        rollback_plan="git revert the wave commits or delete the three new files",
        commit_hash_or_file_list="HEAD",
        risky_runtime_change=False,
        revert_strategy="",
    )
    if not overrides:
        return base
    return dataclasses.replace(base, **overrides)


# ── per-gate pass + fail coverage ───────────────────────────────────────────


class TestPlanningGate:
    def test_pass_on_complete_packet(self):
        assert planning_gate(_base_packet()).passed

    def test_fail_when_owner_gates_not_identified(self):
        result = planning_gate(_base_packet(owner_gates_identified=False))
        assert result.status == "fail"
        assert any("owner gates" in r for r in result.reasons)

    @pytest.mark.parametrize(
        "field,empty_value,needle",
        [
            ("repo", "", "missing repo"),
            ("branch", "", "missing branch"),
            ("goal", "", "missing goal"),
            ("allowed_files", [], "allowed_files is empty"),
            ("acceptance_criteria", [], "acceptance_criteria is empty"),
        ],
    )
    def test_each_required_field_missing_fails(self, field, empty_value, needle):
        result = planning_gate(_base_packet(**{field: empty_value}))
        assert result.status == "fail"
        assert any(needle in r for r in result.reasons)


class TestBuildGate:
    def test_pass_on_in_scope_diff(self):
        result = build_gate(_base_packet())
        assert result.passed, result.reasons

    def test_fail_when_changed_file_outside_allowed(self):
        result = build_gate(
            _base_packet(changed_files=["pyproject.toml"], docs_only_stage=False)
        )
        assert result.status == "fail"
        assert any("outside allowed list" in r for r in result.reasons)

    def test_fail_on_secret_in_diff(self):
        result = build_gate(_base_packet(diff_text="+ OPENAI_API_KEY=sk-leak\n"))
        assert result.status == "fail"
        assert any("secret" in r.lower() for r in result.reasons)

    def test_fail_when_protected_file_edited_without_approval(self):
        result = build_gate(
            _base_packet(
                allowed_files=["uv.lock"],
                changed_files=["uv.lock"],
                protected_files=["uv.lock"],
                protected_edit_approved=False,
                docs_only_stage=False,
            )
        )
        assert result.status == "fail"
        assert any("protected files" in r for r in result.reasons)

    def test_pass_when_protected_file_edit_is_approved(self):
        result = build_gate(
            _base_packet(
                allowed_files=["uv.lock"],
                changed_files=["uv.lock"],
                protected_files=["uv.lock"],
                protected_edit_approved=True,
                docs_only_stage=False,
            )
        )
        assert result.passed, result.reasons

    def test_fail_on_runtime_change_in_docs_only_stage(self):
        result = build_gate(
            _base_packet(
                allowed_files=["hermes_cli/foo.py"],
                changed_files=["hermes_cli/foo.py"],
                docs_only_stage=True,
            )
        )
        assert result.status == "fail"
        assert any("docs-only stage" in r for r in result.reasons)


class TestReviewGate:
    def test_pass_on_no_diff(self):
        result = review_gate(_base_packet(changed_files=[], review_findings=[]))
        assert result.passed

    def test_pass_on_findings_with_severity_and_contrarian(self):
        result = review_gate(_base_packet())
        assert result.passed, result.reasons

    def test_fail_when_findings_missing_severity(self):
        result = review_gate(
            _base_packet(review_findings=[{"kind": "blocking", "note": "x"}])
        )
        assert result.status == "fail"
        assert any("severity" in r for r in result.reasons)

    def test_fail_when_no_findings_for_non_empty_diff(self):
        result = review_gate(
            _base_packet(
                changed_files=["docs/x.md"],
                review_findings=[],
                contrarian_objection="anything",
            )
        )
        assert result.status == "fail"
        assert any("no review findings" in r for r in result.reasons)

    def test_fail_when_contrarian_objection_missing(self):
        result = review_gate(_base_packet(contrarian_objection=""))
        assert result.status == "fail"
        assert any("contrarian" in r for r in result.reasons)


class TestTestGate:
    def test_pass_when_tests_run_and_passed(self):
        assert run_test_gate(_base_packet()).passed

    def test_fail_when_tests_run_but_did_not_pass(self):
        result = run_test_gate(_base_packet(tests_passed=False))
        assert result.status == "fail"
        assert any("did not pass" in r for r in result.reasons)

    def test_fail_when_not_run_and_no_skip_reason(self):
        result = run_test_gate(_base_packet(tests_run=False, test_skip_reason=""))
        assert result.status == "fail"
        assert any("no skip reason" in r for r in result.reasons)

    def test_pass_when_skipped_with_reason_and_named_risk(self):
        result = run_test_gate(
            _base_packet(
                tests_run=False,
                test_skip_reason="docs-only diff, no executable code paths",
                unverified_risk_named=True,
            )
        )
        assert result.passed, result.reasons

    def test_fail_when_skipped_with_reason_but_no_named_risk(self):
        result = run_test_gate(
            _base_packet(
                tests_run=False,
                test_skip_reason="quick fix",
                unverified_risk_named=False,
            )
        )
        assert result.status == "fail"
        assert any("unverified risk" in r for r in result.reasons)

    def test_fail_when_git_diff_check_fails(self):
        result = run_test_gate(_base_packet(git_diff_check_passed=False))
        assert result.status == "fail"
        assert any("git diff --check" in r for r in result.reasons)


class TestSecurityGate:
    def test_pass_on_clean_packet(self):
        assert security_gate(_base_packet()).passed

    def test_fail_on_secret_in_diff(self):
        result = security_gate(_base_packet(diff_text="+ sk-leak123\n"))
        assert result.status == "fail"

    def test_fail_on_dependency_change_without_separate_review(self):
        result = security_gate(
            _base_packet(
                is_dependency_change=True, dependency_review_separate=False
            )
        )
        assert result.status == "fail"
        assert any("separate review" in r for r in result.reasons)

    def test_pass_on_dependency_change_with_separate_review(self):
        result = security_gate(
            _base_packet(
                is_dependency_change=True, dependency_review_separate=True
            )
        )
        assert result.passed, result.reasons

    def test_fail_on_credential_file_edit_without_approval(self):
        result = security_gate(
            _base_packet(
                credential_files_edited=[".env"],
                credential_edits_approved=False,
            )
        )
        assert result.status == "fail"
        assert any("credential files edited" in r for r in result.reasons)

    def test_fail_on_added_network_calls(self):
        result = security_gate(_base_packet(network_calls_added=True))
        assert result.status == "fail"

    def test_needs_owner_approval_on_publish(self):
        result = security_gate(_base_packet(is_publish_or_deploy=True))
        assert result.status == "needs_owner_approval"


class TestReleaseGate:
    def test_pass_when_release_fields_complete(self):
        assert release_gate(_base_packet()).passed

    @pytest.mark.parametrize(
        "field,empty_value,needle",
        [
            ("changed_files", [], "no changed files"),
            ("pr_summary", "", "missing PR summary"),
            ("pr_body_ready", False, "PR body not marked ready"),
            ("commits_scoped", False, "commits not scoped"),
            ("verification_summary", "", "verification summary"),
            ("rollback_plan", "", "rollback plan"),
            ("remaining_risks", [], "remaining risks"),
        ],
    )
    def test_each_required_field_missing_fails(self, field, empty_value, needle):
        result = release_gate(_base_packet(**{field: empty_value}))
        assert result.status == "fail"
        assert any(needle in r for r in result.reasons), result.reasons


class TestOwnerApproval:
    def test_no_owner_action_passes_without_phrase(self):
        result = owner_approval_gate(
            _base_packet(is_publish_or_deploy=False, owner_approval="")
        )
        assert result.passed
        assert "no owner-gated action present" in result.reasons[0]

    def test_exact_phrase_passes(self):
        result = owner_approval_gate(
            _base_packet(
                is_publish_or_deploy=True,
                owner_approval=OWNER_APPROVAL_PHRASE,
            )
        )
        assert result.passed, result.reasons

    def test_missing_phrase_fails(self):
        result = owner_approval_gate(
            _base_packet(is_publish_or_deploy=True, owner_approval="")
        )
        assert result.status == "fail"

    def test_typo_fails(self):
        result = owner_approval_gate(
            _base_packet(
                is_publish_or_deploy=True,
                owner_approval="I approve this owner gated action.",  # missing hyphen
            )
        )
        assert result.status == "fail"

    def test_trailing_whitespace_fails(self):
        result = owner_approval_gate(
            _base_packet(
                is_publish_or_deploy=True,
                owner_approval=OWNER_APPROVAL_PHRASE + " ",
            )
        )
        assert result.status == "fail"

    def test_case_change_fails(self):
        result = owner_approval_gate(
            _base_packet(
                is_publish_or_deploy=True,
                owner_approval=OWNER_APPROVAL_PHRASE.upper(),
            )
        )
        assert result.status == "fail"

    def test_phrase_constant_locked(self):
        assert OWNER_APPROVAL_PHRASE == "I approve this owner-gated action."


class TestRollbackGate:
    def test_pass_with_rollback_plan(self):
        assert rollback_gate(_base_packet()).passed

    def test_fail_when_missing_rollback_plan(self):
        result = rollback_gate(_base_packet(rollback_plan=""))
        assert result.status == "fail"
        assert any("missing rollback" in r for r in result.reasons)

    def test_fail_when_risky_runtime_change_lacks_revert_strategy(self):
        result = rollback_gate(
            _base_packet(risky_runtime_change=True, revert_strategy="")
        )
        assert result.status == "fail"
        assert any("revert strategy" in r for r in result.reasons)

    def test_pass_when_risky_runtime_change_has_revert_strategy(self):
        result = rollback_gate(
            _base_packet(
                risky_runtime_change=True,
                revert_strategy="feature flag JARVIS_GATE_RUNTIME=off",
            )
        )
        assert result.passed


# ── realistic ACI build-packet scenarios ────────────────────────────────────


class TestRealisticScenarios:
    def test_clean_docs_only_pr_passes_all_gates(self):
        results = run_all_gates(_base_packet())
        assert overall_status(results) == "pass", {
            n: r.reasons for n, r in results.items() if not r.passed
        }

    def test_code_change_with_tests_passes_all_gates(self):
        packet = _base_packet(
            allowed_files=[
                "hermes_cli/jarvis_prime/gates.py",
                "tests/test_jarvis_prime_gates.py",
            ],
            changed_files=[
                "hermes_cli/jarvis_prime/gates.py",
                "tests/test_jarvis_prime_gates.py",
            ],
            docs_only_stage=False,
            review_findings=[
                {"severity": "med", "kind": "blocking", "note": "edge"},
                {"severity": "low", "kind": "improvement", "note": "nit"},
            ],
        )
        results = run_all_gates(packet)
        assert overall_status(results) == "pass", {
            n: r.reasons for n, r in results.items() if not r.passed
        }

    def test_dependency_change_without_separate_review_fails_security(self):
        packet = _base_packet(
            is_dependency_change=True,
            dependency_review_separate=False,
        )
        results = run_all_gates(packet)
        assert results["security"].status == "fail"
        assert overall_status(results) == "fail"

    def test_dependency_change_with_separate_review_passes_security(self):
        packet = _base_packet(
            is_dependency_change=True,
            dependency_review_separate=True,
        )
        results = run_all_gates(packet)
        assert results["security"].passed, results["security"].reasons

    def test_secret_accidentally_added_fails_build_and_security(self):
        packet = _base_packet(diff_text="+ GH_TOKEN=ghp_leakedvalueXYZ\n")
        results = run_all_gates(packet)
        assert results["build"].status == "fail"
        assert results["security"].status == "fail"
        assert overall_status(results) == "fail"

    def test_publish_attempt_blocked_without_phrase_then_unblocked(self):
        # Step 1: publish attempt with no owner approval → fails overall.
        attempt = _base_packet(is_publish_or_deploy=True, owner_approval="")
        results = run_all_gates(attempt)
        assert results["security"].status == "needs_owner_approval"
        assert results["owner_approval"].status == "fail"
        assert overall_status(results) == "fail"

        # Step 2: exact phrase provided → security still owner-gated, but
        # owner_approval gate passes → overall is needs_owner_approval.
        approved = _base_packet(
            is_publish_or_deploy=True,
            owner_approval=OWNER_APPROVAL_PHRASE,
        )
        results2 = run_all_gates(approved)
        assert results2["security"].status == "needs_owner_approval"
        assert results2["owner_approval"].passed
        assert overall_status(results2) == "needs_owner_approval"

    def test_missing_rollback_fails_rollback_and_release(self):
        packet = _base_packet(rollback_plan="")
        results = run_all_gates(packet)
        assert results["rollback"].status == "fail"
        assert results["release"].status == "fail"

    def test_concurrent_claude_codex_branch_edit_fails_build(self):
        packet = _base_packet(concurrent_editors=["claude", "codex"])
        results = run_all_gates(packet)
        assert results["build"].status == "fail"
        assert any(
            "concurrent editors" in r for r in results["build"].reasons
        )
        assert overall_status(results) == "fail"

    def test_no_tests_with_valid_skip_reason_passes_test_gate(self):
        packet = _base_packet(
            tests_run=False,
            tests_passed=False,
            test_skip_reason="docs-only diff; no behavior change",
            unverified_risk_named=True,
        )
        results = run_all_gates(packet)
        assert results["test"].passed, results["test"].reasons


# ── aggregation, defaults, contract ─────────────────────────────────────────


class TestAggregation:
    def test_run_all_gates_returns_eight_entries(self):
        results = run_all_gates(_base_packet())
        assert len(results) == 8

    def test_run_all_gates_keys_match_ALL_GATES_names(self):
        names_from_results = set(run_all_gates(_base_packet()).keys())
        names_from_registry = {name for name, _ in ALL_GATES}
        assert names_from_results == names_from_registry
        assert names_from_registry == {
            "planning",
            "build",
            "review",
            "test",
            "security",
            "release",
            "owner_approval",
            "rollback",
        }

    def test_all_gates_are_callable(self):
        for name, fn in ALL_GATES:
            assert callable(fn), name

    def test_overall_status_pass_when_all_pass(self):
        results = run_all_gates(_base_packet())
        assert overall_status(results) == "pass"

    def test_overall_status_needs_owner_approval_when_one_owner_gated(self):
        results = run_all_gates(
            _base_packet(
                is_publish_or_deploy=True,
                owner_approval=OWNER_APPROVAL_PHRASE,
            )
        )
        assert overall_status(results) == "needs_owner_approval"

    def test_overall_status_fail_dominates_owner_approval(self):
        # Publish attempt without phrase: owner_approval fails AND security
        # is needs_owner_approval. Overall must be "fail".
        results = run_all_gates(
            _base_packet(is_publish_or_deploy=True, owner_approval="")
        )
        assert overall_status(results) == "fail"

    def test_no_production_deploy_passes_without_owner_approval(self):
        # Acceptance criterion: a publish/deploy with the wrong phrase
        # must never produce overall "pass".
        for bad_phrase in (
            "",
            "i approve this owner-gated action.",
            "I approve this owner-gated action",  # missing period
            "I approve this owner-gated action. ",  # trailing space
            "I approve this owner gated action.",  # missing hyphen
        ):
            results = run_all_gates(
                _base_packet(
                    is_publish_or_deploy=True, owner_approval=bad_phrase
                )
            )
            assert overall_status(results) != "pass", bad_phrase


class TestPacketDefaults:
    def test_packet_defaults_are_independent_lists(self):
        p1 = Packet()
        p2 = Packet()
        p1.allowed_files.append("leak")
        assert p2.allowed_files == []

    def test_gate_result_passed_property(self):
        assert GateResult("pass").passed
        assert not GateResult("fail").passed
        assert not GateResult("needs_owner_approval").passed
