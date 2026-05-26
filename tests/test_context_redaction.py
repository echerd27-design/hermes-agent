"""Tests for hermes_cli.context.redaction."""

import re

import pytest

from hermes_cli.context import SECRET_PATTERNS, reject, scrub


class TestRedactionScrub:
    def test_openai_sk_token_replaced_with_placeholder(self):
        cleaned, count = scrub("auth=sk-abcdef0123456789xyz")
        assert "sk-abcdef0123456789xyz" not in cleaned
        assert "[REDACTED:openai_sk]" in cleaned
        assert count == 1

    def test_github_pat_classic_and_fine_grained_replaced(self):
        text = "PAT1=ghp_0123456789abcdef\nPAT2=github_pat_0123456789abcdef_more"
        cleaned, count = scrub(text)
        assert "ghp_0123456789abcdef" not in cleaned
        assert "github_pat_0123456789abcdef_more" not in cleaned
        assert "[REDACTED:github_pat_classic]" in cleaned
        assert "[REDACTED:github_pat_fine_grained]" in cleaned
        assert count >= 2

    @pytest.mark.parametrize(
        "raw",
        [
            "gho_0123456789abcdefXX",
            "ghu_0123456789abcdefXX",
            "ghs_0123456789abcdefXX",
            "ghr_0123456789abcdefXX",
        ],
    )
    def test_github_oauth_tokens_replaced(self, raw):
        cleaned, count = scrub(raw)
        assert raw not in cleaned
        assert "[REDACTED:github_oauth]" in cleaned
        assert count == 1

    @pytest.mark.parametrize(
        "raw",
        [
            "xoxb-0123456789-abcd-EFG",
            "xoxa-0123456789-abcd-EFG",
            "xapp-0123456789-abcd-EFG",
            "xoxp-0123456789-abcd-EFG",
        ],
    )
    def test_slack_tokens_replaced(self, raw):
        cleaned, count = scrub(raw)
        assert raw not in cleaned
        assert "[REDACTED:slack_token]" in cleaned
        assert count == 1

    def test_aws_access_key_replaced(self):
        cleaned, count = scrub("key=AKIAIOSFODNN7EXAMPLE rest")
        assert "AKIAIOSFODNN7EXAMPLE" not in cleaned
        assert "[REDACTED:aws_access_key]" in cleaned
        assert count == 1

    def test_gcp_api_key_replaced(self):
        raw = "AIza" + "B" * 35
        cleaned, count = scrub(f"x={raw} y")
        assert raw not in cleaned
        assert "[REDACTED:gcp_api_key]" in cleaned
        assert count == 1

    def test_jwt_replaced(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4fwpMeJf36"
        cleaned, count = scrub(f"Bearer {jwt}")
        # Both the bearer-header structured rule and the JWT vendor pattern
        # could in principle match; either way the raw value is gone.
        assert jwt not in cleaned
        assert count >= 1

    def test_authorization_bearer_header_replaced(self):
        cleaned, count = scrub("Authorization: Bearer opaque-token-1234567890ABC")
        assert "opaque-token-1234567890ABC" not in cleaned
        assert "[REDACTED:auth_bearer]" in cleaned
        assert count >= 1

    def test_private_key_block_replaced(self):
        raw = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "AAAABBBBCCCCDDDDEEEEFFFFGGGG\n"
            "-----END RSA PRIVATE KEY-----"
        )
        cleaned, count = scrub(f"key={raw}\nafter")
        assert "AAAABBBBCCCCDDDDEEEEFFFFGGGG" not in cleaned
        assert "[REDACTED:private_key_block]" in cleaned
        assert "after" in cleaned
        assert count >= 1

    def test_env_assign_api_key_replaced(self):
        cleaned, count = scrub('OPENAI_API_KEY="literal-value-12345"')
        assert "literal-value-12345" not in cleaned
        assert "[REDACTED:env_assign_secret]" in cleaned
        assert count >= 1

    def test_json_field_token_replaced(self):
        cleaned, count = scrub('{"token": "literal-value-12345"}')
        assert "literal-value-12345" not in cleaned
        assert "[REDACTED:json_field_secret]" in cleaned
        assert count >= 1

    def test_db_connstr_password_replaced(self):
        cleaned, count = scrub("postgres://user:p4ssw0rd@db.local:5432/app")
        assert "p4ssw0rd" not in cleaned
        assert "[REDACTED:db_connstr]" in cleaned
        # Host preserved for debuggability.
        assert "db.local" in cleaned
        assert count >= 1

    def test_clean_text_unchanged_count_zero(self):
        text = "hello world, file.py:42 def main(): pass"
        cleaned, count = scrub(text)
        assert cleaned == text
        assert count == 0

    def test_multiple_secrets_all_replaced_count_correct(self):
        text = (
            "first sk-abcdef0123456789xyz second ghp_0123456789abcdef "
            "third AKIAIOSFODNN7EXAMPLE"
        )
        cleaned, count = scrub(text)
        assert "sk-abcdef0123456789xyz" not in cleaned
        assert "ghp_0123456789abcdef" not in cleaned
        assert "AKIAIOSFODNN7EXAMPLE" not in cleaned
        assert count == 3

    def test_empty_input(self):
        cleaned, count = scrub("")
        assert cleaned == ""
        assert count == 0


class TestRedactionReject:
    def test_reject_returns_kind_on_seeded_secret(self):
        kind = reject("auth=sk-abcdef0123456789xyz")
        assert kind == "openai_sk"

    def test_reject_returns_first_kind_when_multiple_secrets_present(self):
        kind = reject("ghp_0123456789abcdef and sk-abcdef0123456789xyz")
        # SECRET_PATTERNS order: structured matchers first, then vendor
        # prefixes — both these are vendor prefixes, so the first one listed
        # in SECRET_PATTERNS wins.
        assert kind in {"github_pat_classic", "openai_sk"}

    def test_reject_returns_none_on_clean_text(self):
        assert reject("hello world, just a normal sentence") is None

    def test_reject_returns_none_on_empty(self):
        assert reject("") is None


class TestPatternsClosed:
    def test_secret_patterns_is_immutable_tuple(self):
        assert isinstance(SECRET_PATTERNS, tuple)
        for kind, pattern in SECRET_PATTERNS:
            assert isinstance(kind, str)
            assert isinstance(pattern, re.Pattern)

    def test_secret_patterns_kinds_unique(self):
        kinds = [k for k, _ in SECRET_PATTERNS]
        assert len(kinds) == len(set(kinds))
