"""Tests for hermes_cli.jarvis_prime.gate_reports.

These tests use locally-defined fake gate result objects and dicts
so they do NOT depend on the runtime gate evaluator
(`hermes_cli.jarvis_prime.gates`), which is built by a different wave.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from hermes_cli.jarvis_prime import (
    GATE_DISPLAY_NAMES,
    GATE_ORDER,
    STATUS_FAIL,
    STATUS_OWNER_APPROVAL,
    STATUS_PASS,
    STATUS_SKIPPED,
    as_dict,
    failure_summary,
    markdown_report,
    mobile_report,
    owner_approval_summary,
)


# ── Fakes (no import from gates.py) ───────────────────────────────────


@dataclass
class FakeGateResult:
    name: str
    status: str
    message: str = ""
    owner: str = ""
    evidence: str = ""


@dataclass
class FakeReport:
    gates: list = field(default_factory=list)
    result: str = ""
    remaining_risk: str = ""
    next_action: str = ""
    title: str = ""
    timestamp: str = ""


def _full_pass_gates() -> list[FakeGateResult]:
    return [
        FakeGateResult(name=GATE_DISPLAY_NAMES[k], status=STATUS_PASS, message=f"{k} ok")
        for k in GATE_ORDER
    ]


def _mixed_status_gates() -> list[FakeGateResult]:
    return [
        FakeGateResult(name="Planning gate", status="pass"),
        FakeGateResult(name="Build gate", status="pass", message="scope respected"),
        FakeGateResult(name="Review gate", status="pass"),
        FakeGateResult(name="Test gate", status="fail", message="2 failing unit tests"),
        FakeGateResult(name="Security gate", status="pass", message="no secret edits"),
        FakeGateResult(name="Release gate", status="skipped", message="blocked on tests"),
        FakeGateResult(
            name="Owner approval gate",
            status="owner_approval",
            message="deploy step needs sign-off",
            owner="Jeremiah",
        ),
        FakeGateResult(
            name="Rollback gate",
            status="pass",
            message="revert via git revert HEAD~1",
        ),
    ]


def _gates_to_dicts(gates: list[FakeGateResult]) -> list[dict[str, str]]:
    return [
        {
            "name": g.name,
            "status": g.status,
            "message": g.message,
            "owner": g.owner,
            "evidence": g.evidence,
        }
        for g in gates
    ]


# ── Duck-typed contract ───────────────────────────────────────────────


class TestDuckTypedContract:
    def test_accepts_object_gate_with_attributes(self):
        report = FakeReport(
            gates=_mixed_status_gates(),
            result="fail",
            remaining_risk="risk x",
            next_action="run tests",
        )
        out = markdown_report(report)
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out

    def test_accepts_dict_gate(self):
        report = FakeReport(
            gates=_gates_to_dicts(_mixed_status_gates()),
            result="fail",
        )
        out = markdown_report(report)
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out
        assert "FAIL" in out

    def test_mixed_object_and_dict_gates(self):
        object_gates = _mixed_status_gates()[:4]
        dict_gates = _gates_to_dicts(_mixed_status_gates()[4:])
        report = FakeReport(gates=[*object_gates, *dict_gates])
        out = markdown_report(report)
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out

    def test_accepts_dict_report(self):
        report = {
            "gates": _gates_to_dicts(_mixed_status_gates()),
            "result": "fail",
            "remaining_risk": "see test gate",
            "next_action": "rerun pytest",
        }
        out = markdown_report(report)
        assert "see test gate" in out
        assert "rerun pytest" in out

    def test_object_report_with_overall_alias(self):
        @dataclass
        class AltReport:
            gates: list
            overall: str = ""
            remaining_risk: str = ""
            next_action: str = ""

        report = AltReport(gates=_mixed_status_gates(), overall="pass")
        # Explicit overall is honored verbatim — even though a fail row exists.
        assert "## Result\n\nPASS" in markdown_report(report)


# ── Markdown ──────────────────────────────────────────────────────────


class TestMarkdownReport:
    def test_contains_all_eight_canonical_gates_when_all_present(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        out = markdown_report(report)
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out
        assert "## Result" in out
        assert "## Remaining risk" in out
        assert "## Next action" in out

    def test_missing_gates_render_as_skipped_not_run(self):
        partial = [
            FakeGateResult(name="Planning gate", status="pass"),
            FakeGateResult(name="Build gate", status="pass"),
            FakeGateResult(name="Test gate", status="pass"),
        ]
        report = FakeReport(gates=partial)
        out = markdown_report(report)
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out
        # Five canonical gates were not provided; each should appear as
        # SKIPPED with "not run" detail.
        skipped_lines = [
            line for line in out.splitlines() if "SKIPPED" in line and "not run" in line
        ]
        assert len(skipped_lines) == 5

    def test_markdown_is_deterministic(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        assert markdown_report(report) == markdown_report(report)

    def test_input_order_does_not_affect_output(self):
        gates = _mixed_status_gates()
        report_a = FakeReport(gates=list(gates), result="fail")
        report_b = FakeReport(gates=list(reversed(gates)), result="fail")
        assert markdown_report(report_a) == markdown_report(report_b)

    def test_title_and_timestamp_appear(self):
        report = FakeReport(
            gates=_full_pass_gates(),
            title="W09 Verification",
            timestamp="2026-05-26T18:00:00Z",
        )
        out = markdown_report(report)
        assert "# W09 Verification" in out
        assert "2026-05-26T18:00:00Z" in out


# ── Mobile ────────────────────────────────────────────────────────────


class TestMobileReport:
    def test_mobile_under_length_budget(self):
        report = FakeReport(
            gates=_mixed_status_gates(),
            result="fail",
            remaining_risk="Cannot ship until Test gate clears.",
        )
        out = mobile_report(report)
        assert len(out) <= 400
        assert "Risk:" in out
        assert "Next:" in out

    def test_mobile_calls_out_first_failure_when_present(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        out = mobile_report(report)
        assert "First fail" in out
        assert "Test gate" in out
        assert "2 failing unit tests" in out

    def test_mobile_ok_path_when_all_pass(self):
        report = FakeReport(gates=_full_pass_gates(), result="pass")
        out = mobile_report(report)
        assert "PASS" in out
        assert "First fail" not in out
        assert "Owner needed" not in out
        assert "Risk:" in out
        assert "Next:" in out

    def test_mobile_calls_out_owner_when_no_fail_but_owner_pending(self):
        gates = [
            FakeGateResult(name=GATE_DISPLAY_NAMES[k], status="pass")
            for k in GATE_ORDER
            if k != "owner_approval"
        ]
        gates.append(
            FakeGateResult(
                name="Owner approval gate",
                status="owner_approval",
                message="deploy",
                owner="Jeremiah",
            )
        )
        report = FakeReport(gates=gates)
        out = mobile_report(report)
        assert "Owner needed" in out
        assert "Owner approval gate" in out

    def test_mobile_truncates_long_risk_and_next(self):
        long_text = "x" * 500
        report = FakeReport(
            gates=_full_pass_gates(),
            remaining_risk=long_text,
            next_action=long_text,
        )
        out = mobile_report(report)
        assert len(out) <= 400
        assert "..." in out

    def test_mobile_is_single_line_per_section(self):
        report = FakeReport(
            gates=_mixed_status_gates(),
            remaining_risk="line one\nline two\nline three",
            next_action="alpha\nbeta",
        )
        out = mobile_report(report)
        risk_lines = [ln for ln in out.splitlines() if ln.startswith("Risk:")]
        next_lines = [ln for ln in out.splitlines() if ln.startswith("Next:")]
        assert len(risk_lines) == 1
        assert len(next_lines) == 1


# ── as_dict ───────────────────────────────────────────────────────────


class TestAsDict:
    def test_as_dict_is_json_safe(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        payload = as_dict(report)
        encoded = json.dumps(payload, sort_keys=True)
        assert json.loads(encoded) == payload

    def test_counts_match_gates(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        payload = as_dict(report)
        # _mixed_status_gates supplies all 8 canonical gates, so counts
        # must sum to 8.
        assert sum(payload["counts"].values()) == 8
        assert payload["counts"][STATUS_PASS] == 5
        assert payload["counts"][STATUS_FAIL] == 1
        assert payload["counts"][STATUS_OWNER_APPROVAL] == 1
        assert payload["counts"][STATUS_SKIPPED] == 1

    def test_no_non_serializable_types(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        payload = as_dict(report)

        def _walk(value: Any) -> None:
            if isinstance(value, dict):
                for k, v in value.items():
                    assert isinstance(k, str)
                    _walk(v)
            elif isinstance(value, list):
                for v in value:
                    _walk(v)
            else:
                assert isinstance(value, (str, int, bool)) or value is None, (
                    f"unexpected type {type(value)} for value {value!r}"
                )

        _walk(payload)

    def test_as_dict_has_required_keys(self):
        report = FakeReport(gates=[], result="")
        payload = as_dict(report)
        for k in (
            "title",
            "timestamp",
            "gates",
            "counts",
            "result",
            "remaining_risk",
            "next_action",
        ):
            assert k in payload

    def test_as_dict_emits_all_eight_canonical_gates(self):
        report = FakeReport(gates=[])
        payload = as_dict(report)
        names = {g["name"] for g in payload["gates"]}
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in names


# ── Failure summary ───────────────────────────────────────────────────


class TestFailureSummary:
    def test_lists_only_failed_gates(self):
        report = FakeReport(
            gates=_mixed_status_gates(),
            result="fail",
            remaining_risk="r",
            next_action="n",
        )
        out = failure_summary(report)
        assert "Test gate" in out
        assert "2 failing unit tests" in out
        # Passing gates should not appear in the failure list body.
        assert "Planning gate" not in out
        assert "Review gate" not in out
        # Risk + next action are always present.
        assert "Remaining risk:" in out
        assert "Next action:" in out

    def test_no_failures_branch(self):
        report = FakeReport(gates=_full_pass_gates(), result="pass")
        out = failure_summary(report)
        assert "No failed gates." in out
        assert "Remaining risk:" in out
        assert "Next action:" in out

    def test_multiple_failures_listed(self):
        gates = [
            FakeGateResult(name="Test gate", status="fail", message="a"),
            FakeGateResult(name="Security gate", status="fail", message="b"),
        ]
        report = FakeReport(gates=gates)
        out = failure_summary(report)
        assert "Failed gates (2):" in out
        assert "Test gate" in out
        assert "Security gate" in out


# ── Owner approval summary ────────────────────────────────────────────


class TestOwnerApprovalSummary:
    def test_includes_owner_name_and_message(self):
        report = FakeReport(gates=_mixed_status_gates(), result="fail")
        out = owner_approval_summary(report)
        assert "Owner approval gate" in out
        assert "Jeremiah" in out
        assert "deploy step needs sign-off" in out
        assert "Remaining risk:" in out
        assert "Next action:" in out

    def test_none_pending_branch(self):
        report = FakeReport(gates=_full_pass_gates(), result="pass")
        out = owner_approval_summary(report)
        assert "No owner-approval gates pending." in out
        assert "Remaining risk:" in out
        assert "Next action:" in out


# ── Edge cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_report_renders_all_skipped(self):
        report = FakeReport(gates=[])
        out = markdown_report(report)
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out
        skipped_lines = [
            line for line in out.splitlines() if "SKIPPED" in line and "not run" in line
        ]
        assert len(skipped_lines) == 8
        assert "## Result\n\nSKIPPED" in out

    def test_unknown_gate_name_does_not_crash(self):
        gates = [
            FakeGateResult(name="Planning gate", status="pass"),
            FakeGateResult(name="FooBar Gate", status="fail", message="weird gate"),
        ]
        report = FakeReport(gates=gates)
        out = markdown_report(report)
        assert "FooBar Gate" in out
        assert "weird gate" in out

    def test_unknown_status_coerced_to_skipped(self):
        gates = [
            FakeGateResult(name="Planning gate", status="weird-value"),
        ]
        report = FakeReport(gates=gates)
        out = markdown_report(report)
        # The unknown status should be normalized to skipped.
        # That gate should NOT appear as PASS/FAIL/OWNER APPROVAL.
        planning_line = next(
            (ln for ln in out.splitlines() if "Planning gate" in ln), None
        )
        assert planning_line is not None
        assert "SKIPPED" in planning_line

    def test_missing_optional_fields_use_defaults(self):
        gates = [{"name": "Planning gate", "status": "pass"}]
        report = {"gates": gates}
        # Should not raise.
        md = markdown_report(report)
        assert "Planning gate" in md
        assert "Remaining risk" in md
        assert "None stated." in md
        assert "Next action" in md
        assert "Proceed." in md

    def test_overall_result_derived_when_absent(self):
        gates = _mixed_status_gates()
        report = FakeReport(gates=gates, result="")
        payload = as_dict(report)
        assert payload["result"] == STATUS_FAIL

        all_pass = FakeReport(gates=_full_pass_gates(), result="")
        assert as_dict(all_pass)["result"] == STATUS_PASS

        empty = FakeReport(gates=[], result="")
        assert as_dict(empty)["result"] == STATUS_SKIPPED

    def test_overall_explicit_overrides_derivation(self):
        report = FakeReport(gates=_mixed_status_gates(), result="pass")
        payload = as_dict(report)
        # Explicit value is preserved even with a fail row present.
        assert payload["result"] == STATUS_PASS

    def test_status_aliases_accepted(self):
        cases = [
            ("OWNER APPROVAL", STATUS_OWNER_APPROVAL),
            ("owner-approval", STATUS_OWNER_APPROVAL),
            ("PASSED", STATUS_PASS),
            ("failed", STATUS_FAIL),
            ("not run", STATUS_SKIPPED),
        ]
        for raw, expected in cases:
            report = FakeReport(
                gates=[FakeGateResult(name="Planning gate", status=raw)]
            )
            payload = as_dict(report)
            planning = next(
                g for g in payload["gates"] if g["name"] == "Planning gate"
            )
            assert planning["status"] == expected, (
                f"raw={raw!r} expected={expected!r} got={planning['status']!r}"
            )

    def test_name_aliases_accepted(self):
        cases = [
            "planning_gate",
            "Planning Gate",
            "PLANNING",
            "planning",
        ]
        for raw in cases:
            report = FakeReport(
                gates=[FakeGateResult(name=raw, status="pass")]
            )
            payload = as_dict(report)
            names = [g["name"] for g in payload["gates"]]
            # Canonical display "Planning gate" should appear exactly once
            # in the canonical block.
            assert names.count("Planning gate") == 1, (
                f"raw={raw!r} names={names}"
            )

    def test_remaining_risk_default_when_blank(self):
        report = FakeReport(gates=_full_pass_gates(), remaining_risk="")
        out = markdown_report(report)
        assert "None stated." in out

    def test_next_action_default_when_blank_uses_overall(self):
        # Pass overall → "Proceed."
        pass_out = markdown_report(
            FakeReport(gates=_full_pass_gates(), next_action="")
        )
        assert "Proceed." in pass_out

        # Fail overall → "Block on fail; resolve failing gates before proceeding."
        fail_out = markdown_report(
            FakeReport(gates=_mixed_status_gates(), next_action="")
        )
        assert "Block on fail" in fail_out

        # Owner-approval overall → "Awaiting owner approval."
        owner_gates = [
            FakeGateResult(name=GATE_DISPLAY_NAMES[k], status="pass")
            for k in GATE_ORDER
            if k != "owner_approval"
        ]
        owner_gates.append(
            FakeGateResult(name="Owner approval gate", status="owner_approval")
        )
        owner_out = markdown_report(FakeReport(gates=owner_gates, next_action=""))
        assert "Awaiting owner approval." in owner_out

    def test_does_not_import_gates_module(self):
        import sys
        import hermes_cli.jarvis_prime as pkg  # noqa: F401

        assert "hermes_cli.jarvis_prime.gates" not in sys.modules

    @pytest.mark.parametrize("bad_gates", [None, "not a list", 42, {"x": 1}])
    def test_non_sequence_gates_is_treated_as_empty(self, bad_gates):
        report = FakeReport(gates=bad_gates)  # type: ignore[arg-type]
        out = markdown_report(report)
        # Still renders all 8 canonical rows as skipped.
        for k in GATE_ORDER:
            assert GATE_DISPLAY_NAMES[k] in out
