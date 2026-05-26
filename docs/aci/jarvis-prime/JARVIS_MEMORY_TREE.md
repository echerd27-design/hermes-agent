# Jarvis Prime — Memory Tree

> **Status:** W12 foundation. Module built, not wired into runtime.

The Memory Tree is the knowledge memory for Jarvis Prime. It stores artifacts (documents, repo files, job descriptions, web pages), their chunked bodies, and hierarchical summaries. It is **isolated from** and **complementary to** the existing preference / mission / session memory surface.

## Why a second memory surface?

The repo already runs a conversational/session memory store across:

- `hermes_state.py` — SQLite state store with FTS5 search and context sanitisation.
- `agent/memory_manager.py` — context-window scoped memory and sanitisation.
- `agent/memory_provider.py` — runtime memory provider interface.
- `tools/memory_tool.py` — tool-callable read/write surface.
- `hermes_cli/memory_setup.py` — CLI wiring for the session store.

Those modules manage *what the agent currently knows about its user, mission, and conversation*. They are not designed to ingest hundreds of documents, chunk them, and answer ad-hoc keyword/semantic queries with provenance.

The Memory Tree adds that capability behind a stable, stdlib-only contract so a future wave can plug it into JARVIS without changing anything else.

## Non-overlap contract

The Memory Tree:

- Does **not** import from `hermes_state`, `agent/memory_*`, `tools/memory_tool`, or `hermes_cli/memory_setup`.
- Does **not** register itself with the runtime, router, or model registry in this wave.
- Does **not** expose any tool or skill yet.
- Lives entirely under `hermes_cli/memory_tree/` and uses only the Python standard library.

## Public API

```python
from hermes_cli.memory_tree import (
    Artifact, Chunk, Summary,
    MemoryTreeIndex, Retriever, RetrievalPacket,
    make_artifact, chunk_text, build_summary_tree, export_vault,
)
```

Typical lifecycle:

```python
artifact, cleaned = make_artifact(
    source_uri="file://docs/foo.md",
    content=raw_markdown,
    kind="markdown",
    title="Foo",
)
chunks = chunk_text(artifact, cleaned)
summaries = build_summary_tree(artifact, chunks)

with MemoryTreeIndex(Path("~/.hermes/memory_tree.db").expanduser()) as idx:
    idx.upsert_artifact(artifact)
    idx.upsert_chunks(chunks)
    for s in summaries:
        idx.upsert_summary(s)

    packet = Retriever(idx).retrieve("how does the indexer cascade deletes?")
    export_vault(idx, Path("~/Obsidian/JarvisVault").expanduser())
```

`RetrievalPacket` carries the query, the bounded list of `ScoredChunk` (with their parent `Artifact`), a `truncated` flag, and the total number of candidates considered. It is the unit a future wave will hand to JARVIS for grounding.

## Schema

Three first-class tables plus a version marker, all in `sqlite3`:

```
artifact ─┐
          │ FK (ON DELETE CASCADE)
          ▼
        chunk

summary  (scope ∈ {chunk, section, artifact}, scope_key → chunk_id or artifact_id)
schema_version
```

| Table | Key columns |
|-------|-------------|
| `artifact` | `artifact_id` PK, `source_uri`, `content_hash`, `kind`, `created_at`, `byte_size`, `title`, `provenance_json` |
| `chunk` | `chunk_id` PK, `artifact_id` FK, `ordinal`, `heading_path_json`, `text`, `byte_size`, `char_start`, `char_end` |
| `summary` | `summary_id` PK, `scope`, `scope_key`, `level`, `heading_path_json`, `text`, `child_ids_json`, `created_at` |
| `schema_version` | `version` PK (currently `1`) |

`PRAGMA foreign_keys = ON` always. `PRAGMA journal_mode = WAL` only for on-disk databases. `:memory:` skips WAL.

`MemoryTreeIndex.delete_artifact(id)` cascades chunks via the FK constraint and explicitly cleans up summaries (artifact-scope by `scope_key`, chunk-scope by chunk IDs collected before deletion) since summaries can roll up multiple artifacts in future waves and therefore aren't tied with an FK.

