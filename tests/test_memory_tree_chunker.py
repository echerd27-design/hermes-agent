"""Tests for hermes_cli.memory_tree.chunker."""

from __future__ import annotations

import pytest

from hermes_cli.memory_tree.artifacts import make_artifact
from hermes_cli.memory_tree.chunker import chunk_text


def _markdown_artifact(content: str, kind: str = "markdown"):
    art, cleaned = make_artifact(
        "file://doc.md", content, kind=kind, created_at="2026-01-01T00:00:00Z"
    )
    return art, cleaned


def test_markdown_chunks_preserve_heading_path():
    md = """# Top

intro text.

## A

alpha body.

### A.1

deep body.

## B

beta body.
"""
    artifact, cleaned = _markdown_artifact(md)
    chunks = chunk_text(artifact, cleaned)
    paths = [c.heading_path for c in chunks]
    assert ("Top",) in paths
    assert ("Top", "A") in paths
    assert ("Top", "A", "A.1") in paths
    assert ("Top", "B") in paths


def test_chunk_ids_are_deterministic_across_runs():
    md = "# T\n\nbody one.\n\n## S\n\nbody two.\n"
    artifact, cleaned = _markdown_artifact(md)
    ids_a = [c.chunk_id for c in chunk_text(artifact, cleaned)]
    ids_b = [c.chunk_id for c in chunk_text(artifact, cleaned)]
    assert ids_a == ids_b
    assert all(cid.startswith("chk:") for cid in ids_a)


def test_chunk_ordinals_are_monotonic():
    md = "# T\n\nA\n\n## S1\n\nB\n\n## S2\n\nC\n"
    artifact, cleaned = _markdown_artifact(md)
    chunks = chunk_text(artifact, cleaned)
    ordinals = [c.ordinal for c in chunks]
    assert ordinals == list(range(len(chunks)))


def test_plain_text_chunking_has_no_headings():
    text = "paragraph one.\n\nparagraph two.\n\nparagraph three.\n"
    artifact, cleaned = _markdown_artifact(text, kind="text")
    chunks = chunk_text(artifact, cleaned, target_chars=20, max_chars=40)
    assert chunks
    assert all(c.heading_path == () for c in chunks)


def test_chunk_never_exceeds_max_chars():
    huge_para = ("word " * 600).strip()
    artifact, cleaned = _markdown_artifact(huge_para, kind="text")
    chunks = chunk_text(artifact, cleaned, target_chars=200, max_chars=400)
    assert chunks
    for c in chunks:
        assert len(c.text) <= 400


def test_chunker_returns_empty_for_empty_content():
    artifact, _ = _markdown_artifact("hello")
    assert chunk_text(artifact, "") == []


def test_chunker_validates_sizes():
    artifact, cleaned = _markdown_artifact("hi")
    with pytest.raises(ValueError):
        chunk_text(artifact, cleaned, target_chars=0, max_chars=10)
    with pytest.raises(ValueError):
        chunk_text(artifact, cleaned, target_chars=200, max_chars=100)


def test_chunker_skips_whitespace_only_sections():
    md = "# T\n\n   \n\n## S\n\nreal body.\n"
    artifact, cleaned = _markdown_artifact(md)
    chunks = chunk_text(artifact, cleaned)
    bodies = [c.text for c in chunks]
    assert any("real body" in b for b in bodies)
    assert all(b.strip() for b in bodies)


def test_char_offsets_point_into_content():
    md = "# Top\n\nalpha\n\n## Sub\n\nbeta\n"
    artifact, cleaned = _markdown_artifact(md)
    chunks = chunk_text(artifact, cleaned)
    for c in chunks:
        assert 0 <= c.char_start <= c.char_end <= len(cleaned)
        assert cleaned[c.char_start:c.char_end].strip().startswith(c.text.split("\n")[0][:5])
