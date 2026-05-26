"""Deterministic Markdown / text chunker.

Splits content into bounded chunks while preserving heading paths for
Markdown documents. Chunk IDs are derived from artifact_id + ordinal +
char offsets so re-running on the same input yields identical IDs.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from hermes_cli.memory_tree.artifacts import Artifact


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    artifact_id: str
    ordinal: int
    heading_path: tuple[str, ...]
    text: str
    byte_size: int
    char_start: int
    char_end: int


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


def _chunk_id(artifact_id: str, ordinal: int, start: int, end: int) -> str:
    h = hashlib.sha256()
    h.update(f"{artifact_id}:{ordinal}:{start}:{end}".encode("utf-8"))
    return f"chk:{h.hexdigest()[:16]}"


def _split_to_budget(text: str, target: int, hard_max: int) -> list[tuple[int, int]]:
    """Return (start, end) char offsets splitting text by paragraph→sentence→hard-wrap."""
    if len(text) <= target:
        return [(0, len(text))]

    spans: list[tuple[int, int]] = []
    paragraphs = [m for m in re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", text)]
    if not paragraphs:
        # Pure whitespace — emit a single span if there's any content.
        return [(0, len(text))] if text else []

    buf_start = paragraphs[0].start()
    buf_end = buf_start

    def _flush(start: int, end: int) -> None:
        if end > start:
            spans.append((start, end))

    for para in paragraphs:
        para_text = text[para.start():para.end()]
        # If a single paragraph blows past hard_max, break it on sentences then hard-wrap.
        if len(para_text) > hard_max:
            _flush(buf_start, buf_end)
            buf_start = para.end()
            buf_end = para.end()
            for s_start, s_end in _split_long_paragraph(text, para.start(), para.end(), target, hard_max):
                _flush(s_start, s_end)
            continue

        if buf_end == buf_start:
            buf_start = para.start()
            buf_end = para.end()
            continue

        # Would adding this paragraph push us past target?
        if (para.end() - buf_start) > target:
            _flush(buf_start, buf_end)
            buf_start = para.start()
            buf_end = para.end()
        else:
            buf_end = para.end()

    _flush(buf_start, buf_end)
    return spans


def _split_long_paragraph(
    text: str, p_start: int, p_end: int, target: int, hard_max: int
) -> list[tuple[int, int]]:
    body = text[p_start:p_end]
    sentence_breaks = [m.start() for m in _SENTENCE_RE.finditer(body)]
    cuts = [0, *sentence_breaks, len(body)]
    spans: list[tuple[int, int]] = []
    cur_start = 0
    cur_end = 0
    for nxt in cuts[1:]:
        if (nxt - cur_start) > target and cur_end > cur_start:
            spans.append((p_start + cur_start, p_start + cur_end))
            cur_start = cur_end
        cur_end = nxt
    if cur_end > cur_start:
        spans.append((p_start + cur_start, p_start + cur_end))

    # Hard-wrap any over-large span.
    out: list[tuple[int, int]] = []
    for s, e in spans:
        if (e - s) <= hard_max:
            out.append((s, e))
            continue
        cursor = s
        while cursor < e:
            out.append((cursor, min(cursor + hard_max, e)))
            cursor += hard_max
    return out


def _markdown_sections(content: str) -> list[tuple[tuple[str, ...], int, int]]:
    """Return [(heading_path, body_start, body_end), ...] covering all content."""
    sections: list[tuple[tuple[str, ...], int, int]] = []
    headings = list(_HEADING_RE.finditer(content))

    if not headings:
        if content:
            sections.append(((), 0, len(content)))
        return sections

    # Preamble before first heading.
    first = headings[0]
    if first.start() > 0:
        preamble = content[: first.start()]
        if preamble.strip():
            sections.append(((), 0, first.start()))

    stack: list[tuple[int, str]] = []  # (level, title)
    for idx, match in enumerate(headings):
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        path = tuple(t for _, t in stack)
        body_start = match.end()
        body_end = headings[idx + 1].start() if idx + 1 < len(headings) else len(content)
        sections.append((path, body_start, body_end))
    return sections


def chunk_text(
    artifact: Artifact,
    content: str,
    *,
    target_chars: int = 1200,
    max_chars: int = 2000,
) -> list[Chunk]:
    """Split content into deterministic chunks."""
    if target_chars <= 0 or max_chars <= 0 or target_chars > max_chars:
        raise ValueError("invalid chunk size: require 0 < target_chars <= max_chars")
    if not content:
        return []

    chunks: list[Chunk] = []
    ordinal = 0

    if artifact.kind in {"markdown", "doc"}:
        sections = _markdown_sections(content)
    else:
        sections = [((), 0, len(content))]

    for heading_path, body_start, body_end in sections:
        body = content[body_start:body_end]
        if not body.strip():
            continue
        for sub_start, sub_end in _split_to_budget(body, target_chars, max_chars):
            abs_start = body_start + sub_start
            abs_end = body_start + sub_end
            text = content[abs_start:abs_end].strip("\n")
            if not text.strip():
                continue
            chunk = Chunk(
                chunk_id=_chunk_id(artifact.artifact_id, ordinal, abs_start, abs_end),
                artifact_id=artifact.artifact_id,
                ordinal=ordinal,
                heading_path=heading_path,
                text=text,
                byte_size=len(text.encode("utf-8")),
                char_start=abs_start,
                char_end=abs_end,
            )
            chunks.append(chunk)
            ordinal += 1

    return chunks


def iter_chunks(chunks: Iterable[Chunk]) -> Iterable[Chunk]:
    """Stable pass-through helper for typing consistency at call sites."""
    yield from chunks
