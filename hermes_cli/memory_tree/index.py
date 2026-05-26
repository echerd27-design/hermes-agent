"""SQLite-backed index for artifacts, chunks, and summaries.

Stdlib-only, synchronous, single-writer assumption. Designed for the
isolated foundation: callers manage lifecycle via context manager.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Iterable, Iterator, Sequence

from hermes_cli.memory_tree.artifacts import Artifact
from hermes_cli.memory_tree.chunker import Chunk

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);

CREATE TABLE IF NOT EXISTS artifact (
    artifact_id   TEXT PRIMARY KEY,
    source_uri    TEXT NOT NULL,
    source_path   TEXT,
    content_hash  TEXT NOT NULL,
    kind          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    byte_size     INTEGER NOT NULL,
    title         TEXT,
    provenance_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunk (
    chunk_id          TEXT PRIMARY KEY,
    artifact_id       TEXT NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,
    ordinal           INTEGER NOT NULL,
    heading_path_json TEXT NOT NULL,
    text              TEXT NOT NULL,
    byte_size         INTEGER NOT NULL,
    char_start        INTEGER NOT NULL,
    char_end          INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunk_artifact_ordinal ON chunk(artifact_id, ordinal);

CREATE TABLE IF NOT EXISTS summary (
    summary_id        TEXT PRIMARY KEY,
    scope             TEXT NOT NULL,
    scope_key         TEXT NOT NULL,
    level             INTEGER NOT NULL,
    heading_path_json TEXT NOT NULL,
    text              TEXT NOT NULL,
    child_ids_json    TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_summary_scope ON summary(scope, scope_key);
"""


_TOKEN_RE = re.compile(r"[A-Za-z0-9]{2,}")


