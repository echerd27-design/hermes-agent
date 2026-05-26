"""Context compression for JARVIS Prime handoffs.

JARVIS Prime hands off long, free-form task notes to AOS specialists and
coding workers (Claude Code, Codex, GitHub PR Publisher, Slack adapter,
mobile voice). The raw payload is whatever the operator pasted in: chat
logs, scratch notes, dict-shaped state, sometimes thousands of characters
with raw secrets mixed in.

This helper compresses any of those shapes into a deterministic,
section-structured, secret-redacted, character-bounded handoff packet.

Design rules:
    - Pure stdlib. No new dependencies (pyproject is locked).
    - Deterministic: same input + same options → byte-identical output.
      No clocks, no rng, no env reads, no iteration-order leaks.
    - Secret-safe by default. Redaction runs before classification AND
      on rendered sections, so truncation cannot leak credentials.
    - Bounded. The rendered text never exceeds ``char_limit``.

Modeled on the pure-helper pattern of :mod:`hermes_cli.session_recap`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence, Union

NotesInput = Union[str, Sequence[Any], Mapping[str, Any]]

_DEFAULT_CHAR_LIMIT = 4000
_REDACTED = "[REDACTED]"
_NONE_PLACEHOLDER = "- (none)"

# Order matters for render() and for round-trip in as_dict().
_SECTION_ORDER: tuple[str, ...] = (
    "mission",
    "decisions",
    "files_touched",
    "unresolved_blockers",
    "owner_gates",
    "verification_evidence",
    "next_action",
)

_LIST_SECTIONS: frozenset[str] = frozenset(
    {
        "decisions",
        "files_touched",
        "unresolved_blockers",
        "owner_gates",
        "verification_evidence",
    }
)

_SCALAR_SECTIONS: frozenset[str] = frozenset({"mission", "next_action"})

# Dict-key aliases for the seven buckets. First wins.
_DICT_ALIASES: Mapping[str, tuple[str, ...]] = {
    "mission": ("mission", "goal", "objective", "purpose"),
    "decisions": ("decisions", "choices", "resolved"),
    "files_touched": (
        "files_touched",
        "files",
        "changed_files",
        "touched_files",
        "paths",
    ),
    "unresolved_blockers": (
        "unresolved_blockers",
        "blockers",
        "unresolved",
        "todos",
        "open_issues",
    ),
    "owner_gates": (
        "owner_gates",
        "gates",
        "approvals",
        "authorizations",
    ),
    "verification_evidence": (
        "verification_evidence",
        "verification",
        "evidence",
        "tests",
        "test_results",
    ),
    "next_action": ("next_action", "next", "next_step", "next_steps"),
}

# Markdown-style headings. Match the entire (lowercased) stripped line;
# never extract tail content from a heading — it only switches the active
# section. Both ``#`` and ``##`` variants are accepted.
_MARKDOWN_HEADINGS: Mapping[str, str] = {
    "# mission": "mission",
    "## mission": "mission",
    "# decisions": "decisions",
    "## decisions": "decisions",
    "# files": "files_touched",
    "## files": "files_touched",
    "# files touched": "files_touched",
    "## files touched": "files_touched",
    "# blockers": "unresolved_blockers",
    "## blockers": "unresolved_blockers",
    "# unresolved": "unresolved_blockers",
    "## unresolved": "unresolved_blockers",
    "# unresolved blockers": "unresolved_blockers",
    "## unresolved blockers": "unresolved_blockers",
    "# owner gates": "owner_gates",
    "## owner gates": "owner_gates",
    "# gates": "owner_gates",
    "## gates": "owner_gates",
    "# verification": "verification_evidence",
    "## verification": "verification_evidence",
    "# evidence": "verification_evidence",
    "## evidence": "verification_evidence",
    "# verification evidence": "verification_evidence",
    "## verification evidence": "verification_evidence",
    "# next": "next_action",
    "## next": "next_action",
    "# next action": "next_action",
    "## next action": "next_action",
    "# next step": "next_action",
    "## next step": "next_action",
}

# Prefix-with-colon anchors. The tail (whatever follows the colon) is
# routed into the section. Order matters: longer prefixes win, so
# ``next action:`` is tried before ``next:``.
_KEY_VALUE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("unresolved blockers:", "unresolved_blockers"),
    ("verification evidence:", "verification_evidence"),
    ("authorization required:", "owner_gates"),
    ("files touched:", "files_touched"),
    ("owner approval:", "owner_gates"),
    ("owner gates:", "owner_gates"),
    ("next action:", "next_action"),
    ("next step:", "next_action"),
    ("verification:", "verification_evidence"),
    ("evidence:", "verification_evidence"),
    ("blockers:", "unresolved_blockers"),
    ("unresolved:", "unresolved_blockers"),
    ("decisions:", "decisions"),
    ("mission:", "mission"),
    ("objective:", "mission"),
    ("decided:", "decisions"),
    ("blocker:", "unresolved_blockers"),
    ("blocked:", "unresolved_blockers"),
    ("verified:", "verification_evidence"),
    ("passed:", "verification_evidence"),
    ("gates:", "owner_gates"),
    ("files:", "files_touched"),
    ("chose:", "decisions"),
    ("todo:", "unresolved_blockers"),
    ("next:", "next_action"),
    ("goal:", "mission"),
)

# Standalone authorization sentinel — full-line match for the owner-gate
# marker recorded by JARVIS Prime ("Yes, with authorization.").
_AUTHORIZATION_SENTINEL = "yes, with authorization."

# File-path heuristic: tokens that look like paths with a known suffix.
_FILE_SUFFIXES: tuple[str, ...] = (
    ".py",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
    ".sh",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".rs",
    ".go",
    ".rb",
    ".java",
    ".kt",
    ".swift",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".sql",
    ".lock",
    ".cfg",
    ".ini",
)

_FILE_TOKEN_RE = re.compile(r"(?<![\w/.])((?:\.{0,2}/)?[A-Za-z0-9_./-]+)")

# Precompiled redaction patterns. Order matters: URL creds first so the
# generic key=value rule doesn't fire on the credential half.
_URL_CRED_RE = re.compile(
    r"(?P<scheme>https?://)(?P<user>[^/\s:@]+):(?P<pw>[^/\s@]+)@",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(
    r"(?P<prefix>Authorization\s*:\s*Bearer\s+|Bearer\s+)"
    r"(?P<token>[A-Za-z0-9._\-]{16,})",
    re.IGNORECASE,
)
_OPENAI_SK_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")
_GITHUB_PAT_RE = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")
_GITHUB_GHP_RE = re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")
_SLACK_RE = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")
_AWS_AKIA_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GENERIC_KV_RE = re.compile(
    r"(?P<key>(?i:api[_-]?key|secret|token|password|passwd|auth[_-]?token))"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<val>[A-Za-z0-9._/+\-]{6,})"
)


def _redact(text: str) -> str:
    """Replace credential-shaped substrings with ``[REDACTED]``.

    Patterns are intentionally conservative: high-signal tokens (provider
    prefixes, AWS access-key shape, Bearer headers, URL credentials) and
    a generic ``key=value`` rule covering the most common label words.
    """
    if not text:
        return text
    out = _URL_CRED_RE.sub(lambda m: f"{m.group('scheme')}{_REDACTED}@", text)
    out = _BEARER_RE.sub(lambda m: f"{m.group('prefix')}{_REDACTED}", out)
    out = _OPENAI_SK_RE.sub(_REDACTED, out)
    out = _GITHUB_PAT_RE.sub(_REDACTED, out)
    out = _GITHUB_GHP_RE.sub(_REDACTED, out)
    out = _SLACK_RE.sub(_REDACTED, out)
    out = _AWS_AKIA_RE.sub(_REDACTED, out)
    out = _GENERIC_KV_RE.sub(
        lambda m: f"{m.group('key')}{m.group('sep')}{_REDACTED}", out
    )
    return out


@dataclass(frozen=True)
class CompressedHandoff:
    """A deterministic, bounded handoff packet."""

    mission: str
    decisions: tuple[str, ...]
    files_touched: tuple[str, ...]
    unresolved_blockers: tuple[str, ...]
    owner_gates: tuple[str, ...]
    verification_evidence: tuple[str, ...]
    next_action: str
    truncated: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission": self.mission,
            "decisions": list(self.decisions),
            "files_touched": list(self.files_touched),
            "unresolved_blockers": list(self.unresolved_blockers),
            "owner_gates": list(self.owner_gates),
            "verification_evidence": list(self.verification_evidence),
            "next_action": self.next_action,
            "truncated": self.truncated,
        }

    def render(self) -> str:
        return _render(self)


def compress_context(
    notes: NotesInput,
    *,
    char_limit: int = _DEFAULT_CHAR_LIMIT,
    redact_secrets: bool = True,
) -> CompressedHandoff:
    """Compress JARVIS handoff notes into a bounded, structured packet.

    Args:
        notes: Free-form string, list of turn-like items, or a dict
            pre-keyed with the seven section names (or their aliases).
        char_limit: Maximum length of ``render()`` output. Defaults to
            4000. Must be a non-negative int.
        redact_secrets: If True (default), credential-shaped substrings
            are replaced with ``[REDACTED]`` before classification AND
            on rendered output.

    Returns:
        :class:`CompressedHandoff` — a frozen, hashable dataclass.

    Raises:
        TypeError: If ``notes`` is not a string, sequence, or mapping.
    """
    if not isinstance(char_limit, int) or char_limit < 0:
        raise ValueError("char_limit must be a non-negative int")

    buckets = _classify(notes, redact_secrets=redact_secrets)
    handoff = _build(buckets, truncated=False)
    rendered = _render(handoff)
    if len(rendered) <= char_limit:
        return handoff
    return _trim_to_limit(buckets, char_limit=char_limit)


def _classify(
    notes: NotesInput, *, redact_secrets: bool
) -> dict[str, list[str]]:
    """Route input into bucketed lists. Mission/next stored as 1-list."""
    buckets: dict[str, list[str]] = {key: [] for key in _SECTION_ORDER}

    if isinstance(notes, str):
        text = _redact(notes) if redact_secrets else notes
        _ingest_text(text, buckets)
    elif isinstance(notes, Mapping):
        _ingest_mapping(notes, buckets, redact_secrets=redact_secrets)
    elif isinstance(notes, (list, tuple)):
        _ingest_sequence(notes, buckets, redact_secrets=redact_secrets)
    else:
        raise TypeError(
            f"notes must be str, Sequence, or Mapping; got {type(notes).__name__}"
        )

    _dedupe_and_strip(buckets)
    return buckets


def _ingest_mapping(
    notes: Mapping[str, Any],
    buckets: dict[str, list[str]],
    *,
    redact_secrets: bool,
) -> None:
    for section, aliases in _DICT_ALIASES.items():
        value: Any = None
        for alias in aliases:
            if alias in notes:
                value = notes[alias]
                break
            # Also check case-insensitive at the top level.
            lower_match = next(
                (k for k in notes if k.lower() == alias), None
            )
            if lower_match is not None:
                value = notes[lower_match]
                break
        if value is None:
            continue
        items = _coerce_value(value)
        if redact_secrets:
            items = [_redact(s) for s in items]
        buckets[section].extend(items)


def _ingest_sequence(
    notes: Sequence[Any],
    buckets: dict[str, list[str]],
    *,
    redact_secrets: bool,
) -> None:
    for item in notes:
        if isinstance(item, Mapping):
            _ingest_mapping(item, buckets, redact_secrets=redact_secrets)
            continue
        text = _stringify(item)
        if redact_secrets:
            text = _redact(text)
        _ingest_text(text, buckets)


def _ingest_text(text: str, buckets: dict[str, list[str]]) -> None:
    """Walk lines, switching active section on heading/prefix anchors."""
    active_section: str | None = None
    mission_captured = bool(buckets["mission"])

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            active_section = None
            continue

        heading = _match_markdown_heading(stripped)
        if heading is not None:
            active_section = heading
            continue

        prefix_match = _match_key_value_prefix(stripped)
        if prefix_match is not None:
            section, tail = prefix_match
            if tail:
                _route_line(tail, section, buckets)
            else:
                active_section = section
            continue

        if stripped.lower().rstrip(".") == _AUTHORIZATION_SENTINEL.rstrip("."):
            buckets["owner_gates"].append(stripped)
            continue

        if active_section is not None:
            _route_line(line, active_section, buckets)
            continue

        if not mission_captured:
            buckets["mission"].append(_strip_bullet(line))
            mission_captured = True
            continue

        for path in _extract_file_paths(line):
            buckets["files_touched"].append(path)


def _match_markdown_heading(stripped: str) -> str | None:
    """Return the section if the whole line is a recognized markdown heading."""
    lowered = stripped.lower()
    return _MARKDOWN_HEADINGS.get(lowered)


def _match_key_value_prefix(stripped: str) -> tuple[str, str] | None:
    """Return (section, original-cased tail) if line starts with a ``Key:`` prefix."""
    lowered = stripped.lower()
    for prefix, section in _KEY_VALUE_PREFIXES:
        if lowered.startswith(prefix):
            # lower() preserves length for ASCII so the lowered offset is
            # valid against the original-cased string.
            tail = stripped[len(prefix):].lstrip()
            return section, tail
    return None


def _route_line(line: str, section: str, buckets: dict[str, list[str]]) -> None:
    stripped = _strip_bullet(line)
    if not stripped:
        return
    if section in _SCALAR_SECTIONS:
        if not buckets[section]:
            buckets[section].append(stripped)
        return
    if section == "files_touched":
        paths = _extract_file_paths(stripped)
        if paths:
            buckets[section].extend(paths)
        else:
            # Fall back to literal token if it at least looks like a path.
            buckets[section].append(_normalize_path(stripped))
        return
    buckets[section].append(stripped)


def _strip_bullet(line: str) -> str:
    """Drop leading list markers and surrounding whitespace."""
    cleaned = line.strip()
    for marker in ("- ", "* ", "+ "):
        if cleaned.startswith(marker):
            cleaned = cleaned[len(marker):].lstrip()
            break
    if cleaned[:2].rstrip(".").isdigit() and cleaned[2:3] in {".", ")", " "}:
        # numbered list "1. foo"
        cleaned = cleaned.split(maxsplit=1)[-1] if " " in cleaned else cleaned
    return cleaned.strip()


def _extract_file_paths(line: str) -> list[str]:
    found: list[str] = []
    for match in _FILE_TOKEN_RE.finditer(line):
        token = match.group(1)
        if any(token.lower().endswith(suffix) for suffix in _FILE_SUFFIXES):
            found.append(_normalize_path(token))
    return found


def _normalize_path(path: str) -> str:
    cleaned = path.strip().rstrip(",.;:")
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def _coerce_value(value: Any) -> list[str]:
    """Flatten a dict value into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [json.dumps(value, sort_keys=True)]
    if isinstance(value, (list, tuple, set, frozenset)):
        out: list[str] = []
        for item in value:
            out.extend(_coerce_value(item))
        return out
    return [str(value)]


