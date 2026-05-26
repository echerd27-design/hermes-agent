"""Deterministic hierarchical summaries — no LLM call.

Level 0: first sentence of each chunk, scoped to the chunk's heading path.
Level 1: bullet-list rollup of siblings sharing a heading-path prefix.
Level 2: artifact-level rollup — title + ordered top-level headings.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from hermes_cli.memory_tree.artifacts import Artifact
from hermes_cli.memory_tree.chunker import Chunk

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


@dataclass(frozen=True)
class Summary:
    summary_id: str
    scope: str
    scope_key: str
    level: int
    heading_path: tuple[str, ...]
    text: str
    child_ids: tuple[str, ...]
    created_at: str


def _summary_id(scope: str, scope_key: str, level: int, heading_path: Sequence[str]) -> str:
    h = hashlib.sha256()
    h.update(f"{scope}:{scope_key}:{level}:{'/'.join(heading_path)}".encode("utf-8"))
    return f"sum:{h.hexdigest()[:16]}"


def _first_sentence(text: str, *, max_len: int = 240) -> str:
    text = text.strip()
    if not text:
        return ""
    first = _SENTENCE_RE.split(text, maxsplit=1)[0]
    first = first.strip()
    if len(first) > max_len:
        first = first[: max_len - 1].rstrip() + "…"
    return first


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_summary_tree(artifact: Artifact, chunks: Sequence[Chunk]) -> list[Summary]:
    """Build a deterministic three-level summary tree for an artifact."""
    created = artifact.created_at or _utc_now_iso()
    summaries: list[Summary] = []

    # Level 0 — one summary per chunk
    level0_by_path: dict[tuple[str, ...], list[Summary]] = {}
    for chunk in chunks:
        first = _first_sentence(chunk.text)
        if not first:
            continue
        text = first if not chunk.heading_path else f"[{' › '.join(chunk.heading_path)}] {first}"
        sid = _summary_id("chunk", chunk.chunk_id, 0, chunk.heading_path)
        s = Summary(
            summary_id=sid,
            scope="chunk",
            scope_key=chunk.chunk_id,
            level=0,
            heading_path=chunk.heading_path,
            text=text,
            child_ids=(),
            created_at=created,
        )
        summaries.append(s)
        level0_by_path.setdefault(chunk.heading_path, []).append(s)

    # Level 1 — section rollups grouped by top-level heading
    level1_by_top: dict[str, list[Summary]] = {}
    for path, items in sorted(level0_by_path.items(), key=lambda kv: kv[0]):
        top = path[0] if path else ""
        bullets = [f"- {s.text}" for s in items]
        body = "\n".join(bullets)
        sid = _summary_id("section", artifact.artifact_id, 1, path)
        s = Summary(
            summary_id=sid,
            scope="section",
            scope_key=artifact.artifact_id,
            level=1,
            heading_path=path,
            text=body,
            child_ids=tuple(child.summary_id for child in items),
            created_at=created,
        )
        summaries.append(s)
        level1_by_top.setdefault(top, []).append(s)

    # Level 2 — artifact rollup
    top_headings = [t for t in level1_by_top.keys() if t]
    body_lines = []
    if artifact.title:
        body_lines.append(f"# {artifact.title}")
    body_lines.append(f"Source: {artifact.source_uri}")
    if top_headings:
        body_lines.append("Sections:")
        body_lines.extend(f"- {h}" for h in top_headings)
    body = "\n".join(body_lines)
    children = tuple(
        s.summary_id
        for group in level1_by_top.values()
        for s in group
    )
    sid = _summary_id("artifact", artifact.artifact_id, 2, ())
    summaries.append(
        Summary(
            summary_id=sid,
            scope="artifact",
            scope_key=artifact.artifact_id,
            level=2,
            heading_path=(),
            text=body,
            child_ids=children,
            created_at=created,
        )
    )

    return summaries


__all__ = ["Summary", "build_summary_tree"]
