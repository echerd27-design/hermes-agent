"""Stateless payload compressors for Jarvis Prime.

A different layer from ``agent/context_engine.py`` (the in-runtime
plugin ABC for whole-conversation compaction) and from
``trajectory_compressor.py`` (the async LLM-summarization pass for
stored trajectories). This module compresses *individual model/tool
payloads* — one stack trace, one diff, one log chunk — synchronously,
in pure Python, with no I/O and no network.

Every public function follows the same shape:

1. ``scrub`` runs first — secrets become typed placeholders before any
   evidence extractor or compressor sees the text.
2. Evidence is extracted from the scrubbed text into a typed tuple of
   ``(kind, snippet)`` pairs that survive compression verbatim.
3. The payload-specific rule set runs on the scrubbed text.
4. A frozen :class:`ContextPacket` is returned.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

from .context_packet import ContextPacket
from .redaction import scrub


_DEFAULT_MAX_CHARS = 4000


# ---------------------------------------------------------------------------
# Evidence extraction
# ---------------------------------------------------------------------------

# Evidence patterns match against the *scrubbed* text, so they cannot
# accidentally capture a secret value. The placeholder shape
# ``[REDACTED:<kind>]`` deliberately uses square brackets which are not in
# any evidence regex below.

_FILE_PATH_RE = re.compile(
    r"\b(?:[A-Za-z]:\\(?:[^\\\s\"'<>|*?\n]+\\)*[^\\\s\"'<>|*?\n]+\.[A-Za-z0-9]+"
    r"|(?:\./|/)?(?:[A-Za-z0-9_\-./]+/)+[A-Za-z0-9_\-.]+\.[A-Za-z0-9]+)\b"
)
_LINE_REF_RE = re.compile(
    r"\b([A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]+):(\d+)\b"
)
_TEST_ID_RE = re.compile(
    r"\b[A-Za-z0-9_\-./\\]+\.py::\w+(?:::\w+)*(?:\[[^\]]+\])?\b"
)
_FUNCTION_NAME_RE = re.compile(
    r"\bdef\s+([A-Za-z_]\w*)\s*\("
)
_STACK_FRAME_RE = re.compile(
    r'^\s*File "([^"]+)", line (\d+), in (\S+)\s*$',
    re.MULTILINE,
)
_ERROR_LINE_RE = re.compile(
    r"^(?:E\s+)?([A-Z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*Error|"
    r"[A-Z][A-Za-z0-9_]*Exception|"
    r"AssertionError|Traceback)(?::\s.*)?$",
    re.MULTILINE,
)
_SECURITY_WARNING_RE = re.compile(
    r"\b(CVE-\d{4}-\d{4,7}"
    r"|GHSA-[A-Za-z0-9\-]{4,}"
    r"|SEC-\d+"
    r"|security\s+warning"
    r"|vulnerability\s+(?:found|detected))",
    re.IGNORECASE,
)
_OWNER_GATE_RE = re.compile(
    r"\b(requires?\s+owner\s+approval"
    r"|owner[- ]gated\s+action"
    r"|owner\s+sign[- ]?off\s+required"
    r"|gate:\s*owner)",
    re.IGNORECASE,
)


def _extract_evidence(text: str) -> tuple[tuple[str, str], ...]:
    """Return ordered, de-duplicated ``(kind, snippet)`` evidence pairs."""

    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []

    def _push(kind: str, snippet: str) -> None:
        snippet = snippet.strip()
        if not snippet:
            return
        key = (kind, snippet)
        if key in seen:
            return
        seen.add(key)
        out.append(key)

    for m in _LINE_REF_RE.finditer(text):
        _push("line_ref", m.group(0))

    for m in _FILE_PATH_RE.finditer(text):
        snippet = m.group(0)
        # A ``file:line`` match was already captured as line_ref; skip the
        # raw filename in that case to avoid a duplicate record.
        if _LINE_REF_RE.search(snippet):
            continue
        _push("file_path", snippet)

    for m in _TEST_ID_RE.finditer(text):
        _push("test_id", m.group(0))

    for m in _FUNCTION_NAME_RE.finditer(text):
        _push("function_name", m.group(1))

    for m in _STACK_FRAME_RE.finditer(text):
        _push("stack_frame", m.group(0).strip())
        _push("function_name", m.group(3))

    for m in _ERROR_LINE_RE.finditer(text):
        _push("error_message", m.group(0).strip())

    for m in _SECURITY_WARNING_RE.finditer(text):
        _push("security_warning", m.group(0))

    for m in _OWNER_GATE_RE.finditer(text):
        _push("owner_gate", m.group(0))

    return tuple(out)


# ---------------------------------------------------------------------------
# Compression helpers
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_PROGRESS_LINE_RE = re.compile(r"^[.FEsxX]+\s*\[\s*\d+%\s*\]\s*$")
_LOG_HOT_LINE_RE = re.compile(r"(ERROR|WARN|WARNING|CRITICAL|FATAL|Traceback)")
_TEST_STATUS_LINE_RE = re.compile(r"^(FAILED|ERROR|PASSED|SKIPPED|XFAIL|XPASS)\s")
_HEADING_RE = re.compile(r"^#{1,6}\s")
_CODE_FENCE_RE = re.compile(r"^```")
_DIFF_KEEP_LINE_RE = re.compile(r"^(?:diff --git|\+\+\+|---|@@)")
_DIFF_CHANGE_RE = re.compile(r"^[+\-]")
_TRACE_HEADER_RE = re.compile(r"^Traceback \(most recent call last\):\s*$")
_FRAME_HEADER_RE = re.compile(r'^\s*File "([^"]+)", line (\d+), in (\S+)\s*$')


def _truncate_to_max(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    elided = len(text) - max_chars
    cut = text[:max_chars]
    # Try to anchor truncation on a paragraph boundary.
    boundary = cut.rfind("\n\n")
    if boundary > max_chars // 2:
        cut = cut[:boundary]
        elided = len(text) - len(cut)
    return cut + f"\n[... {elided} chars elided ...]", True


def _build_packet(
    *,
    source_type: str,
    original: str,
    payload: str,
    evidence: tuple[tuple[str, str], ...],
    warnings: tuple[str, ...],
    artifact_ref: str | None,
) -> ContextPacket:
    return ContextPacket(
        source_type=source_type,
        payload=payload,
        original_length=len(original),
        compressed_length=len(payload),
        preserved_evidence=evidence,
        warnings=warnings,
        artifact_ref=artifact_ref,
    )


def _prepare(text: str) -> tuple[str, list[str], tuple[tuple[str, str], ...]]:
    """Run scrub → evidence extract. Returns (clean, base_warnings, evidence)."""

    clean, redacted = scrub(text or "")
    warnings: list[str] = []
    if redacted:
        warnings.append(f"redacted {redacted} secret-like tokens")
    evidence = _extract_evidence(clean)
    return clean, warnings, evidence


# ---------------------------------------------------------------------------
# compress_text
# ---------------------------------------------------------------------------

def compress_text(
    text: str,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    original = text or ""
    clean, warnings, evidence = _prepare(original)
    collapsed = _BLANK_RUN_RE.sub("\n\n", clean)
    payload, truncated = _truncate_to_max(collapsed, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")
    return _build_packet(
        source_type="text",
        original=original,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# compress_markdown
# ---------------------------------------------------------------------------

def compress_markdown(
    md: str,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    original = md or ""
    clean, warnings, evidence = _prepare(original)

    lines = clean.splitlines()
    out: list[str] = []
    in_code = False
    paragraph: list[str] = []
    paragraphs_collapsed = 0

    def flush_paragraph() -> None:
        nonlocal paragraphs_collapsed
        if not paragraph:
            return
        if len(paragraph) > 5:
            first, last = paragraph[0], paragraph[-1]
            elided = len(paragraph) - 2
            out.append(first)
            out.append(f"[... {elided} lines elided ...]")
            out.append(last)
            paragraphs_collapsed += 1
        else:
            out.extend(paragraph)
        paragraph.clear()

    for line in lines:
        if _CODE_FENCE_RE.match(line):
            flush_paragraph()
            out.append(line)
            in_code = not in_code
            continue
        if in_code:
            out.append(line)
            continue
        if _HEADING_RE.match(line):
            flush_paragraph()
            out.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            out.append(line)
            continue
        paragraph.append(line)
    flush_paragraph()

    body = "\n".join(out)
    if paragraphs_collapsed:
        warnings.append(f"collapsed {paragraphs_collapsed} long prose paragraphs")
    payload, truncated = _truncate_to_max(body, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")

    return _build_packet(
        source_type="markdown",
        original=original,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# compress_json
# ---------------------------------------------------------------------------

_JSON_ARRAY_CUTOFF = 5


def _summarize_json_node(node: Any) -> Any:
    if isinstance(node, list):
        if len(node) > _JSON_ARRAY_CUTOFF:
            first = _summarize_json_node(node[0])
            second = _summarize_json_node(node[1])
            last = _summarize_json_node(node[-1])
            elided = len(node) - 3
            return [first, second, f"[<elided {elided} items>]", last]
        return [_summarize_json_node(item) for item in node]
    if isinstance(node, dict):
        return {key: _summarize_json_node(value) for key, value in node.items()}
    return node


def compress_json(
    data: str | Mapping[str, Any] | Sequence[Any],
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    if isinstance(data, str):
        original_text = data
    else:
        original_text = json.dumps(data, ensure_ascii=False)

    clean, warnings, evidence = _prepare(original_text)

    parse_failed = False
    try:
        parsed = json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        parse_failed = True
        parsed = None

    if parse_failed:
        warnings.append("json parse failed; falling back to text compression")
        payload, truncated = _truncate_to_max(clean, max_chars)
        if truncated:
            warnings.append("truncated to max_chars")
        return _build_packet(
            source_type="json",
            original=original_text,
            payload=payload,
            evidence=evidence,
            warnings=tuple(warnings),
            artifact_ref=artifact_ref,
        )

    summarized = _summarize_json_node(parsed)
    body = json.dumps(summarized, ensure_ascii=False)
    payload, truncated = _truncate_to_max(body, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")

    return _build_packet(
        source_type="json",
        original=original_text,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# compress_log
# ---------------------------------------------------------------------------

def compress_log(
    text: str,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    original = text or ""
    clean, warnings, evidence = _prepare(original)
    no_ansi = _ANSI_RE.sub("", clean)

    out: list[str] = []
    duplicates_collapsed = 0
    prev_line: str | None = None
    repeat_count = 0
    hot_lines_seen = 0

    def flush_repeats() -> None:
        nonlocal duplicates_collapsed
        if prev_line is None:
            return
        if repeat_count > 1:
            out.append(f"{prev_line} (× {repeat_count})")
            duplicates_collapsed += repeat_count - 1
        else:
            out.append(prev_line)

    for line in no_ansi.splitlines():
        is_hot = bool(_LOG_HOT_LINE_RE.search(line))
        if is_hot:
            hot_lines_seen += 1
        if prev_line is not None and line == prev_line and not is_hot:
            repeat_count += 1
            continue
        flush_repeats()
        prev_line = line
        repeat_count = 1
    flush_repeats()

    body = "\n".join(out)
    if duplicates_collapsed:
        warnings.append(f"deduplicated {duplicates_collapsed} repeated log lines")
    payload, truncated = _truncate_to_max(body, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")
    if hot_lines_seen:
        warnings.append(f"preserved {hot_lines_seen} error/warn lines")

    return _build_packet(
        source_type="log",
        original=original,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# compress_diff
# ---------------------------------------------------------------------------

def compress_diff(
    text: str,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    original = text or ""
    clean, warnings, evidence = _prepare(original)

    out: list[str] = []
    context_run: list[str] = []
    unchanged_collapsed = 0

    def flush_context() -> None:
        nonlocal unchanged_collapsed
        if not context_run:
            return
        if len(context_run) >= 3:
            unchanged_collapsed += len(context_run)
            out.append(f"[... {len(context_run)} unchanged lines ...]")
        else:
            out.extend(context_run)
        context_run.clear()

    for line in clean.splitlines():
        if _DIFF_KEEP_LINE_RE.match(line) or _DIFF_CHANGE_RE.match(line):
            flush_context()
            out.append(line)
        else:
            # Treat as context (space-prefixed or otherwise unchanged).
            context_run.append(line)
    flush_context()

    body = "\n".join(out)
    if unchanged_collapsed:
        warnings.append(f"collapsed {unchanged_collapsed} unchanged context lines")
    payload, truncated = _truncate_to_max(body, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")

    return _build_packet(
        source_type="diff",
        original=original,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# compress_test_output
# ---------------------------------------------------------------------------

def compress_test_output(
    text: str,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    original = text or ""
    clean, warnings, evidence = _prepare(original)

    out: list[str] = []
    progress_dropped = 0
    in_traceback = False

    for line in clean.splitlines():
        stripped = line.rstrip()
        if _PROGRESS_LINE_RE.match(stripped):
            progress_dropped += 1
            continue
        if _TRACE_HEADER_RE.match(stripped):
            in_traceback = True
            out.append(stripped)
            continue
        if in_traceback:
            if stripped and not stripped.startswith(" ") and not _ERROR_LINE_RE.match(stripped):
                in_traceback = False
            out.append(stripped)
            continue
        if _TEST_STATUS_LINE_RE.match(stripped):
            out.append(stripped)
            continue
        if _ERROR_LINE_RE.match(stripped):
            out.append(stripped)
            continue
        out.append(stripped)

    body = "\n".join(out)
    if progress_dropped:
        warnings.append(f"dropped {progress_dropped} progress lines")
    payload, truncated = _truncate_to_max(body, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")

    return _build_packet(
        source_type="test_output",
        original=original,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# compress_stack_trace
# ---------------------------------------------------------------------------

def compress_stack_trace(
    text: str,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    artifact_ref: str | None = None,
) -> ContextPacket:
    original = text or ""
    clean, warnings, evidence = _prepare(original)

    lines = clean.splitlines()
    out: list[str] = []
    pending_frame: tuple[str, str] | None = None  # (frame_header, code_line)
    repeat_count = 0
    recursion_collapsed = 0

    def flush_pending() -> None:
        nonlocal recursion_collapsed
        if pending_frame is None:
            return
        out.append(pending_frame[0])
        if pending_frame[1] is not None:
            out.append(pending_frame[1])
        if repeat_count > 1:
            extra = repeat_count - 1
            out.append(f"... (frame repeated {extra} more time{'s' if extra != 1 else ''}) ...")
            recursion_collapsed += extra

    i = 0
    while i < len(lines):
        line = lines[i]
        if _FRAME_HEADER_RE.match(line):
            code_line = ""
            if i + 1 < len(lines) and not _FRAME_HEADER_RE.match(lines[i + 1]):
                code_line = lines[i + 1]
                i += 1
            frame = (line, code_line)
            if pending_frame is not None and frame == pending_frame:
                repeat_count += 1
            else:
                flush_pending()
                pending_frame = frame
                repeat_count = 1
        else:
            flush_pending()
            pending_frame = None
            repeat_count = 0
            out.append(line)
        i += 1
    flush_pending()

    body = "\n".join(out)
    if recursion_collapsed:
        warnings.append(f"collapsed {recursion_collapsed} repeated stack frames")
    payload, truncated = _truncate_to_max(body, max_chars)
    if truncated:
        warnings.append("truncated to max_chars")

    return _build_packet(
        source_type="stack_trace",
        original=original,
        payload=payload,
        evidence=evidence,
        warnings=tuple(warnings),
        artifact_ref=artifact_ref,
    )


# ---------------------------------------------------------------------------
# Public listing — helps callers reflect over the available compressors.
# ---------------------------------------------------------------------------

COMPRESSORS: tuple[tuple[str, Callable[..., ContextPacket]], ...] = (
    ("text", compress_text),
    ("markdown", compress_markdown),
    ("json", compress_json),
    ("log", compress_log),
    ("diff", compress_diff),
    ("test_output", compress_test_output),
    ("stack_trace", compress_stack_trace),
)


__all__ = [
    "ContextPacket",
    "compress_text",
    "compress_markdown",
    "compress_json",
    "compress_log",
    "compress_diff",
    "compress_test_output",
    "compress_stack_trace",
    "COMPRESSORS",
]
