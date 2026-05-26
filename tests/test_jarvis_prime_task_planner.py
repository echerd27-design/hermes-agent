"""Tests for hermes_cli.jarvis_prime.task_planner.

Covers determinism, dispatch, role/phase invariants, dependency consistency,
and the wave's hard constraint that the planner has no dependency on the
forbidden ``jobs`` / ``job_store`` modules.
"""

from __future__ import annotations

import inspect
import json
import re

import pytest

from hermes_cli.jarvis_prime import task_planner
from hermes_cli.jarvis_prime.task_planner import (
    MISSIONS,
    PHASE_ORDER,
    SCHEMA_VERSION,
    plan_android_build_check,
    plan_bug_fix,
    plan_docs_only_update,
    plan_for,
    plan_gateway_setup,
    plan_launch_readiness,
    plan_release_pr,
    plan_repo_audit,
    plan_security_review,
    plan_slack_setup,
)


_PLAN_FUNCS = (
    plan_repo_audit,
    plan_bug_fix,
    plan_launch_readiness,
    plan_android_build_check,
    plan_gateway_setup,
    plan_slack_setup,
    plan_docs_only_update,
    plan_security_review,
    plan_release_pr,
)


def _all_tasks(plan):
    for phase in plan["phases"]:
        for task in phase["tasks"]:
            yield phase["name"], task


# ─── Module surface ─────────────────────────────────────────────────────────


def test_missions_is_frozen_tuple_of_nine_unique_keys():
    assert isinstance(MISSIONS, tuple), "MISSIONS must be a tuple"
    assert len(MISSIONS) == 9, f"expected 9 missions, got {len(MISSIONS)}"
    assert len(set(MISSIONS)) == 9, "mission keys must be unique"


def test_phase_order_constant_matches_wave_contract():
    assert PHASE_ORDER == ("builder", "reviewer", "tester", "owner_approval")


def test_schema_version_is_set():
    assert SCHEMA_VERSION == "1.0"


def test_package_init_reexports_public_api():
    import hermes_cli.jarvis_prime as jp

    assert jp.MISSIONS == MISSIONS
    assert jp.plan_for is plan_for
    for fn in _PLAN_FUNCS:
        assert getattr(jp, fn.__name__) is fn, f"missing re-export: {fn.__name__}"


# ─── Phase / role separation ────────────────────────────────────────────────


@pytest.mark.parametrize("mission", MISSIONS)
def test_each_plan_separates_four_phases_in_order(mission):
    plan = plan_for(mission)

    assert plan["mission"] == mission
    assert plan["phase_order"] == ("builder", "reviewer", "tester", "owner_approval")

    names = [phase["name"] for phase in plan["phases"]]
    assert names == ["builder", "reviewer", "tester", "owner_approval"], (
        f"{mission} phases out of order: {names}"
    )

    for phase in plan["phases"]:
        assert phase["tasks"], f"{mission} phase {phase['name']} has no tasks"


@pytest.mark.parametrize("mission", MISSIONS)
def test_each_task_role_matches_its_phase_name(mission):
    plan = plan_for(mission)
    for phase_name, task in _all_tasks(plan):
        assert task["role"] == phase_name, (
            f"{mission} task {task['id']} role={task['role']} "
            f"does not match phase {phase_name}"
        )


# ─── Task identity and dependencies ─────────────────────────────────────────


@pytest.mark.parametrize("mission", MISSIONS)
def test_task_ids_are_unique_within_each_plan(mission):
    plan = plan_for(mission)
    ids = [task["id"] for _, task in _all_tasks(plan)]
    assert len(ids) == len(set(ids)), f"duplicate task id in {mission}: {ids}"


@pytest.mark.parametrize("mission", MISSIONS)
def test_task_ids_are_namespaced_by_mission_and_phase(mission):
    plan = plan_for(mission)
    for phase_name, task in _all_tasks(plan):
        prefix = f"{mission}.{phase_name}."
        assert task["id"].startswith(prefix), (
            f"task id {task['id']} missing prefix {prefix}"
        )


@pytest.mark.parametrize("mission", MISSIONS)
def test_depends_on_references_resolve_within_plan(mission):
    plan = plan_for(mission)
    known_ids = {task["id"] for _, task in _all_tasks(plan)}
    for _, task in _all_tasks(plan):
        for dep in task["depends_on"]:
            assert dep in known_ids, (
                f"{mission} task {task['id']} depends on unknown id {dep}"
            )