## Chunking semantics

`chunk_text(artifact, content, *, target_chars=1200, max_chars=2000)` returns deterministic `Chunk` records:

- **Markdown / doc** artifacts: split on ATX headings (`#`..`######`), maintain a heading stack so each chunk carries its full `heading_path`. Within a section, paragraphs are accumulated until the target budget; oversize paragraphs fall back to sentence boundaries and then hard-wrapping.
- **text / code / job** artifacts: paragraph + hard-wrap fallback, `heading_path = ()`.
- Every chunk respects `max_chars`. No chunk leaks past the artifact's character bounds.
- `chunk_id = "chk:" + sha256(artifact_id + ":" + ordinal + ":" + char_start + ":" + char_end)[:16]` — re-running on the same input yields the same IDs.

## Summary tree

`build_summary_tree(artifact, chunks)` produces three levels with no LLM call:

- **Level 0** — first sentence of each chunk, prefixed by its heading path.
- **Level 1** — per-section rollup: bullet list of sibling level-0 sentences, grouped by full heading path.
- **Level 2** — artifact rollup: title + source URI + ordered top-level headings.

Summary IDs are deterministic (`sum:<sha256[:16]>`). The function is pure — callers persist the records via `MemoryTreeIndex.upsert_summary`.

## Retrieval

`Retriever(index, max_chunks=8, max_chars=8000).retrieve(query, source_filter=None)`:

- Tokenises the query (stopwords removed, alphanumerics ≥2 chars, lowercased).
- Pulls candidate chunks via `MemoryTreeIndex.keyword_search` (term-frequency LIKE).
- Re-scores with small boosts for heading-path hits, title hits, and recency.
- Enforces the hard caps; sets `truncated=True` when the cap bites.
- `source_filter` accepts URI prefixes (`"file://"`, `"https://github.com/"`, …) or `kind` values (`"markdown"`, `"code"`).

This is intentionally a stopgap until a vector-backed retriever lands in a later wave. The packet shape is forward-compatible.

## Safety

- `redact_secrets(text)` scrubs AWS access/secret keys, Slack/GitHub/OpenAI/Anthropic tokens, JWTs, `Bearer …` headers, generic `password=` / `api_key=` patterns, and PEM private-key blocks. Order matters: Anthropic before OpenAI so `sk-ant-…` is correctly attributed.
- `make_artifact(..., redact=True)` runs the scrubber on ingest and records the firing tags in `provenance["redactions"]`.
- `make_artifact(..., redact=False)` raises `SecretContentError` if the content still trips a pattern — never silently store flagged material.
- The vault exporter writes the `redactions` list into each artifact's YAML frontmatter so downstream readers see what was removed.
- No network call, subprocess, or filesystem write beyond what the caller asks for.

## Vault export

`export_vault(index, target_dir, *, include_summaries=True, overwrite=False) -> ExportResult` writes an Obsidian-friendly layout:

```
target_dir/
  index.md                    # wiki-link table of contents
  artifacts/
    <slug>__<artifact_id>.md  # YAML frontmatter + rendered chunks
  summaries/
    <artifact_id>.md          # nested-bullet summary tree (when enabled)
```

Refuses non-empty target directories unless `overwrite=True`. Slugifies titles to `[\w-]+` and appends the artifact ID to guarantee filename uniqueness.

## Future wiring (out of scope this wave)

- A `MemoryTreeProvider` that adapts the retriever into the existing memory provider protocol.
- A `tools/knowledge_tool.py` exposing `query_memory_tree(query)` for tool calls.
- Background ingestion daemons for repo/Gmail/Slack content.
- Vector embeddings (the schema already has room for a sibling `embedding` table).
- FTS5 index alongside the LIKE-based keyword search.

These are intentionally deferred. The foundation in this wave is small, isolated, and reversible.

## Verification

```bash
pytest tests/test_memory_tree_*.py -q
python -m compileall hermes_cli/memory_tree
```
