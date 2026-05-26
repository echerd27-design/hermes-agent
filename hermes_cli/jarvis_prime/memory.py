"""JARVIS Prime memory contract — in-process policy-enforcement layer.

This module enforces the rules defined in
``docs/memory-and-personality-policy.md`` at the API boundary. It does not
persist anything. Durable persistence is owned by the plugin provider
system at ``plugins/memory/`` and is intentionally not touched by this
contract; see ``docs/aci/reports/W03_MEMORY_CONTRACT.md`` for the audit
report that accompanies this module.

What the contract enforces:

* ``durable`` vs ``session`` distinction — durable entries survive
  ``clear_session()``; session entries do not.
* Secrets (tokens, API keys, passwords, OAuth credentials, high-entropy
  strings) are rejected from durable storage and silently redacted in
  session storage and in ``summarize_for_prompt`` output.
* Stale artifact references (PR numbers, issue numbers, commit SHAs) are
  rejected from durable storage; the policy doc allows them in session
  state and task notes, so the session surface accepts them unchanged.
* Inputs marked as raw voice dumps (``[voice]`` / ``[raw_voice]`` prefix)
  are rejected from durable storage.
* ``summarize_for_prompt`` always produces output whose length is
  bounded by ``max_chars`` and applies a final redact() pass for defence
  in depth.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Literal, Optional

__all__ = [
    "MemoryRejected",
    "MemoryEntry",
    "JarvisMemory",
    "is_secret_like",
    "is_stale_artifact",
    "is_raw_voice_dump",
    "redact",
]


Kind = Literal["durable", "session"]
Category = Literal["decision", "lesson", "preference", "task_progress"]


class MemoryRejected(ValueError):
    """Raised when a value violates the durable-memory contract."""


@dataclass(frozen=True)
class MemoryEntry:
    key: str
    value: str
    kind: Kind
    category: Category
    repo: Optional[str] = None
    created_at: float = field(default_factory=time.time)


# ── Detection patterns ────────────────────────────────────────────────────
#
# Mirrors the credential-suffix filter in ``tests/conftest.py`` so the
# contract aligns with the existing hermetic test invariants. Patterns are
# compiled once at import time.

_SECRET_PREFIX_RE = re.compile(
    r"\b("
    r"sk-[A-Za-z0-9_\-]{16,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|gho_[A-Za-z0-9]{20,}"
    r"|ghu_[A-Za-z0-9]{20,}"
    r"|ghs_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|xox[abprs]-[A-Za-z0-9\-]{10,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_\-]{30,}"
    r"|hf_[A-Za-z0-9]{30,}"
    r")\b"
)

_SECRET_KEYWORD_RE = re.compile(
    r"(?i)\b(password|passwd|secret|api[_\-]?key|access[_\-]?token|auth[_\-]?token|"
    r"bearer|client[_\-]?secret|private[_\-]?key|oauth[_\-]?token)\b"
    r"\s*[:=]\s*\S+"
)

_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{8,}\b")

# High-entropy alphanumeric token: ≥32 chars, mixes letters and digits.
# The mix requirement keeps long pure-prose phrases (e.g. lowercase
# sentences without digits) from being flagged.
_HIGH_ENTROPY_RE = re.compile(
    r"\b(?=[A-Za-z0-9_\-/+]*[A-Za-z])(?=[A-Za-z0-9_\-/+]*\d)[A-Za-z0-9_\-/+]{32,}\b"
)

_STALE_PR_ISSUE_RE = re.compile(r"(?i)\b(pr|issue|fix(?:es|ed)?|close[sd]?)\s*#?\s*\d+\b")
_STALE_HASH_NUM_RE = re.compile(r"(?<![\w#])#\d+\b")
_STALE_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")

_VOICE_PREFIX_RE = re.compile(r"^\s*\[(?:voice|raw_voice|voice_dump)\b", re.IGNORECASE)


def is_secret_like(text: str) -> bool:
    """Return True if *text* looks like it contains a credential."""
    if not text:
        return False
    return bool(
        _SECRET_PREFIX_RE.search(text)
        or _SECRET_KEYWORD_RE.search(text)
        or _BEARER_RE.search(text)
        or _HIGH_ENTROPY_RE.search(text)
    )


def is_stale_artifact(text: str) -> bool:
    """Return True if *text* references a transient artifact (PR/issue/SHA).

    A bare hex string that already qualifies as a secret token is treated
    as a secret, not a stale artifact — the secret detector runs first at
    the policy gate.
    """
    if not text:
        return False
    return bool(
        _STALE_PR_ISSUE_RE.search(text)
        or _STALE_HASH_NUM_RE.search(text)
        or _STALE_SHA_RE.search(text)
    )


def is_raw_voice_dump(text: str) -> bool:
    """Return True if *text* is a raw voice transcript marked for ingestion."""
    if not text:
        return False
    return bool(_VOICE_PREFIX_RE.match(text))


def redact(text: str) -> str:
    """Replace secret-shaped substrings with ``[REDACTED]``."""
    if not text:
        return text
    out = _SECRET_PREFIX_RE.sub("[REDACTED]", text)
    out = _BEARER_RE.sub("[REDACTED]", out)
    out = _SECRET_KEYWORD_RE.sub(
        lambda m: m.group(0).split("=", 1)[0].split(":", 1)[0].rstrip() + "=[REDACTED]"
        if ("=" in m.group(0) or ":" in m.group(0))
        else "[REDACTED]",
        out,
    )
    out = _HIGH_ENTROPY_RE.sub("[REDACTED]", out)
    return out


# ── Memory store ──────────────────────────────────────────────────────────


class JarvisMemory:
    """In-process JARVIS Prime memory contract.

    Storage is two ordered lists; entries with the same ``key`` within a
    kind are replaced on re-insertion. Persistence and cross-process
    sharing are intentionally delegated to the plugin provider system
    (``plugins/memory/``) and are out of scope for this contract.
    """

    def __init__(self) -> None:
        self._durable: List[MemoryEntry] = []
        self._session: List[MemoryEntry] = []

    # ── Durable surface ───────────────────────────────────────────────

    def remember_decision(self, key: str, value: str) -> MemoryEntry:
        return self._remember_durable(key, value, category="decision")

    def remember_lesson(self, key: str, value: str, *, repo: str) -> MemoryEntry:
        if not repo:
            raise ValueError("repo-scoped lesson requires a non-empty repo name")
        return self._remember_durable(key, value, category="lesson", repo=repo)

    def remember_preference(self, key: str, value: str) -> MemoryEntry:
        return self._remember_durable(key, value, category="preference")

    # ── Session surface ───────────────────────────────────────────────

    def note_task_progress(self, key: str, value: str) -> MemoryEntry:
        self._require_nonempty(key, value)
        stored_value = redact(value) if is_secret_like(value) else value
        entry = MemoryEntry(
            key=key,
            value=stored_value,
            kind="session",
            category="task_progress",
        )
        self._upsert(self._session, entry)
        return entry

    # ── Mutations ─────────────────────────────────────────────────────

    def forget(self, key: str) -> bool:
        before = len(self._durable)
        self._durable = [e for e in self._durable if e.key != key]
        return len(self._durable) < before

    def clear_session(self) -> int:
        count = len(self._session)
        self._session = []
        return count

    # ── Reads ─────────────────────────────────────────────────────────

    def durable_items(self) -> List[MemoryEntry]:
        return list(self._durable)

    def session_items(self) -> List[MemoryEntry]:
        return list(self._session)

    # ── Prompt assembly ───────────────────────────────────────────────

    def summarize_for_prompt(self, max_chars: int = 1200) -> str:
        if max_chars <= 0:
            return ""
        parts: List[str] = []
        used = 0
        for entry in self._iter_for_summary():
            line = redact(self._format_entry(entry))
            needed = len(line) + (1 if parts else 0)
            if used + needed > max_chars:
                break
            parts.append(line)
            used += needed
        return "\n".join(parts)

    # ── Internal helpers ──────────────────────────────────────────────

    def _remember_durable(
        self,
        key: str,
        value: str,
        *,
        category: Category,
        repo: Optional[str] = None,
    ) -> MemoryEntry:
        self._require_nonempty(key, value)
        if is_secret_like(value):
            raise MemoryRejected(
                f"refusing to store secret-shaped value in durable memory (key={key!r})"
            )
        if is_raw_voice_dump(value):
            raise MemoryRejected(
                f"refusing to store raw voice dump in durable memory (key={key!r})"
            )
        if is_stale_artifact(value):
            raise MemoryRejected(
                f"refusing to store stale artifact reference in durable memory (key={key!r})"
            )
        entry = MemoryEntry(
            key=key, value=value, kind="durable", category=category, repo=repo
        )
        self._upsert(self._durable, entry)
        return entry

    @staticmethod
    def _require_nonempty(key: str, value: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("memory key must be a non-empty string")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("memory value must be a non-empty string")

    @staticmethod
    def _upsert(bucket: List[MemoryEntry], entry: MemoryEntry) -> None:
        for i, existing in enumerate(bucket):
            if existing.key == entry.key:
                bucket[i] = entry
                return
        bucket.append(entry)

    def _iter_for_summary(self) -> Iterator[MemoryEntry]:
        yield from self._durable
        yield from self._session

    @staticmethod
    def _format_entry(entry: MemoryEntry) -> str:
        scope = f"({entry.repo})" if entry.repo else ""
        return f"[{entry.kind}:{entry.category}]{scope} {entry.key}: {entry.value}"
