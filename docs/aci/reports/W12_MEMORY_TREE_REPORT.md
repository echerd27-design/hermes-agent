# W12 — Memory Tree Core: Sprint Report

**Mission:** Build the isolated Jarvis Prime Memory Tree backend foundation.

**Branch (development):** `claude/tender-davinci-H4uej`
**Branch (sprint alias, also pushed):** `aci/jarvis-prime-12-memory-tree-core`
**PR target:** `echerd27-design/hermes-agent:main` (draft).

## Changed files

```
hermes_cli/memory_tree/__init__.py
hermes_cli/memory_tree/artifacts.py
hermes_cli/memory_tree/chunker.py
hermes_cli/memory_tree/index.py
hermes_cli/memory_tree/retriever.py
hermes_cli/memory_tree/summary_tree.py
hermes_cli/memory_tree/vault.py
tests/test_memory_tree_artifacts.py
tests/test_memory_tree_chunker.py
tests/test_memory_tree_index.py
tests/test_memory_tree_retriever.py
tests/test_memory_tree_summary_tree.py
tests/test_memory_tree_vault.py
tests/test_memory_tree_integration.py
docs/aci/jarvis-prime/JARVIS_MEMORY_TREE.md
docs/aci/reports/W12_MEMORY_TREE_REPORT.md
```

All paths fall inside the sprint's ALLOWED FILES list. No FORBIDDEN file was modified.

## Tests run

```
uv run --extra dev python -m pytest tests/test_memory_tree_*.py -q
→ 59 passed in 2.04s
python -m compileall hermes_cli/memory_tree
→ OK
```

Suite breakdown:

| File | Cases | Focus |
|------|-------|-------|
| `test_memory_tree_artifacts.py` | 16 | ID determinism, secret redaction across 9 patterns, provenance, `SecretContentError` raise path |
| `test_memory_tree_chunker.py` | 8 | Heading-path preservation, deterministic IDs, ordinal monotonicity, `max_chars` enforcement, validation |
| `test_memory_tree_index.py` | 8 | Schema version, WAL pragma (only on-disk), idempotent upserts, FK + summary cascade, keyword search ranking & filtering |
| `test_memory_tree_retriever.py` | 8 | Stopword tokenisation, heading/title boosts, `max_chunks` and `max_chars` budgets, `source_filter`, no-candidate path |
| `test_memory_tree_summary_tree.py` | 7 | Deterministic summary IDs, level-0/1/2 rollups, child-id linkage, no-network guarantee, empty-content handling |
| `test_memory_tree_vault.py` | 7 | Layout, frontmatter + redactions, refuse / overwrite semantics, slug uniqueness, optional summaries, wiki-link index |
| `test_memory_tree_integration.py` | 1 | End-to-end ingest → chunk → index → summarise → retrieve → export |

## Acceptance criteria — confirmed

- [x] Stdlib-only (no new dependency added; uses `sqlite3`, `hashlib`, `re`, `dataclasses`, `pathlib`, `json`, `datetime`).
- [x] Tests cover artifact creation, chunking, SQLite indexing, retrieval, vault export, and secret redaction.
- [x] No modification to the existing memory surface (`hermes_state.py`, `agent/memory_*.py`, `tools/memory_tool.py`, `hermes_cli/memory_setup.py`).
- [x] Not wired into JARVIS runtime / router / registry.

## Risks

- **Pattern false-positives.** The secret-redaction regexes are intentionally conservative. They will miss exotic token shapes (custom Vault tokens, internal credential formats). Mitigation: provenance tags every redaction so reviewers can audit; future waves should add a configurable allow/deny pattern set.
- **Keyword-only retrieval.** `Retriever` uses `LIKE` + term-frequency, no FTS5, no embeddings. Recall on phrasing variants will be weaker than a vector store. Mitigation: API shape (`RetrievalPacket`) is forward-compatible; vector + FTS5 backends can be added without breaking callers.
- **Markdown chunker is heading-driven.** Documents without headings will fall back to paragraph splitting; very dense code/text files may produce chunks that approach `max_chars`. Mitigation: hard cap enforced; tests cover the fallback path.
- **Schema is v1.** Migrations beyond v1 will need a real migration step (the `schema_version` table is in place but no upgrade machinery yet).

## Rollback

Single revert. Delete:

```
hermes_cli/memory_tree/
tests/test_memory_tree_*.py
docs/aci/jarvis-prime/JARVIS_MEMORY_TREE.md
docs/aci/reports/W12_MEMORY_TREE_REPORT.md
```

No other files touched, no schema in production, no runtime wiring → no fallout.

## Draft PR summary (for the GitHub draft PR body)

- Adds the isolated `hermes_cli/memory_tree/` package (artifacts, chunker, sqlite index, retriever, summary tree, vault export).
- 59-case pytest suite, stdlib-only, no new dependencies.
- Not wired into JARVIS runtime; future wave will add a provider/tool adapter.
- Sprint design + safety contract documented at `docs/aci/jarvis-prime/JARVIS_MEMORY_TREE.md`.

## Sprint contract divergences (recorded per non-overlap clause)

Three divergences from the sprint header, resolved with the user before implementation:

1. **Branch dual-push.** Harness mandates development on `claude/tender-davinci-H4uej`; sprint header specifies `aci/jarvis-prime-12-memory-tree-core`. Per user decision, work was developed on the harness branch and pushed to both names; PR opens from one of them.
2. **Forbidden-list expansion.** The sprint's literal FORBIDDEN paths (`hermes_cli/jarvis_prime/memory.py`, `runtime.py`, `router.py`) do not exist in this repo — the actual memory surface lives at `hermes_state.py`, `agent/memory_*.py`, `tools/memory_tool.py`, `hermes_cli/memory_setup.py`. Per user decision, the *spirit* of the non-overlap contract was applied: none of those files were modified.
3. **Upstream-repo mismatch.** Sprint targets `A-C-I-SOFTWARE-AND-DEVELOPMENT/hermes-agent`. MCP scope only permits `echerd27-design/hermes-agent`. Per user decision, the draft PR opens against `echerd27-design/hermes-agent`.

## Open questions

None blocking. The future-wiring section of the design doc lists deferred work for the next wave.
