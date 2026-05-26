"""Export the memory tree to an Obsidian-compatible Markdown vault."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hermes_cli.memory_tree.artifacts import Artifact
from hermes_cli.memory_tree.chunker import Chunk
from hermes_cli.memory_tree.index import MemoryTreeIndex
from hermes_cli.memory_tree.summary_tree import Summary


@dataclass(frozen=True)
class ExportResult:
    target_dir: str
    artifact_files: tuple[str, ...]
    summary_files: tuple[str, ...]
    index_file: str


def _slugify(value: str | None, fallback: str) -> str:
    base = value or fallback
    slug = re.sub(r"[^\w\-]+", "-", base).strip("-")
    return (slug[:64] or fallback)


def _yaml_value(v: object) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    text = str(v).replace("\n", " ").replace('"', '\\"')
    return f"\"{text}\""


def _frontmatter(artifact: Artifact) -> str:
    lines = ["---"]
    lines.append(f"artifact_id: {_yaml_value(artifact.artifact_id)}")
    lines.append(f"source_uri: {_yaml_value(artifact.source_uri)}")
    lines.append(f"source_path: {_yaml_value(artifact.source_path)}")
    lines.append(f"content_hash: {_yaml_value(artifact.content_hash)}")
    lines.append(f"kind: {_yaml_value(artifact.kind)}")
    lines.append(f"created_at: {_yaml_value(artifact.created_at)}")
    lines.append(f"byte_size: {artifact.byte_size}")
    lines.append(f"title: {_yaml_value(artifact.title)}")
    redactions = artifact.provenance.get("redactions") if artifact.provenance else None
    if redactions:
        lines.append(f"redactions: {_yaml_value(redactions)}")
    if artifact.provenance:
        lines.append("provenance:")
        for key, value in sorted(artifact.provenance.items()):
            lines.append(f"  {key}: {_yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def _render_chunk(chunk: Chunk) -> str:
    if chunk.heading_path:
        depth = min(len(chunk.heading_path), 6)
        heading = "#" * depth + " " + chunk.heading_path[-1]
        return f"{heading}\n\n{chunk.text}"
    return chunk.text


def _render_summaries(summaries: list[Summary]) -> str:
    if not summaries:
        return ""
    by_level: dict[int, list[Summary]] = {}
    for s in summaries:
        by_level.setdefault(s.level, []).append(s)
    out: list[str] = []
    for level in sorted(by_level):
        out.append(f"## Level {level}\n")
        for s in by_level[level]:
            path = " › ".join(s.heading_path) or "(root)"
            out.append(f"- **{path}**")
            for line in s.text.splitlines():
                out.append(f"  {line}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def export_vault(
    index: MemoryTreeIndex,
    target_dir: Path,
    *,
    include_summaries: bool = True,
    overwrite: bool = False,
) -> ExportResult:
    """Render artifacts/chunks/summaries into an Obsidian-friendly vault."""
    target = Path(target_dir)
    if target.exists() and any(target.iterdir()) and not overwrite:
        raise FileExistsError(f"target_dir {target} is not empty (pass overwrite=True)")

    artifacts_dir = target / "artifacts"
    summaries_dir = target / "summaries"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    if include_summaries:
        summaries_dir.mkdir(parents=True, exist_ok=True)

    artifact_files: list[str] = []
    summary_files: list[str] = []
    index_lines: list[str] = ["# Memory Tree Vault", ""]

    for artifact in index.iter_artifacts():
        chunks = list(index.iter_chunks(artifact.artifact_id))
        slug = _slugify(artifact.title, artifact.artifact_id.replace(":", "-"))
        fname = f"{slug}__{artifact.artifact_id.replace(':', '-')}.md"
        path = artifacts_dir / fname
        body = [_frontmatter(artifact), ""]
        for chunk in chunks:
            body.append(_render_chunk(chunk))
            body.append("")
        path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
        artifact_files.append(str(path.relative_to(target)))
        index_lines.append(f"- [[artifacts/{fname}|{artifact.title or artifact.artifact_id}]]")

        if include_summaries:
            summaries = [s for s in index.iter_summaries() if s.scope_key == artifact.artifact_id or (
                s.scope == "chunk" and s.scope_key in {c.chunk_id for c in chunks}
            )]
            if summaries:
                sfname = f"{artifact.artifact_id.replace(':', '-')}.md"
                spath = summaries_dir / sfname
                rendered = _render_summaries(summaries)
                spath.write_text(
                    f"# Summary — {artifact.title or artifact.artifact_id}\n\n{rendered}",
                    encoding="utf-8",
                )
                summary_files.append(str(spath.relative_to(target)))

    index_path = target / "index.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    return ExportResult(
        target_dir=str(target),
        artifact_files=tuple(artifact_files),
        summary_files=tuple(summary_files),
        index_file=str(index_path.relative_to(target)),
    )


__all__ = ["ExportResult", "export_vault"]
