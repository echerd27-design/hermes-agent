"""Tests for the ACI product workspace schema (Wave 13)."""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

from hermes_cli.jarvis_prime import (
    Workspace,
    create_workspace_from_template,
    get_workspace_template,
    list_workspace_templates,
)
from hermes_cli.jarvis_prime import workspaces as workspaces_module


EXPECTED_TEMPLATE_IDS = (
    "aci-internal",
    "hazmat-command",
    "hermes-core",
    "hey-jay",
    "nourish",
)


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------


def test_lists_five_templates():
    assert list_workspace_templates() == EXPECTED_TEMPLATE_IDS


@pytest.mark.parametrize("workspace_id", EXPECTED_TEMPLATE_IDS)
def test_get_template_basic_shape(workspace_id):
    ws = get_workspace_template(workspace_id)
    assert isinstance(ws, Workspace)
    assert ws.workspace_id == workspace_id
    assert ws.product_name.strip()
    assert ws.memory_namespace == f"aci/{workspace_id}"
    assert ws.specialists, "every template must declare at least one specialist"
    assert ws.default_branch == "main"


def test_nourish_template_has_medical_claim_guard():
    ws = get_workspace_template("nourish")
    assert ws.product_name == "Nourish"
    assert any("medical" in rule.lower() for rule in ws.risk_rules)


def test_hazmat_template_preserves_audit_trail():
    ws = get_workspace_template("hazmat-command")
    assert ws.product_name == "HazMat Command"
    assert any("audit" in rule.lower() for rule in ws.risk_rules)


def test_hey_jay_template_protects_low_clearance_warnings():
    ws = get_workspace_template("hey-jay")
    assert ws.product_name == "Hey Jay"
    assert any("low-clearance" in rule.lower() for rule in ws.risk_rules)


def test_hermes_core_template_points_at_repo():
    ws = get_workspace_template("hermes-core")
    assert ws.product_name == "Hermes Core"
    assert ws.repo_full_name == "echerd27-design/hermes-agent"
    assert "scripts/run_tests.sh" in ws.test_commands


def test_aci_internal_template_keeps_internal_scope():
    ws = get_workspace_template("aci-internal")
    assert ws.product_name == "ACI Internal"
    assert any("PII" in rule or "production data" in rule for rule in ws.risk_rules)


def test_unknown_template_raises_with_valid_ids_listed():
    with pytest.raises(KeyError) as excinfo:
        get_workspace_template("does-not-exist")
    msg = str(excinfo.value)
    for valid in EXPECTED_TEMPLATE_IDS:
        assert valid in msg


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def _base_kwargs(**overrides):
    kwargs = {
        "workspace_id": "demo",
        "product_name": "Demo",
        "memory_namespace": "aci/demo",
    }
    kwargs.update(overrides)
    return kwargs


def test_workspace_id_must_be_slug_lowercase():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(workspace_id="Demo"))


def test_workspace_id_rejects_spaces():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(workspace_id="my demo"))


def test_workspace_id_rejects_leading_hyphen():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(workspace_id="-demo"))


def test_workspace_id_required():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(workspace_id=""))


def test_product_name_required():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(product_name=""))


def test_product_name_whitespace_only_rejected():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(product_name="   "))


def test_memory_namespace_required():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(memory_namespace=""))


def test_repo_full_name_must_be_owner_repo_or_none():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(repo_full_name="not-a-slash-pair"))


def test_tuple_field_rejects_non_string_entry():
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(risk_rules=("ok", 7)))


def test_tuple_field_rejects_plain_list_when_constructed_directly():
    # Direct construction should pass a tuple; from_dict coerces, but
    # the dataclass itself is strict so downstream callers can rely on
    # the tuple invariant.
    with pytest.raises(ValueError):
        Workspace(**_base_kwargs(risk_rules=["ok"]))


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("workspace_id", EXPECTED_TEMPLATE_IDS)
def test_to_dict_is_json_safe(workspace_id):
    ws = get_workspace_template(workspace_id)
    payload = ws.to_dict()
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["workspace_id"] == workspace_id
    # tuples must become lists for JSON
    assert isinstance(decoded["risk_rules"], list)
    assert isinstance(decoded["specialists"], list)


