"""Evidence evaluator: gate patch/test evidence against a WorkPacket."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .patch_engine import Patch, PatchValidationResult
from .test_runner import TestResult
from .work_packet import WorkPacket


@dataclass(frozen=True)
class Evidence:
    patches: tuple[Patch, ...] = field(default_factory=tuple)
    validations: tuple[PatchValidationResult, ...] = field(default_factory=tuple)
    test_results: tuple[TestResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reasons: tuple[str, ...]
    missing: tuple[str, ...]


def _make_evidence_from_iterables(
    patches: Iterable[Patch],
    validations: Iterable[PatchValidationResult],
    test_results: Iterable[TestResult],
) -> Evidence:
    return Evidence(
        patches=tuple(patches),
        validations=tuple(validations),
        test_results=tuple(test_results),
    )


def evaluate(packet: WorkPacket, evidence: Evidence) -> Verdict:
    reasons: list[str] = []
    missing: list[str] = []

    rejected = [v for v in evidence.validations if not v.allowed]
    if rejected:
        for v in rejected:
            reasons.append(f"validation rejected {v.patch.target_path}: {v.reason}")

    green_runs = [t for t in evidence.test_results if t.returncode == 0]
    meta = packet.metadata_dict()
    skip_reason = meta.get("test_skip_reason", "")
    if not green_runs and not skip_reason:
        reasons.append("no green test result and no test_skip_reason metadata")

    rationale_corpus = " ".join(
        (p.rationale or "").lower() for p in evidence.patches
    )
    metadata_corpus = " ".join(v.lower() for _, v in packet.metadata)
    haystack = rationale_corpus + " " + metadata_corpus

    for criterion in packet.acceptance_criteria:
        token = criterion.strip().lower()
        if not token:
            continue
        if token not in haystack:
            missing.append(criterion)

    if missing:
        reasons.append(
            "acceptance criteria not referenced in patch rationales or metadata: "
            + "; ".join(missing)
        )

    passed = not rejected and (bool(green_runs) or bool(skip_reason)) and not missing
    return Verdict(passed=passed, reasons=tuple(reasons), missing=tuple(missing))
