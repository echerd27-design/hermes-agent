"""ContextPacket — frozen dataclass returned by every compressor.

Carries the compressed payload, length metadata, the typed evidence the
compressor was required to preserve verbatim, engine-side warnings, and an
optional opaque pointer to a full-fidelity stash the producer kept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


SOURCE_TYPES = (
    "text",
    "markdown",
    "json",
    "log",
    "diff",
    "test_output",
    "stack_trace",
)


EVIDENCE_KINDS = (
    "file_path",
    "line_ref",
    "function_name",
    "test_id",
    "error_message",
    "stack_frame",
    "security_warning",
    "owner_gate",
)


@dataclass(frozen=True)
class ContextPacket:
    source_type: str
    payload: str
    original_length: int
    compressed_length: int
    preserved_evidence: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    artifact_ref: str | None = None

    @property
    def compression_ratio(self) -> float:
        if self.original_length <= 0:
            return 1.0
        return self.compressed_length / self.original_length

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "payload": self.payload,
            "original_length": self.original_length,
            "compressed_length": self.compressed_length,
            "preserved_evidence": [list(pair) for pair in self.preserved_evidence],
            "warnings": list(self.warnings),
            "artifact_ref": self.artifact_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContextPacket":
        evidence_raw = data.get("preserved_evidence", ()) or ()
        evidence = tuple(
            (str(pair[0]), str(pair[1]))
            for pair in evidence_raw
            if pair and len(pair) >= 2
        )
        warnings_raw = data.get("warnings", ()) or ()
        warnings = tuple(str(w) for w in warnings_raw)
        return cls(
            source_type=str(data["source_type"]),
            payload=str(data["payload"]),
            original_length=int(data["original_length"]),
            compressed_length=int(data["compressed_length"]),
            preserved_evidence=evidence,
            warnings=warnings,
            artifact_ref=(
                None if data.get("artifact_ref") is None else str(data["artifact_ref"])
            ),
        )
