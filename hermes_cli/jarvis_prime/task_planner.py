"""Deterministic task graph planner for common ACI Hermes / JARVIS Prime missions.

Produces pure-data task graphs for nine named missions:

    repo_audit, bug_fix, launch_readiness, android_build_check,
    gateway_setup, slack_setup, docs_only_update, security_review, release_pr

Each plan separates four phases: builder, reviewer, tester, owner_approval.
Tasks reference AOS Council bench agents (see ``CLAUDE.md``) and JARVIS
verification gates (see ``docs/jarvis-verification-gates.md``).

The module is stdlib-only, performs no I/O, makes no LLM calls, and is
fully deterministic: ``plan_for(m) == plan_for(m)`` for every supported
mission ``m``. Downstream consumers (job store, scheduler) read the
output; this module never imports them.
"""

from __future__ import annotations

PHASE_ORDER = ("builder", "reviewer", "tester", "owner_approval")

SCHEMA_VERSION = "1.0"


# ─── Mission templates ──────────────────────────────────────────────────────
#
# Each template is a tuple of:
#   (mission_key, summary, ((phase_name, ((slug, title, agent, gate,
#                                          depends_on_slugs), ...)), ...))
#
# ``depends_on_slugs`` references task slugs in the same plan; the builder
# below expands them to fully-qualified ids of the form
# ``{mission}.{phase}.{slug}``. Cross-phase references use
# ``{phase}/{slug}`` so the resolver can locate the target task.

_REPO_AUDIT = (
    "repo_audit",
    "Audit repository for AOS and JARVIS readiness.",
    (
        ("builder", (
            ("evidence", "Gather repo evidence bundle",
             "evidence-architect", "planning", ()),
            ("inventory", "Inventory agents, skills, commands, plugins",
             "claude-code-builder", "build", ("evidence",)),
        )),
        ("reviewer", (
            ("synthesis", "Synthesize audit findings",
             "contrarian-reviewer", "review", ("builder/inventory",)),
            ("gaps", "Flag registry and routing gaps",
             "codex-reviewer", "review", ("builder/inventory",)),
        )),
        ("tester", (
            ("verify", "Run AOS and JARVIS verification scripts",
             "local-test-runner", "test", ("reviewer/gaps",)),
        )),
        ("owner_approval", (
            ("signoff", "Owner accepts audit report",
             "aos-council-director", "owner_approval",
             ("reviewer/synthesis", "tester/verify")),
        )),
    ),
)

_BUG_FIX = (
    "bug_fix",
    "Reproduce, patch, review, and merge a bug fix.",
    (
        ("builder", (
            ("repro", "Reproduce the bug and capture evidence",
             "evidence-architect", "planning", ()),
            ("patch", "Author the fix",
             "claude-code-builder", "build", ("repro",)),
        )),
        ("reviewer", (
            ("diff", "Review the diff",
             "codex-reviewer", "review", ("builder/patch",)),
            ("regression", "Surface regression risk",
             "contrarian-reviewer", "review", ("builder/patch",)),
        )),
        ("tester", (
            ("unit", "Run unit tests",
             "local-test-runner", "test", ("builder/patch",)),
            ("targeted", "Run targeted regression tests",
             "local-test-runner", "test", ("builder/patch",)),
        )),
        ("owner_approval", (
            ("merge", "Owner approves merge",
             "aos-council-director", "owner_approval",
             ("reviewer/diff", "reviewer/regression",
              "tester/unit", "tester/targeted")),
        )),
    ),
)

_LAUNCH_READINESS = (
    "launch_readiness",
    "Confirm repository is ready to ship.",
    (
        ("builder", (
            ("checklist", "Assemble launch checklist",
             "delivery-scope-controller", "planning", ()),
            ("evidence", "Collect launch evidence bundle",
             "evidence-architect", "build", ("checklist",)),
        )),
        ("reviewer", (
            ("risk", "Risk and compliance review",
             "assurance-risk-director", "review", ("builder/evidence",)),
            ("contrarian", "Contrarian readiness review",
             "contrarian-reviewer", "review", ("builder/evidence",)),
        )),
        ("tester", (
            ("full_suite", "Run full test suite and smoke tests",
             "local-test-runner", "test", ("builder/checklist",)),
        )),
        ("owner_approval", (
            ("release_gate", "Owner clears the release gate",
             "aos-council-director", "release",
             ("reviewer/risk", "reviewer/contrarian", "tester/full_suite")),
        )),
    ),
)

