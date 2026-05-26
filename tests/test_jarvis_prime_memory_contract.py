"""Contract tests for ``hermes_cli.jarvis_prime.memory``.

These tests verify the policy boundary described in
``docs/aci/reports/W03_MEMORY_CONTRACT.md``: durable vs session
separation, secret rejection/redaction, stale-artifact rejection, raw
voice-dump rejection, and bounded ``summarize_for_prompt`` output.

The tests are hermetic — no fixtures beyond pytest defaults. The
existing ``tests/conftest.py`` strips credential env vars and isolates
HERMES_HOME for every test, which is enough.
"""

from __future__ import annotations

import pytest

from hermes_cli.jarvis_prime import memory as mem
from hermes_cli.jarvis_prime.memory import (
    JarvisMemory,
    MemoryRejected,
    is_raw_voice_dump,
    is_secret_like,
    is_stale_artifact,
    redact,
)


# ── Durable vs session ────────────────────────────────────────────────────


class TestDurableVsSession:
    def test_decision_survives_clear_session(self):
        m = JarvisMemory()
        m.remember_decision("project_focus", "ship JARVIS Prime memory contract")
        m.note_task_progress("current_step", "writing the tests")

        cleared = m.clear_session()

        assert cleared == 1
        assert [e.key for e in m.durable_items()] == ["project_focus"]
        assert m.session_items() == []

    def test_durable_and_session_buckets_are_disjoint(self):
        m = JarvisMemory()
        m.remember_decision("k", "durable value")
        m.note_task_progress("k", "session note about the same key")

        durable = m.durable_items()
        session = m.session_items()

        assert len(durable) == 1 and durable[0].kind == "durable"
        assert len(session) == 1 and session[0].kind == "session"
        assert durable[0].value == "durable value"
        assert session[0].value == "session note about the same key"

    def test_forget_removes_only_named_durable_entry(self):
        m = JarvisMemory()
        m.remember_decision("a", "first")
        m.remember_decision("b", "second")
        m.note_task_progress("a", "session entry should remain")

        assert m.forget("a") is True
        remaining = {e.key for e in m.durable_items()}
        assert remaining == {"b"}
        assert {e.key for e in m.session_items()} == {"a"}

    def test_forget_returns_false_when_key_missing(self):
        m = JarvisMemory()
        assert m.forget("never_stored") is False

    def test_upsert_replaces_value_for_same_key(self):
        m = JarvisMemory()
        m.remember_preference("style", "concise")
        m.remember_preference("style", "concise and mobile-friendly")
        items = m.durable_items()
        assert len(items) == 1
        assert items[0].value == "concise and mobile-friendly"


# ── Secret rejection / redaction ──────────────────────────────────────────


SECRET_SAMPLES = [
    "sk-abcdef0123456789abcdef0123456789",
    "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    "AKIAIOSFODNN7EXAMPLE",
    "Bearer abcdefghijklmnop123",
    "password=hunter2",
    "api_key: AIzaSyA-1234567890abcdefghijklmnopqrstuv",
    "AAAAB3NzaC1yc2EAAAADAQABAAABAQDexample0123456789",
]


class TestSecretRejection:
    @pytest.mark.parametrize("value", SECRET_SAMPLES)
    def test_is_secret_like_detects(self, value):
        assert is_secret_like(value) is True

    def test_is_secret_like_allows_prose(self):
        assert is_secret_like("Jeremiah prefers concise responses while moving") is False
        assert is_secret_like("Use mobile-friendly mode after 9pm") is False
        assert is_secret_like("") is False

    @pytest.mark.parametrize("value", SECRET_SAMPLES)
    def test_durable_decision_rejects_secret(self, value):
        m = JarvisMemory()
        with pytest.raises(MemoryRejected):
            m.remember_decision("k", value)
        assert m.durable_items() == []

    @pytest.mark.parametrize("value", SECRET_SAMPLES)
    def test_durable_lesson_rejects_secret(self, value):
        m = JarvisMemory()
        with pytest.raises(MemoryRejected):
            m.remember_lesson("k", value, repo="hermes-agent")

    @pytest.mark.parametrize("value", SECRET_SAMPLES)
    def test_durable_preference_rejects_secret(self, value):
        m = JarvisMemory()
        with pytest.raises(MemoryRejected):
            m.remember_preference("k", value)

    def test_session_redacts_secret_silently(self):
        secret = "sk-abcdef0123456789abcdef0123456789"
        m = JarvisMemory()
        entry = m.note_task_progress("k", f"deployed using token {secret}")
        assert "[REDACTED]" in entry.value
        assert secret not in entry.value

    def test_redact_replaces_known_patterns(self):
        out = redact("auth header: Bearer abcdefghijklmnop123 and password=hunter2")
        assert "Bearer abcdefghijklmnop123" not in out
        assert "hunter2" not in out
        assert "[REDACTED]" in out

    def test_redact_on_empty_string(self):
        assert redact("") == ""


# ── Stale-artifact rejection ──────────────────────────────────────────────


STALE_SAMPLES = [
    "PR #123 fixed the issue",
    "issue #456 is the blocker",
    "see #789 for context",
    "rebased onto abcdef1 yesterday",
    "merged commit 1a2b3c4 into main",
    "fixes #42",
]


