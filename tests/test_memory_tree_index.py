"""Tests for hermes_cli.memory_tree.index."""

from __future__ import annotations

from hermes_cli.memory_tree.artifacts import make_artifact
from hermes_cli.memory_tree.chunker import chunk_text
from hermes_cli.memory_tree.index import SCHEMA_VERSION, MemoryTreeIndex
from hermes_cli.memory_tree.summary_tree import build_summary_tree


def _seed(idx: MemoryTreeIndex, content: str = "# T\n\nalpha body.\n\n## S\n\nbeta body.\n"):
    artifact, cleaned = make_artifact(
        "file://t.md", content, kind="markdown", created_at="2026-01-01T00:00:00Z"
    )
    chunks = chunk_text(artifact, cleaned)
    idx.upsert_artifact(artifact)
    idx.upsert_chunks(chunks)
    return artifact, chunks


def test_schema_version_seeded():
    with MemoryTreeIndex(":memory:") as idx:
        assert idx.schema_version() == SCHEMA_VERSION


def test_on_disk_uses_wal(tmp_path):
    db = tmp_path / "tree.db"
    with MemoryTreeIndex(db) as idx:
        mode = idx.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    assert db.exists()


def test_memory_db_does_not_use_wal():
    with MemoryTreeIndex(":memory:") as idx:
        mode = idx.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() != "wal"


def test_upsert_and_get_artifact():
    with MemoryTreeIndex(":memory:") as idx:
        artifact, _ = _seed(idx)
        round_trip = idx.get_artifact(artifact.artifact_id)
        assert round_trip is not None
        assert round_trip.artifact_id == artifact.artifact_id
        assert round_trip.source_uri == artifact.source_uri


def test_upsert_is_idempotent():
    with MemoryTreeIndex(":memory:") as idx:
        artifact, chunks = _seed(idx)
        idx.upsert_artifact(artifact)
        idx.upsert_chunks(chunks)
        count = idx.conn.execute("SELECT COUNT(*) FROM chunk").fetchone()[0]
        assert count == len(chunks)
        a_count = idx.conn.execute("SELECT COUNT(*) FROM artifact").fetchone()[0]
        assert a_count == 1


def test_delete_artifact_cascades_chunks_and_summaries():
    with MemoryTreeIndex(":memory:") as idx:
        artifact, chunks = _seed(idx)
        for s in build_summary_tree(artifact, chunks):
            idx.upsert_summary(s)
        idx.delete_artifact(artifact.artifact_id)
        assert idx.get_artifact(artifact.artifact_id) is None
        remaining_chunks = list(idx.iter_chunks())
        assert remaining_chunks == []
        remaining_summaries = list(idx.iter_summaries())
        assert all(s.scope_key != artifact.artifact_id for s in remaining_summaries)


def test_keyword_search_ranks_by_frequency():
    with MemoryTreeIndex(":memory:") as idx:
        artifact, _ = _seed(
            idx,
            "# T\n\nalpha alpha alpha here.\n\n## S\n\nbeta once mentioned.\n",
        )
        results = idx.keyword_search(["alpha"], limit=5)
        assert results
        assert results[0][2] >= 3


def test_keyword_search_filters_by_source():
    with MemoryTreeIndex(":memory:") as idx:
        a1, c1 = make_artifact(
            "file://repo/a.md",
            "# A\n\nalpha repo content.\n",
            kind="markdown",
            created_at="2026-01-01T00:00:00Z",
        )
        a2, c2 = make_artifact(
            "https://example.com/b",
            "# B\n\nalpha web content.\n",
            kind="markdown",
            created_at="2026-01-01T00:00:00Z",
        )
        for art, content in ((a1, c1), (a2, c2)):
            idx.upsert_artifact(art)
            idx.upsert_chunks(chunk_text(art, content))

        repo_hits = idx.keyword_search(["alpha"], source_filter=["file://"])
        assert repo_hits
        assert all(h[1].source_uri.startswith("file://") for h in repo_hits)

        web_hits = idx.keyword_search(["alpha"], source_filter=["https://"])
        assert web_hits
        assert all(h[1].source_uri.startswith("https://") for h in web_hits)


def test_iter_chunks_filters_by_artifact():
    with MemoryTreeIndex(":memory:") as idx:
        artifact, chunks = _seed(idx)
        listed = list(idx.iter_chunks(artifact.artifact_id))
        assert len(listed) == len(chunks)
        none_listed = list(idx.iter_chunks("art:nonexistent"))
        assert none_listed == []