_ANDROID_BUILD_CHECK = (
    "android_build_check",
    "Verify the Android client builds and passes smoke checks.",
    (
        ("builder", (
            ("manifest", "Validate Gradle and manifest configuration",
             "claude-code-builder", "planning", ()),
            ("compile", "Compile the debug APK",
             "claude-code-builder", "build", ("manifest",)),
        )),
        ("reviewer", (
            ("lint", "Review lint and dependency drift",
             "codex-reviewer", "review", ("builder/compile",)),
        )),
        ("tester", (
            ("apk_smoke", "Install APK and run smoke harness",
             "local-test-runner", "test", ("builder/compile",)),
        )),
        ("owner_approval", (
            ("signoff", "Owner approves build artifact",
             "aos-council-director", "owner_approval",
             ("reviewer/lint", "tester/apk_smoke")),
        )),
    ),
)

_GATEWAY_SETUP = (
    "gateway_setup",
    "Configure and verify a Hermes gateway adapter.",
    (
        ("builder", (
            ("config", "Design gateway configuration",
             "principal-systems-architect", "planning", ()),
            ("wire", "Wire the adapter implementation",
             "claude-code-builder", "build", ("config",)),
        )),
        ("reviewer", (
            ("security_audit", "Audit network and credential surface",
             "assurance-risk-director", "security", ("builder/wire",)),
            ("diff", "Review the adapter diff",
             "codex-reviewer", "review", ("builder/wire",)),
        )),
        ("tester", (
            ("health_probe", "Probe gateway health endpoints",
             "local-test-runner", "test", ("builder/wire",)),
        )),
        ("owner_approval", (
            ("network_signoff", "Owner authorizes network exposure",
             "aos-council-director", "owner_approval",
             ("reviewer/security_audit", "reviewer/diff",
              "tester/health_probe")),
        )),
    ),
)

_SLACK_SETUP = (
    "slack_setup",
    "Install and authorize the Hermes Slack integration.",
    (
        ("builder", (
            ("app_manifest", "Author the Slack app manifest",
             "claude-code-builder", "planning", ()),
            ("auth", "Wire Slack OAuth and store credentials",
             "claude-code-builder", "build", ("app_manifest",)),
        )),
        ("reviewer", (
            ("scope_review", "Review requested OAuth scopes",
             "assurance-risk-director", "security", ("builder/auth",)),
        )),
        ("tester", (
            ("webhook_probe", "Send a probe message and confirm delivery",
             "local-test-runner", "test", ("builder/auth",)),
        )),
        ("owner_approval", (
            ("oauth_signoff", "Owner authorizes workspace install",
             "aos-council-director", "owner_approval",
             ("reviewer/scope_review", "tester/webhook_probe")),
        )),
    ),
)

_DOCS_ONLY_UPDATE = (
    "docs_only_update",
    "Author or revise repository documentation without runtime change.",
    (
        ("builder", (
            ("draft", "Draft the documentation update",
             "evidence-architect", "planning", ()),
            ("edit", "Apply the doc edits",
             "claude-code-builder", "build", ("draft",)),
        )),
        ("reviewer", (
            ("coherence", "Review for clarity and coherence",
             "contrarian-reviewer", "review", ("builder/edit",)),
        )),
        ("tester", (
            ("links", "Validate links and code samples",
             "local-test-runner", "test", ("builder/edit",)),
        )),
        ("owner_approval", (
            ("merge", "Owner approves merge",
             "aos-council-director", "owner_approval",
             ("reviewer/coherence", "tester/links")),
        )),
    ),
)

_SECURITY_REVIEW = (
    "security_review",
    "Conduct a security review of the pending changes.",
    (
        ("builder", (
            ("scope", "Scope the review and threat surface",
             "assurance-risk-director", "planning", ()),
            ("surface_map", "Map the attack surface and inputs",
             "evidence-architect", "build", ("scope",)),
        )),
        ("reviewer", (
            ("threat_model", "Build a threat model and rank objections",
             "contrarian-reviewer", "security", ("builder/surface_map",)),
            ("audit", "Audit credentials, secrets, and dependencies",
             "assurance-risk-director", "security", ("builder/surface_map",)),
        )),
        ("tester", (
            ("scanners", "Run security scanners",
             "local-test-runner", "test", ("builder/surface_map",)),
        )),
        ("owner_approval", (
            ("risk_signoff", "Owner acknowledges remaining risk",
             "aos-council-director", "owner_approval",
             ("reviewer/threat_model", "reviewer/audit", "tester/scanners")),
        )),
    ),
)