@pytest.mark.parametrize("workspace_id", EXPECTED_TEMPLATE_IDS)
def test_from_dict_round_trips(workspace_id):
    ws = get_workspace_template(workspace_id)
    rebuilt = Workspace.from_dict(ws.to_dict())
    assert rebuilt == ws


def test_from_dict_ignores_unknown_keys():
    ws = get_workspace_template("nourish")
    payload = ws.to_dict()
    payload["future_field_introduced_in_wave_99"] = "ignored"
    rebuilt = Workspace.from_dict(payload)
    assert rebuilt == ws


def test_from_dict_missing_required_raises():
    payload = {"product_name": "Demo", "memory_namespace": "aci/demo"}
    with pytest.raises(ValueError) as excinfo:
        Workspace.from_dict(payload)
    assert "workspace_id" in str(excinfo.value)


def test_from_dict_rejects_non_mapping():
    with pytest.raises(ValueError):
        Workspace.from_dict(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_from_dict_coerces_lists_to_tuples():
    payload = {
        "workspace_id": "demo",
        "product_name": "Demo",
        "memory_namespace": "aci/demo",
        "risk_rules": ["one", "two"],
    }
    ws = Workspace.from_dict(payload)
    assert ws.risk_rules == ("one", "two")


# ---------------------------------------------------------------------------
# Derivation via create_workspace_from_template
# ---------------------------------------------------------------------------


def test_create_from_template_applies_overrides():
    derived = create_workspace_from_template(
        "nourish",
        repo_full_name="echerd27-design/nourish",
        default_branch="develop",
    )
    assert derived.repo_full_name == "echerd27-design/nourish"
    assert derived.default_branch == "develop"
    # original template untouched
    original = get_workspace_template("nourish")
    assert original.repo_full_name is None
    assert original.default_branch == "main"


def test_create_from_template_coerces_list_overrides():
    derived = create_workspace_from_template(
        "hey-jay",
        risk_rules=["new rule one", "new rule two"],
    )
    assert derived.risk_rules == ("new rule one", "new rule two")


def test_create_from_template_returns_frozen_instance():
    derived = create_workspace_from_template("hermes-core")
    with pytest.raises(dataclasses.FrozenInstanceError):
        derived.default_branch = "develop"  # type: ignore[misc]


def test_create_from_template_unknown_id_raises():
    with pytest.raises(KeyError):
        create_workspace_from_template("does-not-exist")


# ---------------------------------------------------------------------------
# Stdlib-only guard
# ---------------------------------------------------------------------------


_STDLIB_WHITELIST = {
    "dataclasses",
    "typing",
    "re",
    "json",
    "copy",
    "collections",
    "collections.abc",
    "__future__",
}


def _iter_top_level_imports(source: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            # node.module is None for `from . import x`; we don't
            # currently use relative imports, but guard anyway.
            if node.module is not None:
                yield node.module


def test_module_imports_only_stdlib():
    module_path = Path(workspaces_module.__file__)
    source = module_path.read_text(encoding="utf-8")
    for module_name in _iter_top_level_imports(source):
        root = module_name.split(".")[0]
        assert (
            module_name in _STDLIB_WHITELIST or root in _STDLIB_WHITELIST
        ), (
            f"workspaces.py imports non-stdlib module {module_name!r}; "
            "Wave 13 must stay stdlib-only with no external calls."
        )


def test_package_import_has_no_external_calls():
    # The whitelist also has to hold for the package __init__, which
    # only re-exports from the workspaces module.
    init_path = Path(workspaces_module.__file__).parent / "__init__.py"
    source = init_path.read_text(encoding="utf-8")
    for module_name in _iter_top_level_imports(source):
        root = module_name.split(".")[0]
        # The package __init__ imports from hermes_cli.jarvis_prime.workspaces
        # itself, which is fine — it's the leaf module under test.
        if root == "hermes_cli":
            continue
        assert (
            module_name in _STDLIB_WHITELIST or root in _STDLIB_WHITELIST
        ), f"__init__.py imports non-stdlib module {module_name!r}"
