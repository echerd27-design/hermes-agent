"""Jarvis Prime context-compression engine (stdlib-only).

A stateless, pure-function payload compressor — different layer from the
in-runtime ``agent.context_engine`` plugin ABC and from the async
``trajectory_compressor`` LLM summarizer. See
``docs/aci/jarvis-prime/JARVIS_CONTEXT_ENGINE.md`` for the full design
rationale.
"""

from .context_engine import (
    COMPRESSORS,
    compress_diff,
    compress_json,
    compress_log,
    compress_markdown,
    compress_stack_trace,
    compress_test_output,
    compress_text,
)
from .context_packet import EVIDENCE_KINDS, SOURCE_TYPES, ContextPacket
from .redaction import SECRET_PATTERNS, reject, scrub

__all__ = [
    "ContextPacket",
    "SOURCE_TYPES",
    "EVIDENCE_KINDS",
    "compress_text",
    "compress_markdown",
    "compress_json",
    "compress_log",
    "compress_diff",
    "compress_test_output",
    "compress_stack_trace",
    "COMPRESSORS",
    "scrub",
    "reject",
    "SECRET_PATTERNS",
]