def _tokenise(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class MemoryTreeIndex(AbstractContextManager["MemoryTreeIndex"]):
    """Thin sqlite3 wrapper. Use as a context manager."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self._is_memory = self._db_path == ":memory:"
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------ lifecycle
    def __enter__(self) -> "MemoryTreeIndex":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def open(self) -> None:
        if self._conn is not None:
            return
        conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if not self._is_memory:
            conn.execute("PRAGMA journal_mode = WAL")
        with conn:
            conn.executescript(_SCHEMA)
            cur = conn.execute("SELECT version FROM schema_version")
            row = cur.fetchone()
            if row is None:
                conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("MemoryTreeIndex is not open")
        return self._conn

    # ------------------------------------------------------------------ writes
    def upsert_artifact(self, artifact: Artifact) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO artifact(artifact_id, source_uri, source_path, content_hash,
                                     kind, created_at, byte_size, title, provenance_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    source_uri=excluded.source_uri,
                    source_path=excluded.source_path,
                    content_hash=excluded.content_hash,
                    kind=excluded.kind,
                    created_at=excluded.created_at,
                    byte_size=excluded.byte_size,
                    title=excluded.title,
                    provenance_json=excluded.provenance_json
                """,
                (
                    artifact.artifact_id,
                    artifact.source_uri,
                    artifact.source_path,
                    artifact.content_hash,
                    artifact.kind,
                    artifact.created_at,
                    artifact.byte_size,
                    artifact.title,
                    json.dumps(dict(artifact.provenance), sort_keys=True),
                ),
            )

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> int:
        rows = [
            (
                c.chunk_id,
                c.artifact_id,
                c.ordinal,
                json.dumps(list(c.heading_path)),
                c.text,
                c.byte_size,
                c.char_start,
                c.char_end,
            )
            for c in chunks
        ]
        if not rows:
            return 0
        with self.conn:
            self.conn.executemany(
                """
                INSERT INTO chunk(chunk_id, artifact_id, ordinal, heading_path_json,
                                  text, byte_size, char_start, char_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    artifact_id=excluded.artifact_id,
                    ordinal=excluded.ordinal,
                    heading_path_json=excluded.heading_path_json,
                    text=excluded.text,
                    byte_size=excluded.byte_size,
                    char_start=excluded.char_start,
                    char_end=excluded.char_end
                """,
                rows,
            )
        return len(rows)

    def upsert_summary(self, summary: "object") -> None:
        # Imported lazily to avoid an import cycle (summary_tree imports chunker).
        from hermes_cli.memory_tree.summary_tree import Summary

        if not isinstance(summary, Summary):
            raise TypeError("expected Summary instance")
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO summary(summary_id, scope, scope_key, level, heading_path_json,
                                    text, child_ids_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(summary_id) DO UPDATE SET
                    scope=excluded.scope,
                    scope_key=excluded.scope_key,
                    level=excluded.level,
                    heading_path_json=excluded.heading_path_json,
                    text=excluded.text,
                    child_ids_json=excluded.child_ids_json,
                    created_at=excluded.created_at
                """,
                (
                    summary.summary_id,
                    summary.scope,
                    summary.scope_key,
                    summary.level,
                    json.dumps(list(summary.heading_path)),
                    summary.text,
                    json.dumps(list(summary.child_ids)),
                    summary.created_at,
                ),
            )

    def delete_artifact(self, artifact_id: str) -> None:
        with self.conn:
            chunk_ids = [
                row[0]
                for row in self.conn.execute(
                    "SELECT chunk_id FROM chunk WHERE artifact_id = ?", (artifact_id,)
                )
            ]
            self.conn.execute("DELETE FROM artifact WHERE artifact_id = ?", (artifact_id,))
            # Summaries have no FK to chunks/artifacts (future waves may roll up
            # multiple artifacts), so clean them up explicitly.
            self.conn.execute(
                "DELETE FROM summary WHERE scope_key = ?", (artifact_id,)
            )
            if chunk_ids:
                placeholders = ",".join("?" * len(chunk_ids))
                self.conn.execute(
                    f"DELETE FROM summary WHERE scope = 'chunk' AND scope_key IN ({placeholders})",
                    chunk_ids,
                )

    # ------------------------------------------------------------------ reads
    def get_artifact(self, artifact_id: str) -> Artifact | None:
        row = self.conn.execute(
            "SELECT * FROM artifact WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            return None
        return Artifact(
            artifact_id=row["artifact_id"],
            source_uri=row["source_uri"],
            source_path=row["source_path"],
            content_hash=row["content_hash"],
            kind=row["kind"],
            created_at=row["created_at"],
            byte_size=row["byte_size"],
            title=row["title"],
            provenance=json.loads(row["provenance_json"]),
        )

    def iter_artifacts(self) -> Iterator[Artifact]:
        for row in self.conn.execute("SELECT * FROM artifact ORDER BY created_at, artifact_id"):
            yield Artifact(
                artifact_id=row["artifact_id"],
                source_uri=row["source_uri"],
                source_path=row["source_path"],
                content_hash=row["content_hash"],
                kind=row["kind"],
                created_at=row["created_at"],
                byte_size=row["byte_size"],
                title=row["title"],
                provenance=json.loads(row["provenance_json"]),
            )

    def iter_chunks(self, artifact_id: str | None = None) -> Iterator[Chunk]:
        if artifact_id is None:
            cur = self.conn.execute("SELECT * FROM chunk ORDER BY artifact_id, ordinal")
        else:
            cur = self.conn.execute(
                "SELECT * FROM chunk WHERE artifact_id = ? ORDER BY ordinal",
                (artifact_id,),
            )
        for row in cur:
            yield Chunk(
                chunk_id=row["chunk_id"],
                artifact_id=row["artifact_id"],
                ordinal=row["ordinal"],
                heading_path=tuple(json.loads(row["heading_path_json"])),
                text=row["text"],
                byte_size=row["byte_size"],
                char_start=row["char_start"],
                char_end=row["char_end"],
            )

    def iter_summaries(self, scope: str | None = None) -> Iterator["object"]:
        from hermes_cli.memory_tree.summary_tree import Summary

        if scope is None:
            cur = self.conn.execute("SELECT * FROM summary ORDER BY scope, scope_key, level")
        else:
            cur = self.conn.execute(
                "SELECT * FROM summary WHERE scope = ? ORDER BY scope_key, level",
                (scope,),
            )
        for row in cur:
            yield Summary(
                summary_id=row["summary_id"],
                scope=row["scope"],
                scope_key=row["scope_key"],
                level=row["level"],
                heading_path=tuple(json.loads(row["heading_path_json"])),
                text=row["text"],
                child_ids=tuple(json.loads(row["child_ids_json"])),
                created_at=row["created_at"],
            )

    def keyword_search(
        self,
        terms: Sequence[str],
        limit: int = 50,
        *,
        source_filter: Sequence[str] | None = None,
    ) -> list[tuple[Chunk, Artifact, int]]:
        """Naïve TF-style search.

        Returns up to `limit` (chunk, artifact, term_frequency) tuples ordered by
        descending frequency. Filtering by `source_filter` keeps only artifacts
        whose `source_uri` starts with one of the prefixes or whose `kind`
        matches one of the values.
        """
        lowered = [t.lower() for t in terms if t]
        if not lowered:
            return []

        like_clauses = " OR ".join(["LOWER(text) LIKE ?"] * len(lowered))
        like_args = [f"%{t}%" for t in lowered]
        sql = f"""
            SELECT chunk.*
            FROM chunk
            WHERE {like_clauses}
        """
        cur = self.conn.execute(sql, like_args)
        candidates: list[tuple[Chunk, int]] = []
        for row in cur:
            text_lower = row["text"].lower()
            tf = sum(text_lower.count(t) for t in lowered)
            if tf == 0:
                continue
            chunk = Chunk(
                chunk_id=row["chunk_id"],
                artifact_id=row["artifact_id"],
                ordinal=row["ordinal"],
                heading_path=tuple(json.loads(row["heading_path_json"])),
                text=row["text"],
                byte_size=row["byte_size"],
                char_start=row["char_start"],
                char_end=row["char_end"],
            )
            candidates.append((chunk, tf))

        results: list[tuple[Chunk, Artifact, int]] = []
        for chunk, tf in candidates:
            artifact = self.get_artifact(chunk.artifact_id)
            if artifact is None:
                continue
            if source_filter:
                hit = any(
                    artifact.source_uri.startswith(s) or artifact.kind == s
                    for s in source_filter
                )
                if not hit:
                    continue
            results.append((chunk, artifact, tf))

        results.sort(key=lambda triple: triple[2], reverse=True)
        return results[:limit]

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT version FROM schema_version").fetchone()
        return int(row["version"]) if row else 0


__all__ = ["MemoryTreeIndex", "SCHEMA_VERSION"]
