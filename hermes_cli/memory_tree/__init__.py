"""Jarvis Prime Memory Tree — isolated knowledge index.

Complements (does not replace) the existing JARVIS preference/mission/session
memory surface. Stores repo/project/document/job knowledge as artifacts,
chunks, and hierarchical summaries backed by stdlib sqlite3.

Not wired into runtime in this wave.
"""

from hermes_cli.memory_tree.artifacts import (
    Artifact,
    SecretContentError,
    make_artifact,
    redact_secrets,
)
from hermes_cli.memory_tree.chunker import Chunk, chunk_text
from hermes_cli.memory_tree.index import MemoryTreeIndex
from hermes_cli.memory_tree.retriever import (
    Retriever,
    RetrievalPacket,
    ScoredChunk,
    ScoredSummary,
)
from hermes_cli.memory_tree.summary_tree import Summary, build_summary_tree
from hermes_cli.memory_tree.vault import ExportResult, export_vault

__all__ = [
    "Artifact",
    "Chunk",
    "ExportResult",
    "MemoryTreeIndex",
    "RetrievalPacket",
    "Retriever",
    "ScoredChunk",
    "ScoredSummary",
    "SecretContentError",
    "Summary",
    "build_summary_tree",
    "chunk_text",
    "export_vault",
    "make_artifact",
    "redact_secrets",
]