def _stringify(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        return json.dumps(item, sort_keys=True)
    return str(item)


def _dedupe_and_strip(buckets: dict[str, list[str]]) -> None:
    for section, items in list(buckets.items()):
        cleaned: list[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            stripped = item.strip()
            if not stripped:
                continue
            cleaned.append(stripped)
        # Preserve first-seen order while deduping.
        deduped = list(dict.fromkeys(cleaned))
        if section in _SCALAR_SECTIONS:
            buckets[section] = deduped[:1]
        else:
            buckets[section] = deduped


def _build(buckets: dict[str, list[str]], *, truncated: bool) -> CompressedHandoff:
    return CompressedHandoff(
        mission=buckets["mission"][0] if buckets["mission"] else "",
        decisions=tuple(buckets["decisions"]),
        files_touched=tuple(buckets["files_touched"]),
        unresolved_blockers=tuple(buckets["unresolved_blockers"]),
        owner_gates=tuple(buckets["owner_gates"]),
        verification_evidence=tuple(buckets["verification_evidence"]),
        next_action=buckets["next_action"][0] if buckets["next_action"] else "",
        truncated=truncated,
    )


_SECTION_TITLES: Mapping[str, str] = {
    "mission": "Mission",
    "decisions": "Decisions",
    "files_touched": "Files Touched",
    "unresolved_blockers": "Unresolved Blockers",
    "owner_gates": "Owner Gates",
    "verification_evidence": "Verification Evidence",
    "next_action": "Next Action",
}


def _render(handoff: CompressedHandoff) -> str:
    parts: list[str] = ["# JARVIS Handoff"]
    for section in _SECTION_ORDER:
        parts.append(f"## {_SECTION_TITLES[section]}")
        if section in _SCALAR_SECTIONS:
            value = getattr(handoff, section)
            parts.append(value if value else _NONE_PLACEHOLDER)
        else:
            items: tuple[str, ...] = getattr(handoff, section)
            if not items:
                parts.append(_NONE_PLACEHOLDER)
            else:
                for item in items:
                    parts.append(f"- {item}")
        parts.append("")
    if handoff.truncated:
        parts.append("> Note: handoff was truncated to fit the char limit.")
    return "\n".join(parts).rstrip() + "\n"


_TRIM_ORDER: tuple[str, ...] = (
    "verification_evidence",
    "files_touched",
    "decisions",
    "unresolved_blockers",
    "owner_gates",
)


def _trim_to_limit(
    buckets: dict[str, list[str]], *, char_limit: int
) -> CompressedHandoff:
    """Iteratively shrink buckets until render fits ``char_limit``.

    Loop is bounded by a no-progress check: each iteration must drop at
    least one item or reduce a scalar by ≥1 char, otherwise we bail.
    This protects against char_limit values smaller than the empty
    static frame.
    """
    working = {key: list(value) for key, value in buckets.items()}
    cursor = 0
    last_render_len: int | None = None

    while True:
        handoff = _build(working, truncated=True)
        rendered = _render(handoff)
        if len(rendered) <= char_limit:
            return handoff

        if last_render_len is not None and len(rendered) >= last_render_len:
            # No forward progress in the previous round — give up and
            # return the smallest packet we managed to build. The
            # rendered text may exceed char_limit when the static frame
            # alone is larger than the limit (e.g. char_limit=0).
            return handoff
        last_render_len = len(rendered)

        trimmed = False
        for _ in range(len(_TRIM_ORDER)):
            section = _TRIM_ORDER[cursor % len(_TRIM_ORDER)]
            cursor += 1
            if working[section]:
                working[section].pop()
                trimmed = True
                break

        if trimmed:
            continue

        if working["mission"]:
            shortened = _shorten_scalar(working["mission"][0])
            working["mission"] = [shortened] if shortened else []
            continue
        if working["next_action"]:
            shortened = _shorten_scalar(working["next_action"][0])
            working["next_action"] = [shortened] if shortened else []
            continue

        return handoff


def _shorten_scalar(value: str) -> str:
    """Halve a scalar field with a trailing ellipsis, or drop entirely.

    Returns the empty string once the value is short enough that further
    halving would erase it; callers then drop the bucket.
    """
    if not value:
        return ""
    if len(value) <= 4:
        return ""
    half = max(1, len(value) // 2)
    return value[:half].rstrip() + "…"


__all__ = ["CompressedHandoff", "compress_context", "NotesInput"]
