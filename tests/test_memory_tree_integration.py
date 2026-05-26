"""End-to-end smoke for the memory tree foundation."""

from __future__ import annotations

from hermes_cli.memory_tree.artifacts import make_artifact
from hermes_cli.memory_tree.chunker import chunk_text
from hermes_cli.memory_tree.index import MemoryTreeIndex
from hermes_cli.memory_tree.retriever import Retriever
from hermes_cli.memory_tree.summary_tree import build_summary_tree
from hermes_cli.memory_tree.vault import export_vault


def test_full_round_trip(tmp_path):
    db = tmp_path / "tree.db"
    vault = tmp_path / "vault"

    sample = """# Jarvis Prime Memory Tree

The system stores artifacts, chunks, and summaries.

## Architecture

The architecture is stdlib-only. SQLite backs the index.

## Safety

Secrets like AKIAIOSFODNN7EXAMPLE are redacted on ingest.
"""

    artifact, cleaned = make_artifact(
        "file://docs/memory.md",
        sample,
        kind="markdown",
        title="Memory Tree",
        created_at="2026-01-01T00:00:00Z",
    )
    assert "AKIA" not in cleaned
    assert "aws_access_key" in artifact.provenance["redactions"]

    chunks = chunk_text(artifact, cleaned)
    assert chunks
    summaries = build_summary_tree(artifact, chunks)
    assert summaries

    with MemoryTreeIndex(db) as idx:
        idx.upsert_artifact(artifact)
        idx.upsert_chunks(chunks)
        for s in summaries:
            idx.upsert_summary(s)

        packet = Retriever(idx).retrieve("architecture sqlite")
        assert packet.chunks
        assert any("SQLite" in c.chunk.text for c in packet.chunks)

        export_vault(idx, vault)

    assert (vault / "index.md").exists()
    artifact_files = list((vault / "artifacts").glob("*.md"))
    assert artifact_files
    text = artifact_files[0].read_text(encoding="utf-8")
    assert "Memory Tree" in text
    assert "AKIA" not in text
    assert "[REDACTED:aws_access_key]" in text