_RELEASE_PR = (
    "release_pr",
    "Prepare and publish a release pull request.",
    (
        ("builder", (
            ("notes", "Draft release notes and changelog",
             "delivery-scope-controller", "planning", ()),
            ("branch", "Prepare the release branch",
             "github-pr-publisher", "build", ("notes",)),
        )),
        ("reviewer", (
            ("diff", "Review the release diff",
             "codex-reviewer", "review", ("builder/branch",)),
            ("contrarian", "Contrarian review of release scope",
             "contrarian-reviewer", "review", ("builder/branch",)),
        )),
        ("tester", (
            ("ci", "Confirm continuous integration is green",
             "local-test-runner", "test", ("builder/branch",)),
        )),
        ("owner_approval", (
            ("publish", "Owner authorizes tag and publish",
             "aos-council-director", "release",
             ("reviewer/diff", "reviewer/contrarian", "tester/ci")),
        )),
    ),
)


_TEMPLATES = (
    _REPO_AUDIT,
    _BUG_FIX,
    _LAUNCH_READINESS,
    _ANDROID_BUILD_CHECK,
    _GATEWAY_SETUP,
    _SLACK_SETUP,
    _DOCS_ONLY_UPDATE,
    _SECURITY_REVIEW,
    _RELEASE_PR,
)


MISSIONS = tuple(template[0] for template in _TEMPLATES)


_TEMPLATES_BY_MISSION = {template[0]: template for template in _TEMPLATES}


# ─── Plan construction ──────────────────────────────────────────────────────


def _resolve_dependency(mission, phase, dep_token):
    """Expand a dependency token into a fully-qualified task id.

    A bare slug (``"evidence"``) is treated as a same-phase reference.
    A ``"phase/slug"`` token is a cross-phase reference.
    """
    if "/" in dep_token:
        dep_phase, dep_slug = dep_token.split("/", 1)
        return f"{mission}.{dep_phase}.{dep_slug}"
    return f"{mission}.{phase}.{dep_token}"


def _build_plan(template):
    mission, summary, phase_specs = template

    phases = []
    edges = []

    for phase_name, task_specs in phase_specs:
        tasks = []
        for slug, title, agent, gate, dep_tokens in task_specs:
            task_id = f"{mission}.{phase_name}.{slug}"
            depends_on = [
                _resolve_dependency(mission, phase_name, token)
                for token in dep_tokens
            ]
            tasks.append({
                "id": task_id,
                "title": title,
                "role": phase_name,
                "agent": agent,
                "gate": gate,
                "depends_on": depends_on,
            })
            for dep in depends_on:
                edges.append((dep, task_id))
        phases.append({"name": phase_name, "tasks": tasks})

    edges.sort()

    return {
        "mission": mission,
        "version": SCHEMA_VERSION,
        "summary": summary,
        "phase_order": PHASE_ORDER,
        "phases": phases,
        "edges": edges,
    }


# ─── Public plan functions ──────────────────────────────────────────────────


def plan_repo_audit():
    return _build_plan(_REPO_AUDIT)


def plan_bug_fix():
    return _build_plan(_BUG_FIX)


def plan_launch_readiness():
    return _build_plan(_LAUNCH_READINESS)


def plan_android_build_check():
    return _build_plan(_ANDROID_BUILD_CHECK)


def plan_gateway_setup():
    return _build_plan(_GATEWAY_SETUP)


def plan_slack_setup():
    return _build_plan(_SLACK_SETUP)


def plan_docs_only_update():
    return _build_plan(_DOCS_ONLY_UPDATE)


def plan_security_review():
    return _build_plan(_SECURITY_REVIEW)


def plan_release_pr():
    return _build_plan(_RELEASE_PR)


def plan_for(mission):
    """Return the plan for ``mission``. Raises ``ValueError`` if unknown."""
    template = _TEMPLATES_BY_MISSION.get(mission)
    if template is None:
        supported = ", ".join(MISSIONS)
        raise ValueError(
            f"Unknown mission {mission!r}. Supported missions: {supported}."
        )
    return _build_plan(template)