class TestStaleArtifactRejection:
    @pytest.mark.parametrize("value", STALE_SAMPLES)
    def test_is_stale_artifact_detects(self, value):
        assert is_stale_artifact(value) is True

    def test_is_stale_artifact_allows_prose(self):
        assert is_stale_artifact("Use Python 3.11 with uv 0.4.18") is False
        assert is_stale_artifact("Prefers mobile-friendly responses") is False
        assert is_stale_artifact("") is False

    @pytest.mark.parametrize("value", STALE_SAMPLES)
    def test_durable_rejects_stale_artifact(self, value):
        m = JarvisMemory()
        with pytest.raises(MemoryRejected):
            m.remember_decision("k", value)

    @pytest.mark.parametrize("value", STALE_SAMPLES)
    def test_session_accepts_stale_artifact_unchanged(self, value):
        m = JarvisMemory()
        entry = m.note_task_progress("step", value)
        assert entry.value == value


# ── Raw voice-dump rejection ──────────────────────────────────────────────


VOICE_SAMPLES = [
    "[voice] uh so I was thinking we should refactor the gateway and then",
    "[VOICE] late-night brain dump about routing",
    "[raw_voice] long unstructured ramble",
    "[voice_dump] mumbling about the spec",
]


class TestRawVoiceRejection:
    @pytest.mark.parametrize("value", VOICE_SAMPLES)
    def test_is_raw_voice_dump_detects(self, value):
        assert is_raw_voice_dump(value) is True

    def test_is_raw_voice_dump_allows_prose(self):
        assert is_raw_voice_dump("voice memo idea: support haptic feedback") is False
        assert is_raw_voice_dump("") is False

    @pytest.mark.parametrize("value", VOICE_SAMPLES)
    def test_durable_rejects_voice_dump(self, value):
        m = JarvisMemory()
        with pytest.raises(MemoryRejected):
            m.remember_decision("k", value)

    def test_session_accepts_voice_dump(self):
        m = JarvisMemory()
        entry = m.note_task_progress("dump", "[voice] thinking out loud")
        assert entry.value.startswith("[voice]")


# ── summarize_for_prompt ──────────────────────────────────────────────────


class TestSummarizeForPrompt:
    def test_empty_memory_returns_empty_string(self):
        assert JarvisMemory().summarize_for_prompt() == ""

    def test_output_is_bounded_by_max_chars(self):
        m = JarvisMemory()
        for i in range(50):
            m.remember_decision(f"key_{i}", f"decision number {i} with extra context to push length")
        for i in range(50):
            m.note_task_progress(f"task_{i}", f"in-progress note {i}")

        for budget in (50, 200, 400, 1200):
            out = m.summarize_for_prompt(max_chars=budget)
            assert len(out) <= budget, f"budget={budget} produced len={len(out)}"

    def test_durable_entries_appear_before_session(self):
        m = JarvisMemory()
        m.remember_decision("dur_first", "durable decision A")
        m.remember_preference("dur_second", "user preference B")
        m.note_task_progress("sess_first", "session note C")

        out = m.summarize_for_prompt(max_chars=1200)
        i_dur = out.index("durable decision A")
        i_pref = out.index("user preference B")
        i_sess = out.index("session note C")
        assert i_dur < i_sess
        assert i_pref < i_sess

    def test_secret_in_session_value_is_redacted_in_summary(self):
        secret = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        m = JarvisMemory()
        m.note_task_progress("deploy", f"token was {secret}")
        out = m.summarize_for_prompt(max_chars=1200)
        assert secret not in out
        assert "[REDACTED]" in out

    def test_zero_budget_returns_empty(self):
        m = JarvisMemory()
        m.remember_decision("k", "v")
        assert m.summarize_for_prompt(max_chars=0) == ""

    def test_entry_repo_scope_appears_in_output(self):
        m = JarvisMemory()
        m.remember_lesson("never_amend_main", "always create a new commit", repo="hermes-agent")
        out = m.summarize_for_prompt(max_chars=1200)
        assert "(hermes-agent)" in out


# ── Repo-scoped lessons ──────────────────────────────────────────────────


class TestRepoScopedLessons:
    def test_lesson_stores_repo(self):
        m = JarvisMemory()
        entry = m.remember_lesson(
            "test_runner",
            "use scripts/run_tests.sh as canonical entry point",
            repo="hermes-agent",
        )
        assert entry.repo == "hermes-agent"
        assert entry.category == "lesson"
        assert entry.kind == "durable"

    def test_lesson_requires_repo_kwarg(self):
        m = JarvisMemory()
        with pytest.raises(TypeError):
            m.remember_lesson("k", "v")  # type: ignore[call-arg]

    def test_lesson_rejects_empty_repo(self):
        m = JarvisMemory()
        with pytest.raises(ValueError):
            m.remember_lesson("k", "v", repo="")


# ── Input validation ──────────────────────────────────────────────────────


class TestInputValidation:
    @pytest.mark.parametrize("method", ["remember_decision", "remember_preference", "note_task_progress"])
    def test_empty_key_rejected(self, method):
        m = JarvisMemory()
        with pytest.raises(ValueError):
            getattr(m, method)("", "value")

    @pytest.mark.parametrize("method", ["remember_decision", "remember_preference", "note_task_progress"])
    def test_empty_value_rejected(self, method):
        m = JarvisMemory()
        with pytest.raises(ValueError):
            getattr(m, method)("key", "")

    def test_module_exports_public_surface(self):
        assert {
            "MemoryRejected",
            "MemoryEntry",
            "JarvisMemory",
            "is_secret_like",
            "is_stale_artifact",
            "is_raw_voice_dump",
            "redact",
        }.issubset(set(mem.__all__))
