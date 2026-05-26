"""Tests for hermes_cli.memory_tree.artifacts."""

from __future__ import annotations

import pytest

from hermes_cli.memory_tree.artifacts import (
    SecretContentError,
    make_artifact,
    redact_secrets,
)


def test_artifact_id_is_deterministic():
    art1, _ = make_artifact("file://a.md", "hello world", created_at="2026-01-01T00:00:00Z")
    art2, _ = make_artifact("file://a.md", "hello world", created_at="2026-01-01T00:00:00Z")
    assert art1.artifact_id == art2.artifact_id
    assert art1.content_hash == art2.content_hash
    assert art1.artifact_id.startswith("art:")
    assert art1.content_hash.startswith("sha256:")


def test_artifact_id_changes_with_content():
    a, _ = make_artifact("file://a.md", "one", created_at="2026-01-01T00:00:00Z")
    b, _ = make_artifact("file://a.md", "two", created_at="2026-01-01T00:00:00Z")
    assert a.artifact_id != b.artifact_id


def test_artifact_id_changes_with_source():
    a, _ = make_artifact("file://a.md", "same", created_at="2026-01-01T00:00:00Z")
    b, _ = make_artifact("file://b.md", "same", created_at="2026-01-01T00:00:00Z")
    assert a.artifact_id != b.artifact_id


def test_redact_aws_access_key():
    text = "credential AKIAIOSFODNN7EXAMPLE in code"
    cleaned, tags = redact_secrets(text)
    assert "AKIA" not in cleaned
    assert "aws_access_key" in tags


def test_redact_slack_token():
    text = "token xoxb-1234567890-abcdef-XYZ here"
    cleaned, tags = redact_secrets(text)
    assert "xoxb-" not in cleaned
    assert "slack_token" in tags


def test_redact_github_token():
    text = "use ghp_" + "a" * 40 + " to clone"
    cleaned, tags = redact_secrets(text)
    assert "ghp_" not in cleaned
    assert "github_token" in tags


def test_redact_openai_key():
    text = "OPENAI_API_KEY=sk-" + "a" * 30
    cleaned, tags = redact_secrets(text)
    assert "sk-aaaa" not in cleaned
    assert "openai_key" in tags or "generic_api_key" in tags


def test_redact_anthropic_key():
    text = "ANTHROPIC=sk-ant-" + "a" * 30
    cleaned, tags = redact_secrets(text)
    assert "sk-ant-" not in cleaned
    assert "anthropic_key" in tags or "generic_api_key" in tags


def test_redact_jwt():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    cleaned, tags = redact_secrets(f"Authorization header was {jwt}")
    assert "eyJhbGciOi" not in cleaned
    assert "jwt" in tags


def test_redact_bearer_header():
    text = "Authorization: Bearer abcdef1234567890ABCDEF"
    cleaned, tags = redact_secrets(text)
    assert "Bearer abcdef" not in cleaned
    assert "bearer_header" in tags


def test_redact_pem_block():
    text = "key:\n-----BEGIN RSA PRIVATE KEY-----\nMIIEoAIBAAKCAQEA\n-----END RSA PRIVATE KEY-----\nend"
    cleaned, tags = redact_secrets(text)
    assert "BEGIN" not in cleaned
    assert "pem_private_key" in tags


def test_redact_no_secrets_leaves_text_alone():
    cleaned, tags = redact_secrets("nothing sensitive here")
    assert cleaned == "nothing sensitive here"
    assert tags == []


def test_make_artifact_records_redaction_in_provenance():
    artifact, cleaned = make_artifact(
        "file://leak.md",
        "key AKIAIOSFODNN7EXAMPLE oops",
        created_at="2026-01-01T00:00:00Z",
    )
    assert "AKIA" not in cleaned
    assert artifact.provenance.get("redactions")
    assert "aws_access_key" in artifact.provenance["redactions"]


def test_make_artifact_without_redact_raises_on_secret():
    with pytest.raises(SecretContentError):
        make_artifact(
            "file://leak.md",
            "key AKIAIOSFODNN7EXAMPLE oops",
            redact=False,
            created_at="2026-01-01T00:00:00Z",
        )


def test_make_artifact_requires_source_uri():
    with pytest.raises(ValueError):
        make_artifact("", "content")


def test_make_artifact_preserves_extra_provenance():
    artifact, _ = make_artifact(
        "file://a.md",
        "hi",
        provenance={"agent": "test"},
        created_at="2026-01-01T00:00:00Z",
    )
    assert artifact.provenance["agent"] == "test"


def test_make_artifact_byte_size_matches_cleaned():
    artifact, cleaned = make_artifact(
        "file://a.md",
        "héllo",
        created_at="2026-01-01T00:00:00Z",
    )
    assert artifact.byte_size == len(cleaned.encode("utf-8"))
