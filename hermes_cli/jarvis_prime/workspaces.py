"""ACI product workspace schema for JARVIS Prime.

Each ACI product (Nourish, HazMat Command, Hey Jay, Hermes Core,
ACI Internal) is described by a :class:`Workspace`: a frozen,
serializable record that pins down repo identity, build/test/deploy
commands, the risk rules JARVIS must respect, the default specialist
bench, the memory namespace, and the release checklist.

The module is a leaf — stdlib only, no Hermes imports — so later waves
(routing, memory, release gates) can depend on it without circular
imports and so it survives ``python -m compileall`` on its own.

Built-in templates are exposed via :func:`list_workspace_templates`,
:func:`get_workspace_template`, and
:func:`create_workspace_from_template`. The registry is the source of
truth; callers that need a customized workspace should derive one with
``create_workspace_from_template`` rather than mutating a template.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields, replace
from typing import Any, Optional

__all__ = [
    "Workspace",
    "list_workspace_templates",
    "get_workspace_template",
    "create_workspace_from_template",
]


_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_NAMESPACE_RE = re.compile(r"^[a-z0-9][a-z0-9/_-]*$")


def _coerce_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise ValueError(
            f"{field_name} must be an iterable of strings, not a single string"
        )
    if not isinstance(value, Iterable):
        raise ValueError(f"{field_name} must be an iterable of strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} entries must be strings")
        out.append(item)
    return tuple(out)


@dataclass(frozen=True)
class Workspace:
    """A single ACI product workspace.

    All collection-shaped fields are tuples so the record is hashable
    and safe to share across threads; serialization converts them to
    lists for JSON friendliness.
    """

    workspace_id: str
    product_name: str
    repo_full_name: Optional[str] = None
    product_brief: str = ""
    default_branch: str = "main"
    build_commands: tuple[str, ...] = ()
    test_commands: tuple[str, ...] = ()
    deploy_commands: tuple[str, ...] = ()
    risk_rules: tuple[str, ...] = ()
    specialists: tuple[str, ...] = ()
    memory_namespace: str = ""
    release_checklist: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, str) or not self.workspace_id:
            raise ValueError("workspace_id must be a non-empty string")
        if not _SLUG_RE.match(self.workspace_id):
            raise ValueError(
                "workspace_id must be a lowercase slug "
                "matching ^[a-z0-9][a-z0-9-]*$ "
                f"(got {self.workspace_id!r})"
            )
        if not isinstance(self.product_name, str) or not self.product_name.strip():
            raise ValueError("product_name must be a non-empty string")
        if self.repo_full_name is not None and (
            not isinstance(self.repo_full_name, str) or "/" not in self.repo_full_name
        ):
            raise ValueError(
                "repo_full_name must be 'owner/repo' or None "
                f"(got {self.repo_full_name!r})"
            )
        if not isinstance(self.default_branch, str) or not self.default_branch:
            raise ValueError("default_branch must be a non-empty string")
        if not isinstance(self.memory_namespace, str) or not self.memory_namespace:
            raise ValueError("memory_namespace must be a non-empty string")
        if not _NAMESPACE_RE.match(self.memory_namespace):
            raise ValueError(
                "memory_namespace must match ^[a-z0-9][a-z0-9/_-]*$ "
                f"(got {self.memory_namespace!r})"
            )
        # Tuple-of-str invariants — these are normally guaranteed by
        # from_dict/_coerce_tuple, but the dataclass constructor lets a
        # caller pass arbitrary values, so we check here too.
        for field_name in (
            "build_commands",
            "test_commands",
            "deploy_commands",
            "risk_rules",
            "specialists",
            "release_checklist",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, tuple):
                raise ValueError(f"{field_name} must be a tuple of strings")
            for item in value:
                if not isinstance(item, str):
                    raise ValueError(f"{field_name} entries must be strings")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict (tuples become lists)."""
        return {
            "workspace_id": self.workspace_id,
            "product_name": self.product_name,
            "repo_full_name": self.repo_full_name,
            "product_brief": self.product_brief,
            "default_branch": self.default_branch,
            "build_commands": list(self.build_commands),
            "test_commands": list(self.test_commands),
            "deploy_commands": list(self.deploy_commands),
            "risk_rules": list(self.risk_rules),
            "specialists": list(self.specialists),
            "memory_namespace": self.memory_namespace,
            "release_checklist": list(self.release_checklist),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Workspace":
        """Rebuild a Workspace from a plain mapping.

        Unknown keys are ignored so the schema can grow without
        breaking existing payloads. Missing required keys raise
        ``ValueError``.
        """
        if not isinstance(data, Mapping):
            raise ValueError("from_dict expects a mapping")
        required = {"workspace_id", "product_name", "memory_namespace"}
        missing = sorted(required - set(data.keys()))
        if missing:
            raise ValueError(
                f"missing required workspace fields: {', '.join(missing)}"
            )
        tuple_fields = {
            "build_commands",
            "test_commands",
            "deploy_commands",
            "risk_rules",
            "specialists",
            "release_checklist",
        }
        kwargs: dict[str, Any] = {}
        known = {f.name for f in fields(cls)}
        for key, value in data.items():
            if key not in known:
                continue
            if key in tuple_fields:
                kwargs[key] = _coerce_tuple(value, key)
            else:
                kwargs[key] = value
        return cls(**kwargs)


_TEMPLATES: dict[str, Workspace] = {
    "nourish": Workspace(
        workspace_id="nourish",
        product_name="Nourish",
        repo_full_name=None,
        product_brief=(
            "Personalized nutrition guidance that explains why a meal "
            "suggestion fits the user's goals without making medical claims."
        ),
        default_branch="main",
        build_commands=(),
        test_commands=(),
        deploy_commands=(),
        risk_rules=(
            "no medical claims",
            "no diagnosis or treatment language",
            "explain the why behind every recommendation",
            "respect user dietary restrictions on every suggestion",
        ),
        specialists=(
            "Nourish Product Specialist",
            "Product UX Reviewer",
            "Contrarian Reviewer",
            "Memory Evidence Curator",
        ),
        memory_namespace="aci/nourish",
        release_checklist=(
            "review every user-facing string for medical claim risk",
            "confirm dietary-restriction guards still apply",
            "snapshot recommendation explainers for the audit log",
            "tag the release in the Nourish memory namespace",
        ),
    ),
    "hazmat-command": Workspace(
        workspace_id="hazmat-command",
        product_name="HazMat Command",
        repo_full_name=None,
        product_brief=(
            "Shipping paper OCR and HazMat compliance command center: "
            "captures confidence scores, preserves the correction trail, "
            "and records who approved each correction."
        ),
        default_branch="main",
        build_commands=(),
        test_commands=(),
        deploy_commands=(),
        risk_rules=(
            "preserve audit trail on every OCR correction",
            "never silently overwrite a shipping paper field",
            "record reviewer identity for every approved correction",
            "no production HazMat data in test fixtures",
        ),
        specialists=(
            "HazMat Command Specialist",
            "Security / Compliance Reviewer",
            "QA Release Gate",
            "Memory Evidence Curator",
        ),
        memory_namespace="aci/hazmat-command",
        release_checklist=(
            "verify OCR confidence threshold unchanged or reviewed",
            "confirm correction audit trail still writes",
            "run compliance regression on sample shipping papers",
            "tag the release in the HazMat memory namespace",
            "update the reviewer-identity log retention policy if changed",
        ),
    ),
    "hey-jay": Workspace(
        workspace_id="hey-jay",
        product_name="Hey Jay",
        repo_full_name=None,
        product_brief=(
            "Voice-first driver assistant that warns truck drivers before "
            "low bridges and proposes truck-safe alternatives instead of "
            "generic map reroutes."
        ),
        default_branch="main",
        build_commands=(),
        test_commands=(),
        deploy_commands=(),
        risk_rules=(
            "never suppress low-clearance warnings",
            "never propose a route that ignores known truck restrictions",
            "voice prompts must be short and unambiguous while driving",
            "no route data may be cached past the trip without consent",
        ),
        specialists=(
            "Product UX Reviewer",
            "Logistics Domain Specialist",
            "Contrarian Reviewer",
            "Principal Systems Architect",
        ),
        memory_namespace="aci/hey-jay",
        release_checklist=(
            "regression test low-clearance detection on the known-route corpus",
            "verify voice prompts stay under the cognitive-load budget",
            "confirm truck-safe alternatives are reachable",
            "tag the release in the Hey Jay memory namespace",
        ),
    ),
    "hermes-core": Workspace(
        workspace_id="hermes-core",
        product_name="Hermes Core",
        repo_full_name="echerd27-design/hermes-agent",
        product_brief=(
            "The Hermes agent runtime and CLI itself: agent loop, tools, "
            "skills, plugins, terminal backends, and the JARVIS Prime / AOS "
            "planning layer that rides on top."
        ),
        default_branch="main",
        build_commands=(
            "python -m compileall hermes_cli",
        ),
        test_commands=(
            "scripts/run_tests.sh",
        ),
        deploy_commands=(),
        risk_rules=(
            "no breaking changes to the public CLI without a deprecation notice",
            "no secrets in code, logs, docs, tests, or fixtures",
            "every change needs tests or a written reason tests were skipped",
            "respect the AGENTS.md hermetic-test invariants",
        ),
        specialists=(
            "Principal Systems Architect",
            "Security / Compliance Reviewer",
            "QA Release Gate",
            "Contrarian Reviewer",
            "Memory Evidence Curator",
        ),
        memory_namespace="aci/hermes-core",
        release_checklist=(
            "scripts/run_tests.sh is green",
            "python -m compileall hermes_cli exits 0",
            "AGENTS.md and CLAUDE.md still describe current behavior",
            "no forbidden files touched by the diff",
            "draft PR opened, never merged directly to main",
        ),
    ),
    "aci-internal": Workspace(
        workspace_id="aci-internal",
        product_name="ACI Internal",
        repo_full_name=None,
        product_brief=(
            "ACI's internal tooling: wave reports, planning artifacts, "
            "council orchestration glue, and the cross-product registry "
            "JARVIS Prime uses to route work between Nourish, HazMat "
            "Command, Hey Jay, and Hermes Core."
        ),
        default_branch="main",
        build_commands=(),
        test_commands=(),
        deploy_commands=(),
        risk_rules=(
            "no production data in test fixtures",
            "no customer PII in wave reports",
            "no secrets in committed planning artifacts",
            "every wave stays inside its declared ALLOWED FILES list",
        ),
        specialists=(
            "AOS Council Director",
            "Delivery Scope Controller",
            "Evidence Architect",
            "Contrarian Reviewer",
        ),
        memory_namespace="aci/aci-internal",
        release_checklist=(
            "wave report exists under docs/aci/reports/",
            "ALLOWED / FORBIDDEN file contract honored",
            "draft PR opened with rollback note",
            "no cross-wave file overlap",
        ),
    ),
}


def list_workspace_templates() -> tuple[str, ...]:
    """Return the built-in workspace ids in sorted order."""
    return tuple(sorted(_TEMPLATES.keys()))


def get_workspace_template(workspace_id: str) -> Workspace:
    """Return the built-in template for *workspace_id*.

    Raises :class:`KeyError` with the list of valid ids on miss.
    Templates are frozen, so the returned instance is safe to share.
    """
    try:
        return _TEMPLATES[workspace_id]
    except KeyError as exc:
        valid = ", ".join(list_workspace_templates())
        raise KeyError(
            f"unknown workspace template {workspace_id!r}; valid ids: {valid}"
        ) from exc


def create_workspace_from_template(
    workspace_id: str, **overrides: Any
) -> Workspace:
    """Derive a customized :class:`Workspace` from a built-in template.

    The built-in template is never mutated; ``dataclasses.replace`` is
    used to produce a fresh frozen instance with *overrides* applied.
    """
    base = get_workspace_template(workspace_id)
    tuple_fields = {
        "build_commands",
        "test_commands",
        "deploy_commands",
        "risk_rules",
        "specialists",
        "release_checklist",
    }
    coerced: dict[str, Any] = {}
    for key, value in overrides.items():
        if key in tuple_fields:
            coerced[key] = _coerce_tuple(value, key)
        else:
            coerced[key] = value
    return replace(base, **coerced)
