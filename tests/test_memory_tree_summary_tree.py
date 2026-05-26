"""Tests for hermes_cli.memory_tree.summary_tree."""

from __future__ import annotations

import socket
import sys
from unittest import mock

from hermes_cli.memory_tree.artifacts import make_artifact
from hermes_cli.memory_tree.chunker import chunk_text
from hermes_cli.memory_tree.summary_tree import build_summary_tree


def _build(content: str, title: str | None = "Doc"):
    artifact, cleaned = make_artifact(
        "file://t.md",
        content,
        kind="markdown",
        title=title,
        created_at="2026-01-01T00:00:00Z",
    )
    chunks = chunk_text(artifact, cleaned)
    return artifact, chunks, build_summary_tree(artifact, chunks)


def test_summary_ids_deterministic():
    artifact, chunks, s1 = _build("# T\n\nalpha. body.\n\n## S\n\nbeta. body.\n")
    s2 = build_summary_tree(artifact, chunks)
    assert [s.summary_id for s in s1] == [s.summary_id for s in s2]
    assert all(s.summary_id.startswith("sum:") for s in s1)


def test_levels_present():
    _, _, summaries = _build("# T\n\nfirst. another.\n\n## S\n\ndeeper. more.\n")
    levels = {s.level for s in summaries}
    assert levels == {0, 1, 2}


def test_level0_first_sentence_extraction():
    _, _, summaries = _build("# T\n\nFirst sentence here. Second sentence ignored.\n")
    l0 = [s for s in summaries if s.level == 0]
    assert l0
    assert any("First sentence here." in s.text for s in l0)
    assert not any("Second sentence" in s.text for s in l0)


def test_level2_includes_title_and_top_headings():
    _, _, summaries = _build(
        "# Alpha\n\nbody.\n\n## Sub\n\nbody.\n\n# Bravo\n\nbody.\n",
        title="My Doc",
    )
    l2 = [s for s in summaries if s.level == 2]
    assert len(l2) == 1
    body = l2[0].text
    assert "My Doc" in body
    assert "Alpha" in body
    assert "Bravo" in body


def test_summary_tree_does_not_open_network():
    fake_socket = mock.create_autospec(socket.socket, instance=False)
    fake_socket.side_effect = AssertionError("summary_tree must not open sockets")
    with mock.patch.object(socket, "socket", fake_socket):
        _build("# T\n\nbody one. body two.\n\n## S\n\nbody three.\n")
    fake_socket.assert_not_called()


def test_summary_tree_does_not_import_urllib_lazily():
    # Confirm summary_tree itself does not pull in urllib request at runtime.
    before = set(sys.modules)
    _build("# T\n\nbody.\n")
    new = set(sys.modules) - before
    assert not any(name.startswith("urllib.request") for name in new)


def test_child_ids_link_levels():
    _, _, summaries = _build("# Top\n\nalpha. beta.\n\n## Sub\n\ngamma. delta.\n")
    l0_ids = {s.summary_id for s in summaries if s.level == 0}
    l1 = [s for s in summaries if s.level == 1]
    assert l1
    for s in l1:
        for cid in s.child_ids:
            assert cid in l0_ids


def test_empty_content_yields_only_artifact_level():
    artifact, _ = make_artifact(
        "file://t.md",
        "",
        kind="markdown",
        title="Empty",
        created_at="2026-01-01T00:00:00Z",
    )
    summaries = build_summary_tree(artifact, [])
    assert [s.level for s in summaries] == [2]