@pytest.mark.parametrize("mission", MISSIONS)
def test_edges_match_depends_on_exactly_and_are_sorted(mission):
    plan = plan_for(mission)

    derived = []
    for _, task in _all_tasks(plan):
        for dep in task["depends_on"]:
            derived.append((dep, task["id"]))

    edges = plan["edges"]

    assert sorted(derived) == edges, (
        f"{mission} edges do not match depends_on graph"
    )
    assert edges == sorted(edges), f"{mission} edges are not sorted lexically"


# ─── Determinism ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("fn", _PLAN_FUNCS, ids=lambda fn: fn.__name__)
def test_plan_function_is_deterministic(fn):
    first = fn()
    second = fn()
    assert first == second
    assert json.dumps(first) == json.dumps(second)


def test_plan_for_dispatches_to_named_plan_function():
    pairs = {
        "repo_audit": plan_repo_audit,
        "bug_fix": plan_bug_fix,
        "launch_readiness": plan_launch_readiness,
        "android_build_check": plan_android_build_check,
        "gateway_setup": plan_gateway_setup,
        "slack_setup": plan_slack_setup,
        "docs_only_update": plan_docs_only_update,
        "security_review": plan_security_review,
        "release_pr": plan_release_pr,
    }
    assert set(pairs) == set(MISSIONS), "test pairing drifted from MISSIONS"
    for mission, fn in pairs.items():
        assert plan_for(mission) == fn(), f"plan_for({mission!r}) drift"


def test_plan_for_unknown_mission_raises_value_error():
    with pytest.raises(ValueError, match="Unknown mission"):
        plan_for("not_a_real_mission")


# ─── Isolation / immutability ───────────────────────────────────────────────


@pytest.mark.parametrize("mission", MISSIONS)
def test_returned_plan_is_isolated_from_internal_state(mission):
    first = plan_for(mission)
    first["phases"][0]["tasks"][0]["title"] = "MUTATED"
    first["edges"].append(("x", "y"))

    second = plan_for(mission)
    assert second["phases"][0]["tasks"][0]["title"] != "MUTATED"
    assert ("x", "y") not in second["edges"]


# ─── Wave guardrails ────────────────────────────────────────────────────────


_FORBIDDEN_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+\S*(?:jobs|job_store)\S*\s+import|"
    r"import\s+\S*(?:jobs|job_store)\S*)",
    re.MULTILINE,
)


def test_task_planner_does_not_import_forbidden_modules():
    src = inspect.getsource(task_planner)
    matches = _FORBIDDEN_IMPORT_RE.findall(src)
    assert not matches, f"forbidden imports in task_planner.py: {matches}"


def test_package_init_does_not_import_forbidden_modules():
    import hermes_cli.jarvis_prime as jp

    src = inspect.getsource(jp)
    matches = _FORBIDDEN_IMPORT_RE.findall(src)
    assert not matches, f"forbidden imports in __init__.py: {matches}"


# ─── Agent / gate sanity ────────────────────────────────────────────────────


_KNOWN_AGENTS = frozenset({
    # AOS Council bench (CLAUDE.md)
    "aos-council-director",
    "evidence-architect",
    "principal-systems-architect",
    "product-experience-architect",
    "commercial-strategist",
    "assurance-risk-director",
    "delivery-scope-controller",
    "contrarian-reviewer",
    "codex-dispatch-governor",
    # JARVIS workers (docs/jarvis-prime-operating-system.md)
    "claude-code-builder",
    "codex-reviewer",
    "codex-bounded-fix-worker",
    "local-test-runner",
    "github-pr-publisher",
})


_KNOWN_GATES = frozenset({
    "planning", "build", "review", "test",
    "security", "release", "owner_approval", "rollback",
})


@pytest.mark.parametrize("mission", MISSIONS)
def test_task_agents_are_known_council_or_worker_names(mission):
    plan = plan_for(mission)
    for _, task in _all_tasks(plan):
        assert task["agent"] in _KNOWN_AGENTS, (
            f"{mission} task {task['id']} references unknown agent "
            f"{task['agent']!r}"
        )


@pytest.mark.parametrize("mission", MISSIONS)
def test_task_gates_are_known_verification_gates(mission):
    plan = plan_for(mission)
    for _, task in _all_tasks(plan):
        assert task["gate"] in _KNOWN_GATES, (
            f"{mission} task {task['id']} references unknown gate "
            f"{task['gate']!r}"
        )
