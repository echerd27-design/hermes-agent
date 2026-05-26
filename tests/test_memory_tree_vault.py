"""Tests for hermes_cli.memory_tree.vault."""

from __future__ import annotations

import pytest

from hermes_cli.memory_tree.artifacts import make_artifact
from hermes_cli.memory_tree.chunker import chunk_text
from hermes_cli.memory_tree.index import MemoryTreeIndex
from hermes_cli.memory_tree.summary_tree import build_summary_tree
from hermes_cli.memory_tree.vault import export_vault


def _seed(idx, *, with_secret: bool = False, title: str | None = "My Title"):
    content = "# Top\n\nalpha body.\n\n## Sub\n\nbeta body.\n"
    if with_secret:
        content += "\nkey AKIAIOSFODNN7EXAMPLE remains.\n"
    artifact, cleaned = make_artifact(
        "file://t.md",
        content,
        kind="markdown",
        title=title,
        created_at="2026-01-01T00:00:00Z",
    )
    chunks = chunk_text(artifact, cleaned)
    idx.upsert_artifact(artifact)
    idx.upsert_chunks(chunks)
    for s in build_summary_tree(artifact, chunks):
        idx.upsert_summary(s)
    return artifact, chunks


def test_export_creates_expected_layout(tmp_path):
    vault_dir = tmp_path / "vault"
    with MemoryTreeIndex(":memory:") as idx:
        _seed(idx)
        result = export_vault(idx, vault_dir)
    assert (vault_dir / "index.md").exists()
    assert (vault_dir / "artifacts").is_dir()
    assert (vault_dir / "summaries").is_dir()
    assert result.artifact_files
    assert result.index_file == "index.md"


def test_export_frontmatter_contains_provenance_and_redactions(tmp_path):
    vault_dir = tmp_path / "vault"
    with MemoryTreeIndex(":memory:") as idx:
        _seed(idx, with_secret=True)
        export_vault(idx, vault_dir)
    files = list((vault_dir / "artifacts").glob("*.md"))
    assert files
    body = files[0].read_text(encoding="utf-8")
    assert "---" in body
    assert "artifact_id" in body
    assert "redactions" in body
    assert "aws_access_key" in body
    # The secret itself must not be present.
    assert "AKIAIOSFODNN7EXAMPLE" not in body


def test_export_refuses_non_empty_dir_without_overwrite(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "existing.txt").write_text("hi", encoding="utf-8")
    with MemoryTreeIndex(":memory:") as idx:
        _seed(idx)
        with pytest.raises(FileExistsError):
            export_vault(idx, vault_dir)


def test_export_overwrite_allows_non_empty_dir(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "existing.txt").write_text("hi", encoding="utf-8")
    with MemoryTreeIndex(":memory:") as idx:
        _seed(idx)
        export_vault(idx, vault_dir, overwrite=True)
    assert (vault_dir / "index.md").exists()


def test_filenames_are_slugified_and_unique(tmp_path):
    vault_dir = tmp_path / "vault"
    with MemoryTreeIndex(":memory:") as idx:
        for i in range(3):
            artifact, cleaned = make_artifact(
                f"file://t{i}.md",
                f"# T{i}\n\nbody {i}.\n",
                kind="markdown",
                title="A Title With Spaces & Symbols!",
                created_at="2026-01-01T00:00:00Z",
            )
            idx.upsert_artifact(artifact)
            idx.upsert_chunks(chunk_text(artifact, cleaned))
        export_vault(idx, vault_dir)
    names = [p.name for p in (vault_dir / "artifacts").glob("*.md")]
    assert len(names) == 3
    assert len(set(names)) == 3
    for n in names:
        assert " " not in n
        assert "!" not in n


def test_no_summary_dir_when_disabled(tmp_path):
    vault_dir = tmp_path / "vault"
    with MemoryTreeIndex(":memory:") as idx:
        _seed(idx)
        result = export_vault(idx, vault_dir, include_summaries=False)
    assert result.summary_files == ()
    assert not (vault_dir / "summaries").exists()


def test_index_links_use_wiki_format(tmp_path):
    vault_dir = tmp_path / "vault"
    with MemoryTreeIndex(":memory:") as idx:
        _seed(idx)
        export_vault(idx, vault_dir)
    index_md = (vault_dir / "index.md").read_text(encoding="utf-8")
    assert "[[artifacts/" in index_md
