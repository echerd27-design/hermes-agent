"""JARVIS Prime verification gates — runtime implementation.

Source of truth for the gate semantics is
``docs/jarvis-verification-gates.md``. Each gate accepts a
:class:`Packet` (an ACI build packet) and returns a :class:`GateResult`
with one of three statuses: ``"pass"``, ``"fail"``, or
``"needs_owner_approval"``.

The module is stdlib-only and side-effect free. It is safe to import
in any environment (Termux, CI, sandboxed test runner) without
network access or credentials.

This file is intentionally created without a sibling ``__init__.py``;
``hermes_cli.jarvis_prime`` is a PEP 420 namespace subpackage of the
regular ``hermes_cli`` package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal


OWNER_APPROVAL_PHRASE: str = "I approve this owner-gated action."


_SECRET_PATTERNS: tuple[str, ...] = (
    "sk-",
    "api_key=",
    "AWS_SECRET_ACCESS_KEY=",
    "GH_TOKEN=",
    "GITHUB_TOKEN=",
    "ANTHROPIC_API_KEY=",
    "OPENAI_API_KEY=",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
)


GateStatus = Literal["pass", "fail", "needs_owner_approval"]


@dataclass
class Packet:
    """An ACI build packet — the input to every gate."""

    # Planning
    repo: str = ""
    branch: str = ""
    working_tree: str = "clean"
    mission: str = ""
    goal: str = ""
    allowed_files: list[str] = field(default_factory=list)
    disallowed_files: list[str] = field(default_factory=list)
    protected_files: list[str] = field(default_factory=list)
    protected_edit_approved: bool = False
    non_goals: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    owner_gates_identified: bool = False

    # Build
    changed_files: list[str] = field(default_factory=list)
    concurrent_editors: list[str] = field(default_factory=list)
    docs_only_stage: bool = False
    diff_text: str = ""

    # Review
    review_findings: list[dict] = field(default_factory=list)
    contrarian_objection: str = ""

    # Test
    tests_run: bool = False
    tests_passed: bool = False
    test_skip_reason: str = ""
    unverified_risk_named: bool = False
    git_diff_check_passed: bool = True

    # Security
    is_dependency_change: bool = False
    dependency_review_separate: bool = False
    credential_files_edited: list[str] = field(default_factory=list)
    credential_edits_approved: bool = False
    network_calls_added: bool = False
    is_publish_or_deploy: bool = False

    # Release
    pr_summary: str = ""
    pr_body_ready: bool = False
    commits_scoped: bool = False
    verification_summary: str = ""
    remaining_risks: list[str] = field(default_factory=list)

    # Owner
    owner_approval: str = ""

    # Rollback
    rollback_plan: str = ""
    commit_hash_or_file_list: str = ""
    risky_runtime_change: bool = False
    revert_strategy: str = ""


@dataclass
class GateResult:
    status: GateStatus
    reasons: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def _contains_secret(diff_text: str) -> bool:
    return any(pat in diff_text for pat in _SECRET_PATTERNS)


def planning_gate(p: Packet) -> GateResult:
    reasons: list[str] = []
    if not p.repo:
        reasons.append("missing repo")
    if not p.branch:
        reasons.append("missing branch")
    if not p.goal:
        reasons.append("missing goal")
    if not p.allowed_files:
        reasons.append("allowed_files is empty")
    if not p.acceptance_criteria:
        reasons.append("acceptance_criteria is empty")
    if not p.owner_gates_identified:
        reasons.append("owner gates not identified")
    if reasons:
        return GateResult("fail", reasons)
    return GateResult("pass", ["planning fields complete"])


def build_gate(p: Packet) -> GateResult:
    reasons: list[str] = []

    distinct_editors = {e.lower() for e in p.concurrent_editors if e}
    if len(distinct_editors) > 1:
        reasons.append(
            f"concurrent editors on same branch: {sorted(distinct_editors)}"
        )

    allowed = set(p.allowed_files)
    out_of_scope = [f for f in p.changed_files if f not in allowed]
    if out_of_scope:
        reasons.append(f"changed files outside allowed list: {out_of_scope}")

    if _contains_secret(p.diff_text):
        reasons.append("secret-shaped token found in diff")

    protected_hit = sorted(set(p.protected_files) & set(p.changed_files))
    if protected_hit and not p.protected_edit_approved:
        reasons.append(
            f"protected files edited without approval: {protected_hit}"
        )

    if p.docs_only_stage:
        runtime_changes = [
            f
            for f in p.changed_files
            if not (f.startswith("docs/") or f.endswith(".md"))
        ]
        if runtime_changes:
            reasons.append(
                f"runtime files touched in docs-only stage: {runtime_changes}"
            )

    if reasons:
        return GateResult("fail", reasons)
    return GateResult("pass", ["build scope respected"])


def review_gate(p: Packet) -> GateResult:
    if not p.changed_files:
        return GateResult("pass", ["no diff to review"])

    reasons: list[str] = []

    if not p.review_findings:
        reasons.append("no review findings recorded for non-empty diff")
    else:
        kinds: set[str] = set()
        for idx, finding in enumerate(p.review_findings):
            if "severity" not in finding:
                reasons.append(f"finding[{idx}] missing severity")
            kind = finding.get("kind")
            if kind in {"blocking", "improvement"}:
                kinds.add(kind)
        if "blocking" not in kinds and "improvement" not in kinds:
            reasons.append(
                "findings missing blocking-vs-improvement separation"
            )

    if not p.contrarian_objection:
        reasons.append("contrarian objection missing")

    if reasons:
        return GateResult("fail", reasons)
    return GateResult("pass", ["review complete"])


def test_gate(p: Packet) -> GateResult:
    reasons: list[str] = []

    if p.tests_run:
        if not p.tests_passed:
            reasons.append("tests run but did not pass")
    else:
        if not p.test_skip_reason:
            reasons.append("tests not run and no skip reason provided")
        elif not p.unverified_risk_named:
            reasons.append(
                "tests skipped but unverified risk not named"
            )

    if not p.git_diff_check_passed:
        reasons.append("git diff --check failed (whitespace errors)")

    if reasons:
        return GateResult("fail", reasons)
    return GateResult("pass", ["test gate complete"])


def security_gate(p: Packet) -> GateResult:
    reasons: list[str] = []

    if _contains_secret(p.diff_text):
        reasons.append("secret-shaped token found in diff")

    if p.network_calls_added:
        reasons.append("network calls added to local-only scope")

    if p.is_dependency_change and not p.dependency_review_separate:
        reasons.append("dependency change not in separate review")

    if p.credential_files_edited and not p.credential_edits_approved:
        reasons.append(
            f"credential files edited without approval: "
            f"{sorted(set(p.credential_files_edited))}"
        )

    if reasons:
        return GateResult("fail", reasons)

    if p.is_publish_or_deploy:
        return GateResult(
            "needs_owner_approval",
            ["publish/deploy action requires owner approval"],
        )

    return GateResult("pass", ["security checks pass"])


def release_gate(p: Packet) -> GateResult:
    reasons: list[str] = []
    if not p.changed_files:
        reasons.append("no changed files listed")
    if not p.pr_summary:
        reasons.append("missing PR summary")
    if not p.pr_body_ready:
        reasons.append("PR body not marked ready")
    if not p.commits_scoped:
        reasons.append("commits not scoped")
    if not p.verification_summary:
        reasons.append("missing verification summary")
    if not p.rollback_plan:
        reasons.append("missing rollback plan in release")
    if not p.remaining_risks:
        reasons.append("remaining risks not stated")
    if reasons:
        return GateResult("fail", reasons)
    return GateResult("pass", ["release fields complete"])


def owner_approval_gate(p: Packet) -> GateResult:
    if not p.is_publish_or_deploy:
        return GateResult("pass", ["no owner-gated action present"])
    if p.owner_approval == OWNER_APPROVAL_PHRASE:
        return GateResult("pass", ["owner approval phrase matched"])
    return GateResult(
        "fail",
        [
            "owner approval required but missing or incorrect; "
            f"expected exact phrase: {OWNER_APPROVAL_PHRASE!r}"
        ],
    )


def rollback_gate(p: Packet) -> GateResult:
    reasons: list[str] = []
    if not p.rollback_plan:
        reasons.append("missing rollback plan")
    if p.risky_runtime_change and not p.revert_strategy:
        reasons.append("risky runtime change without revert strategy")
    if reasons:
        return GateResult("fail", reasons)
    return GateResult("pass", ["rollback plan present"])


ALL_GATES: tuple[tuple[str, Callable[[Packet], GateResult]], ...] = (
    ("planning", planning_gate),
    ("build", build_gate),
    ("review", review_gate),
    ("test", test_gate),
    ("security", security_gate),
    ("release", release_gate),
    ("owner_approval", owner_approval_gate),
    ("rollback", rollback_gate),
)


def run_all_gates(p: Packet) -> dict[str, GateResult]:
    return {name: fn(p) for name, fn in ALL_GATES}


def overall_status(results: dict[str, GateResult]) -> GateStatus:
    statuses = {r.status for r in results.values()}
    if "fail" in statuses:
        return "fail"
    if "needs_owner_approval" in statuses:
        return "needs_owner_approval"
    return "pass"
