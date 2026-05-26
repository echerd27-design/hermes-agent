"""Raw artifact records and secret-redaction utilities.

Artifacts are the top-level unit ingested into the memory tree: a document,
file, job description, web page, etc. Each artifact carries its source URI,
content hash, kind, creation timestamp, and a provenance dict that records
any redactions performed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping


class SecretContentError(ValueError):
    """Raised when content contains secret-like patterns and redaction is disabled."""


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    source_uri: str
    source_path: str | None
    content_hash: str
    kind: str
    created_at: str
    byte_size: int
    title: str | None
    provenance: Mapping[str, str] = field(default_factory=dict)


# Patterns are intentionally conservative to minimise false positives while
# catching the most common token shapes. Each pattern is paired with a tag
# recorded in provenance.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws(.{0,20})?(secret|sk)[^\n]{0,5}['\"=:\s]([A-Za-z0-9/+=]{40})")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    # anthropic_key must come before openai_key — both start with `sk-` and
    # we want Anthropic-shaped tokens tagged as anthropic, not openai.
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    ("bearer_header", re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}")),
    ("generic_password", re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{6,})")),
    ("generic_api_key", re.compile(r"(?i)(api[_-]?key|apikey|secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})")),
    ("pem_private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
)


def redact_secrets(text: str) -> tuple[str, list[str]]:
    """Return (redacted_text, tags) where tags lists which patterns fired.

    Each match is replaced with `[REDACTED:<tag>]`. Tags are unique and ordered
    by first occurrence.
    """
    seen: list[str] = []
    redacted = text
    for tag, pattern in _SECRET_PATTERNS:
        def _sub(_match: re.Match[str], _tag: str = tag) -> str:
            if _tag not in seen:
                seen.append(_tag)
            return f"[REDACTED:{_tag}]"

        redacted = pattern.sub(_sub, redacted)
    return redacted, seen


def _hash_content(content: str) -> str:
    h = hashlib.sha256()
    h.update(content.encode("utf-8"))
    return f"sha256:{h.hexdigest()[:16]}"


def _artifact_id(source_uri: str, content_hash: str) -> str:
    h = hashlib.sha256()
    h.update(f"{source_uri}:{content_hash}".encode("utf-8"))
    return f"art:{h.hexdigest()[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_artifact(
    source_uri: str,
    content: str,
    *,
    source_path: str | None = None,
    kind: str = "text",
    title: str | None = None,
    provenance: Mapping[str, str] | None = None,
    redact: bool = True,
    created_at: str | None = None,
) -> tuple[Artifact, str]:
    """Build an Artifact + the (possibly redacted) content.

    Returns the artifact plus the cleaned content the caller should chunk and
    persist. If `redact=False` and content still contains secret patterns,
    raises SecretContentError to prevent leaking material into the index.
    """
    if not source_uri:
        raise ValueError("source_uri is required")

    cleaned, tags = redact_secrets(content) if redact else (content, [])

    if not redact:
        _, would_redact = redact_secrets(content)
        if would_redact:
            raise SecretContentError(
                f"content contains secret-like patterns: {would_redact!r}"
            )

    content_hash = _hash_content(cleaned)
    artifact_id = _artifact_id(source_uri, content_hash)
    prov: dict[str, str] = dict(provenance or {})
    if tags:
        prov["redactions"] = ",".join(tags)

    artifact = Artifact(
        artifact_id=artifact_id,
        source_uri=source_uri,
        source_path=source_path,
        content_hash=content_hash,
        kind=kind,
        created_at=created_at or _utc_now_iso(),
        byte_size=len(cleaned.encode("utf-8")),
        title=title,
        provenance=prov,
    )
    return artifact, cleaned
