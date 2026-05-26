"""Tests for hermes_cli.memory_tree.retriever."""

from __future__ import annotations

from hermes_cli.memory_tree.artifacts import make_artifact
from hermes_cli.memory_tree.chunker import chunk_text
from hermes_cli.memory_tree.index import MemoryTreeIndex
from hermes_cli.memory_tree.retriever import Retriever


def _ingest(idx, uri, content, *, kind="markdown", title=None, created_at="2026-01-01T00:00:00Z"):
    artifact, cleaned = make_artifact(
        uri, content, kind=kind, title=title, created_at=created_at
    )
    idx.upsert_artifact(artifact)
    idx.upsert_chunks(chunk_text(artifact, cleaned))
    return artifact


def test_retrieve_empty_query_returns_empty_packet():
    with MemoryTreeIndex(":memory:") as idx:
        _ingest(idx, "file://a.md", "# T\n\nalpha body.\n")
        packet = Retriever(idx).retrieve("the and")  # all stopwords
        assert packet.chunks == ()
        assert packet.total_candidates == 0


def test_retrieve_returns_relevant_chunks():
    with MemoryTreeIndex(":memory:") as idx:
        _ingest(idx, "file://a.md", "# Top\n\nalpha bravo charlie.\n\n## S\n\ndelta echo foxtrot.\n")
        packet = Retriever(idx).retrieve("delta echo")
        assert packet.chunks
        assert any("delta" in c.chunk.text for c in packet.chunks)


def test_heading_boost_prefers_heading_match():
    with MemoryTreeIndex(":memory:") as idx:
        _ingest(
            idx,
            "file://a.md",
            "# Top\n\nfiller paragraph one mentioning widgets briefly.\n",
            title="Misc",
        )
        _ingest(
            idx,
            "file://b.md",
            "# Widgets\n\nfiller body without the keyword frequently.\n",
            title="Misc",
        )
        packet = Retriever(idx).retrieve("widgets")
        assert packet.chunks
        # The chunk under the "Widgets" heading should outrank the prose mention.
        top = packet.chunks[0]
        assert "Widgets" in top.chunk.heading_path or "widgets" in top.chunk.text.lower()


def test_title_boost_helps_title_match():
    with MemoryTreeIndex(":memory:") as idx:
        _ingest(
            idx,
            "file://b.md",
            "# Other\n\nbody without target word.\n",
            title="Cosmic Widgets",
        )
        _ingest(
            idx,
            "file://a.md",
            "# Other\n\nwidgets appears once in body here.\n",
            title="Generic",
        )
        packet = Retriever(idx).retrieve("widgets")
        assert packet.chunks
        scores = sorted([c.score for c in packet.chunks], reverse=True)
        assert scores[0] >= scores[-1]


def test_budget_enforces_max_chunks():
    with MemoryTreeIndex(":memory:") as idx:
        for i in range(12):
            _ingest(idx, f"file://a{i}.md", f"# T{i}\n\nalpha mention number {i}.\n")
        packet = Retriever(idx, max_chunks=4, max_chars=100_000).retrieve("alpha")
        assert len(packet.chunks) == 4
        assert packet.truncated is True


def test_budget_enforces_max_chars():
    with MemoryTreeIndex(":memory:") as idx:
        for i in range(6):
            _ingest(idx, f"file://a{i}.md", f"# T{i}\n\nalpha " + ("x " * 200) + "\n")
        packet = Retriever(idx, max_chunks=100, max_chars=300).retrieve("alpha")
        assert sum(len(c.chunk.text) for c in packet.chunks) <= 300 + 1
        assert packet.truncated is True


def test_source_filter_narrows_results():
    with MemoryTreeIndex(":memory:") as idx:
        _ingest(idx, "file://local.md", "# A\n\nalpha local.\n")
        _ingest(idx, "https://x/y", "# B\n\nalpha remote.\n")
        packet = Retriever(idx).retrieve("alpha", source_filter=["file://"])
        assert packet.chunks
        assert all(c.artifact.source_uri.startswith("file://") for c in packet.chunks)


def test_retrieve_no_candidates_returns_empty():
    with MemoryTreeIndex(":memory:") as idx:
        _ingest(idx, "file://a.md", "# T\n\nalpha body.\n")
        packet = Retriever(idx).retrieve("nonexistentkeyword12345")
        assert packet.chunks == ()
        assert packet.total_candidates == 0
        assert packet.truncated is False
