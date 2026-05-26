"""Keyword retrieval with source-aware ranking and bounded packets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from hermes_cli.memory_tree.artifacts import Artifact
from hermes_cli.memory_tree.chunker import Chunk
from hermes_cli.memory_tree.index import MemoryTreeIndex

_TOKEN_RE = re.compile(r"[A-Za-z0-9]{2,}")
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "have", "are",
        "was", "but", "not", "you", "your", "they", "their", "his", "her",
        "its", "into", "out", "about", "what", "when", "where", "who",
        "how", "why", "which", "will", "would", "should", "could", "than",
        "then", "there", "these", "those", "been", "being", "had", "has",
    }
)


def _tokenise(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS]


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    artifact: Artifact
    score: float


@dataclass(frozen=True)
class ScoredSummary:
    summary_id: str
    artifact_id: str
    text: str
    score: float


@dataclass(frozen=True)
class RetrievalPacket:
    query: str
    chunks: tuple[ScoredChunk, ...]
    summaries: tuple[ScoredSummary, ...]
    truncated: bool
    total_candidates: int


class Retriever:
    """Keyword retrieval over a MemoryTreeIndex with bounded output."""

    def __init__(
        self,
        index: MemoryTreeIndex,
        *,
        max_chunks: int = 8,
        max_chars: int = 8000,
        heading_boost: float = 1.5,
        title_boost: float = 1.2,
        recency_boost: float = 0.5,
    ) -> None:
        self.index = index
        self.max_chunks = max_chunks
        self.max_chars = max_chars
        self.heading_boost = heading_boost
        self.title_boost = title_boost
        self.recency_boost = recency_boost

    def retrieve(
        self,
        query: str,
        *,
        source_filter: Sequence[str] | None = None,
    ) -> RetrievalPacket:
        terms = _tokenise(query)
        if not terms:
            return RetrievalPacket(
                query=query, chunks=(), summaries=(), truncated=False, total_candidates=0
            )

        raw = self.index.keyword_search(terms, limit=200, source_filter=source_filter)
        total = len(raw)

        scored: list[ScoredChunk] = []
        now = datetime.now(timezone.utc)
        for chunk, artifact, tf in raw:
            score = float(tf)
            heading_blob = " ".join(chunk.heading_path).lower()
            for term in terms:
                if term in heading_blob:
                    score += self.heading_boost
                if artifact.title and term in artifact.title.lower():
                    score += self.title_boost
            score += self._recency(artifact, now)
            scored.append(ScoredChunk(chunk=chunk, artifact=artifact, score=score))

        scored.sort(key=lambda s: s.score, reverse=True)

        kept: list[ScoredChunk] = []
        char_budget = 0
        truncated = False
        for entry in scored:
            if len(kept) >= self.max_chunks:
                truncated = True
                break
            char_budget += len(entry.chunk.text)
            if char_budget > self.max_chars:
                truncated = True
                break
            kept.append(entry)

        return RetrievalPacket(
            query=query,
            chunks=tuple(kept),
            summaries=(),  # reserved for future wave
            truncated=truncated,
            total_candidates=total,
        )

    def _recency(self, artifact: Artifact, now: datetime) -> float:
        try:
            created = datetime.strptime(artifact.created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return 0.0
        age_days = max(0.0, (now - created).total_seconds() / 86400.0)
        # Decay over ~30 days; bounded by recency_boost.
        return self.recency_boost * (1.0 / (1.0 + age_days / 30.0))


__all__ = ["Retriever", "RetrievalPacket", "ScoredChunk", "ScoredSummary"]
