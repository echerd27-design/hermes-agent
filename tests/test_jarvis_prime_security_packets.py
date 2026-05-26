"""Validation tests for the JARVIS Prime security gate fixtures.

These tests pin the shape and safety invariants of the fake "security packet"
fixtures under ``tests/fixtures/jarvis_security_packets/``. They use the
existing pytest infrastructure only (stdlib + the autouse fixtures in
``tests/conftest.py``) and do not import any JARVIS or gateway runtime.

The eight required categories track the ``docs/jarvis-verification-gates.md``
Security Gate definition and the Wave 12 task list.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "jarvis_security_packets"

REQUIRED_CATEGORIES = frozenset(
    {
        "secret_added",
        "env_edit",
        "dependency_changed",
        "network_call_added",
        "owner_gated_deploy",
        "app_store_submission",
        "public_posting",
        "dns_change",
    }
)

REQUIRED_KEYS = frozenset(
    {
        "packet_id",
        "category",
        "gate",
        "expected_decision",
        "owner_approval_required",
        "summary",
        "fake",
        "change",
        "rationale",
        "safety_markers",
    }
)

VALID_DECISIONS = frozenset({"pass", "fail", "owner_approval"})

# High-confidence secret patterns. A hit here means the fixture contains
# something that looks like a real credential and the test must fail.
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ASIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"gho_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
)

# Long opaque hex / base64-looking strings without a safety marker are suspicious.
SUSPICIOUS_OPAQUE = re.compile(r"\b[A-Fa-f0-9]{32,}\b")
SAFE_MARKER_TOKENS = ("EXAMPLE", "FAKE", "DO-NOT-USE", "0000")

# URL hosts that are safe to reference. The Security Gate fixtures must never
# point at a real third-party service.
ALLOWED_HOST_SUFFIXES = (
    "example.com",
    "example.org",
    "example.net",
    "example.invalid",
    "localhost",
)
ALLOWED_HOST_LITERALS = frozenset({"127.0.0.1", "::1"})
RFC1918_PREFIXES = ("10.", "192.168.")
# 172.16.0.0/12 prefix check is done numerically below.
URL_PATTERN = re.compile(r"https?://([A-Za-z0-9._\-:\[\]]+)")


def _fixture_files() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.json"))


def _host_is_allowed(host: str) -> bool:
    host = host.lower().split(":", 1)[0]
    if host in ALLOWED_HOST_LITERALS:
        return True
    if any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOST_SUFFIXES):
        return True
    if host.startswith(RFC1918_PREFIXES):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    # TEST-NET ranges from RFC 5737 are also documentation-safe.
    if host.startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
        return True
    return False


def test_fixtures_directory_exists() -> None:
    assert FIXTURES_DIR.is_dir(), f"Missing fixtures directory: {FIXTURES_DIR}"
    assert _fixture_files(), "No fixture JSON files found"


def test_category_coverage_matches_task_list() -> None:
    found = {json.loads(p.read_text(encoding="utf-8"))["category"] for p in _fixture_files()}
    assert found == REQUIRED_CATEGORIES, (
        f"Fixture category set drifted from the Wave 12 task list. "
        f"Missing: {sorted(REQUIRED_CATEGORIES - found)}; "
        f"Extra: {sorted(found - REQUIRED_CATEGORIES)}"
    )


@pytest.mark.parametrize(
    "fixture_path",
    _fixture_files(),
    ids=lambda p: p.stem,
)
def test_fixture_shape_and_safety(fixture_path: Path) -> None:
    raw = fixture_path.read_text(encoding="utf-8")
    packet = json.loads(raw)

    assert isinstance(packet, dict), "fixture must be a JSON object"
    missing = REQUIRED_KEYS - packet.keys()
    assert not missing, f"missing required keys: {sorted(missing)}"

    assert packet["fake"] is True, "fixture must declare itself fake"
    assert packet["gate"] == "Security Gate", "fixture must target the Security Gate"
    assert packet["category"] in REQUIRED_CATEGORIES, (
        f"unknown category {packet['category']!r}"
    )
    assert packet["expected_decision"] in VALID_DECISIONS, (
        f"invalid expected_decision {packet['expected_decision']!r}"
    )

    assert isinstance(packet["owner_approval_required"], bool)
    if packet["expected_decision"] == "owner_approval":
        assert packet["owner_approval_required"] is True, (
            "owner_approval decision must set owner_approval_required=true"
        )

    assert isinstance(packet["safety_markers"], list) and packet["safety_markers"], (
        "safety_markers must be a non-empty list"
    )
    for marker in packet["safety_markers"]:
        assert isinstance(marker, str) and marker, "safety_markers entries must be non-empty strings"

    change = packet["change"]
    assert isinstance(change, dict)
    assert isinstance(change.get("path"), str) and change["path"], "change.path required"
    assert isinstance(change.get("kind"), str) and change["kind"], "change.kind required"

    # Safety: no real-looking secrets anywhere in the serialized fixture.
    for pattern in SECRET_PATTERNS:
        match = pattern.search(raw)
        assert match is None, (
            f"fixture matches secret-like pattern {pattern.pattern!r}: {match.group(0)!r}"
        )

    # Long opaque hex strings are only allowed if accompanied by a safety marker.
    for match in SUSPICIOUS_OPAQUE.finditer(raw):
        token = match.group(0)
        if not any(marker in token for marker in SAFE_MARKER_TOKENS):
            pytest.fail(
                f"opaque hex/base64-looking token without safety marker: {token!r}"
            )

    # Safety: any URL must point at a reserved/test host.
    for match in URL_PATTERN.finditer(raw):
        host = match.group(1)
        assert _host_is_allowed(host), (
            f"URL host {host!r} is not in the allowed reserved/test set"
        )


@pytest.mark.parametrize(
    "fixture_path",
    _fixture_files(),
    ids=lambda p: p.stem,
)
def test_fixture_packet_id_matches_filename(fixture_path: Path) -> None:
    packet = json.loads(fixture_path.read_text(encoding="utf-8"))
    expected = "w12-" + fixture_path.stem.replace("_", "-")
    assert packet["packet_id"] == expected, (
        f"packet_id {packet['packet_id']!r} does not match expected {expected!r}"
    )
