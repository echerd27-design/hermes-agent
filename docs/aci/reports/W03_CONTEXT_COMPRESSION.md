# Wave 03 — JARVIS Prime Context Compression Helper

## Mission

Add a pure-stdlib, deterministic, secret-redacting context compression
helper that turns long, free-form JARVIS Prime handoff notes into a
bounded, section-structured packet usable by AOS specialists, Claude
Code, Codex, GitHub PR Publisher, Slack, Termux, and mobile voice
surfaces.

This wave ships the library + tests + report only. It does not wire the
helper into any existing call site; that integration is a later wave.

## Changed files

- `hermes_cli/jarvis_prime/__init__.py` — exports `compress_context` and
  `CompressedHandoff` for the `hermes_cli.jarvis_prime` package.
- `hermes_cli/jarvis_prime/context_compression.py` — the helper itself.
  Public surface: `compress_context(notes, *, char_limit=4000,
  redact_secrets=True) -> CompressedHandoff` and the frozen
  `CompressedHandoff` dataclass with `.as_dict()` and `.render()`.
- `tests/test_jarvis_prime_context_compression.py` — 23 unit tests
  covering string/list/dict input, redaction patterns, determinism,
  dedup, truncation, edge cases, and the package export.
- `docs/aci/reports/W03_CONTEXT_COMPRESSION.md` — this report.

Nothing else in the repository was modified. `pyproject.toml`,
`uv.lock`, `README.md`, `hermes_cli/__init__.py`, the gateway, the
android app, and every existing `memory.py` are untouched.

## Design summary

- Pure stdlib (`json`, `re`, `dataclasses`, `typing`). No new
  dependencies — the wave is forbidden from touching `pyproject.toml`.
- Deterministic by construction: frozen dataclass, tuples-of-strings,
  fixed section ordering, first-seen dedup, no clocks, no rng, no env
  reads.
- Secret redaction runs before classification AND on rendered output
  (truncation cannot leak credentials). Patterns cover OpenAI/Anthropic
  `sk-`, GitHub `ghp_` / `github_pat_`, Slack `xox[baprs]-`, AWS
  `AKIA…`, `Authorization: Bearer …` headers, URL credentials, and a
  generic `(api_key|secret|token|password|auth_token)=value` rule.
- `render()` output is bounded by `char_limit` (default 4000). When the
  packet exceeds the limit, list buckets are trimmed uniformly from the
  tail in a fixed rotation; scalars halve as a last resort. A
  no-forward-progress check guarantees termination even for
  `char_limit=0`.
- Modeled on the pure-helper pattern of `hermes_cli/session_recap.py`.

## Tests run

```bash
python -m pytest tests/test_jarvis_prime_context_compression.py -v
```

Result: **23 passed in 1.10s**.

```bash
python -m compileall -q hermes_cli/jarvis_prime
```

Result: clean exit.

End-to-end smoke (manual):

```bash
python -c "from hermes_cli.jarvis_prime import compress_context, \
  CompressedHandoff; h = compress_context('Mission: ship Wave 03.\n## \
  Decisions\n- use stdlib\nNext: review the diff'); print(h.render()); \
  assert isinstance(h, CompressedHandoff)"
```

Prints a structured handoff and exits 0.

## Remaining risks

- **No callers wired up.** This wave only adds the library. Until a
  later wave plugs `compress_context` into the Slack adapter, PR
  publisher, mobile voice handler, etc., the helper sits unused.
- **Redaction coverage is regex-bounded.** The patterns catch the most
  common credential shapes seen in this repo and in JARVIS handoffs,
  but they are not a vault scanner. Novel token shapes (e.g. custom
  enterprise tokens, JWTs that don't share a Bearer prefix) will pass
  through unredacted. Callers handling especially sensitive payloads
  should still pre-scrub.
- **Heuristic section classification.** When notes don't use the
  recognized heading or `Key:` anchors, content lands in the mission
  bucket (first line) or the files bucket (path-shaped tokens). The
  helper is best-effort, not an NLU.
- **`char_limit` smaller than the static frame.** The empty rendered
  frame (headings + `- (none)` lines) is ~250 chars. For
  `char_limit` smaller than that, the no-progress check fires and the
  helper returns a still-valid packet whose `render()` exceeds the
  limit. `truncated` is `True` in that case so callers can detect it.

## Rollback plan

This wave is purely additive. To revert:

```bash
rm -rf hermes_cli/jarvis_prime
rm tests/test_jarvis_prime_context_compression.py
rm docs/aci/reports/W03_CONTEXT_COMPRESSION.md
git checkout main
git branch -D claude/zealous-brahmagupta-oQlqA   # if local-only
```

No imports elsewhere in the repo reference the new package, no
dependencies were added, no shared config was touched.

## Owner gates

None triggered. The wave is local, additive, no external calls, no
public-facing claims, no automation, no release-relevant change.

## Next action

Open a follow-up wave to wire `compress_context` into the JARVIS Prime
handoff call sites: Slack adapter, GitHub PR Publisher, mobile voice
handler, and the AOS Council Director's specialist routing. Each
integration is a one- to three-line edit plus a small adapter test.

## PR summary (draft)

> Wave 03 adds `hermes_cli.jarvis_prime.compress_context` — a pure
> stdlib helper that turns long, free-form JARVIS handoff notes into a
> deterministic, secret-redacted, character-bounded packet. Includes
> 23 unit tests (string/list/dict input shapes, redaction patterns,
> determinism, dedup, truncation, edge cases) and a wave report. No
> dependency or call-site changes; the helper sits unused until a
> later wave plugs it into the Slack/PR/voice adapters.
