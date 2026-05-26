"""SOP miner: turn a successful job into a reusable record."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .patch_engine import Patch
from .test_runner import TestResult
from .work_packet import WorkPacket


@dataclass(frozen=True)
class SOPRecord:
    title: str
    mission_summary: str
    branch: str
    steps: tuple[str, ...]
    verification: tuple[str, ...]
    artifacts: tuple[str, ...]
    tags: tuple[str, ...]


def _derive_tags(
    packet: WorkPacket, artifacts: tuple[str, ...]
) -> tuple[str, ...]:
    tags: list[str] = []
    seen: set[str] = set()

    for key, value in packet.metadata:
        if key.lower() == "tag" or key.lower() == "tags":
            for raw in str(value).split(","):
                token = raw.strip()
                if token and token not in seen:
                    tags.append(token)
                    seen.add(token)

    def add(tag: str) -> None:
        if tag not in seen:
            tags.append(tag)
            seen.add(tag)

    for path in artifacts:
        if path.startswith("apps/android/"):
            add("android")
        if path.startswith("docs/"):
            add("docs")
        if path.startswith("tests/"):
            add("tests")
        if path.startswith("hermes_cli/"):
            add("hermes_cli")

    return tuple(tags)


def mine(
    packet: WorkPacket,
    patches: Iterable[Patch],
    test_results: Iterable[TestResult],
) -> SOPRecord:
    patch_list = list(patches)
    # Reference test_results to make the dependency explicit even if unused
    # in field derivation; future tuning may consume timing/counters.
    _ = list(test_results)

    title = packet.mission[:80] if packet.mission else "(untitled)"
    steps = tuple(
        f"[{p.operation}] {p.target_path}: {p.rationale}" for p in patch_list
    )
    artifacts = tuple(sorted({p.target_path for p in patch_list}))
    tags = _derive_tags(packet, artifacts)

    return SOPRecord(
        title=title,
        mission_summary=packet.mission,
        branch=packet.branch,
        steps=steps,
        verification=tuple(packet.verification_commands),
        artifacts=artifacts,
        tags=tags,
    )


def to_markdown(record: SOPRecord) -> str:
    lines: list[str] = []
    lines.append(f"# SOP: {record.title}")
    lines.append("")
    lines.append(f"**Branch:** `{record.branch}`")
    if record.tags:
        lines.append(f"**Tags:** {', '.join(record.tags)}")
    lines.append("")
    lines.append("## Mission")
    lines.append(record.mission_summary or "(no mission summary)")
    lines.append("")
    lines.append("## Steps")
    if record.steps:
        for step in record.steps:
            lines.append(f"- {step}")
    else:
        lines.append("- (no steps recorded)")
    lines.append("")
    lines.append("## Verification")
    if record.verification:
        for cmd in record.verification:
            lines.append(f"- `{cmd}`")
    else:
        lines.append("- (no verification commands)")
    lines.append("")
    lines.append("## Artifacts")
    if record.artifacts:
        for art in record.artifacts:
            lines.append(f"- `{art}`")
    else:
        lines.append("- (no artifacts)")
    lines.append("")
    return "\n".join(lines)
