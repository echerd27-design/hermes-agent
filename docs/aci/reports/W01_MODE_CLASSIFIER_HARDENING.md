# Wave 01 — JARVIS Prime Mode Classifier Hardening

## Summary

JARVIS Prime sits above the AOS Council and routes every inbound
message into one of six operating modes defined in
`docs/jarvis-prime-operating-system.md`: Companion, Strategy, Critic,
Operator, Builder, Mobile Voice. Before this wave there was no
classifier on disk — ACI commands fell through to whatever ad-hoc
handling the caller wired up. This wave ships a deterministic,
stdlib-only classifier with 64 passing test assertions across the 16
real-world commands named in the brief plus 17 supplemental cases,
mobile-voice guard negatives, specialist extraction, tie-break order,
and API contract checks.

## Design notes

**Algorithm.** Normalize text (lowercase, strip punctuation, collapse
whitespace). Two scoring passes: a phrase pass (whole-word substring
match, default weight 3, weight 6 for red-team/contrarian "override"
phrases) and a token pass (weight 1 per single-word vocabulary hit).
A specialist-extraction pass populates `Classification.specialists` for
HazMat / Nourish / Logistics triggers and nudges Operator by 1. A
mobile-voice guard zeros the Mobile Voice score unless an explicit
voice/movement surface phrase or token was seen. Ties are resolved by
the documented priority chain
`MOBILE_VOICE -> BUILDER -> CRITIC -> STRATEGY -> OPERATOR -> COMPANION`.
If every mode scores 0 the result is Companion.

**Why scoring instead of regex routing.** A scoring model handles
co-occurring signals gracefully ("red team this monetization plan"
mixes a Critic override with a Strategy phrase — Critic wins because
its phrase weighs 6 vs Strategy's 3). Single-keyword routing would
either over-trigger or under-trigger depending on order.

**Mobile-voice guard.** The brief is explicit: no false route to Mobile
Voice unless a mobile/voice surface is present. Slack, Termux, and
Android-only are platform surfaces but not voice surfaces, so they are
deliberately excluded from `_MOBILE_VOICE_SURFACE_PHRASES /
_TOKENS`. "Hey Jay", "voice note", "from my phone", "while jogging",
"on the move", etc. all activate the surface.

**Red-team override.** "Red team", "tear apart", "challenge this",
"devil's advocate", "stress test", and "red-team" get phrase weight 6
so they win against a single co-occurring Strategy or Operator phrase
without needing a hard override branch.

**Stdlib only.** Imports: `re`, `enum`, `dataclasses`,
`collections.abc`. No LLM call, no third-party dependency, no I/O.

## Borderline decisions log

Resolved with the user during planning (Q&A round on 2026-05-26):

| Question | Decision |
|----------|----------|
| Where do specialist-activation keywords (HazMat Command, Nourish) route? | **Operator**, with the active specialist exposed via `Classification.specialists`. Reasoning: specialist activation is a coordination/routing action — JARVIS hands off to the specialist via the council. |
| `"production ready"` vs `"launch blockers"` | **production ready -> Critic** (readiness-risk question), **launch blockers -> Strategy** (positioning/scope question). |
| Branch name | `aci/wave-01-mode-classifier-hardening` — user-confirmed override of the harness default `claude/festive-fermat-bPIT0`. |

## Out-of-scope notes

- **`hermes_cli/jarvis_prime/__init__.py` was NOT created** because it
  was not on the ALLOWED FILES list for this wave. The module imports
  cleanly under Python 3.11 via PEP 420 implicit namespace packaging
  (a regular package may contain a namespace-package subdirectory) —
  the 64-test suite confirms this. Recommend a one-line follow-up wave
  to add an empty `__init__.py` for tooling friendliness (some
  linters / coverage tools still prefer explicit packages).
- **No edits made** to `gateway/**`, `apps/android/**`,
  `hermes_cli/main.py`, `pyproject.toml`, `uv.lock`, `README.md`, or
  GitHub workflows.

## Changed files

- `hermes_cli/jarvis_prime/modes.py` *(new, ~225 lines)*
- `tests/test_jarvis_prime_modes.py` *(new, 5 test suites, 64 assertions)*
- `docs/aci/reports/W01_MODE_CLASSIFIER_HARDENING.md` *(this report)*

## Tests run

```
$ python -m compileall hermes_cli/jarvis_prime/modes.py
Compiling 'hermes_cli/jarvis_prime/modes.py'...
(no errors)

$ pytest tests/test_jarvis_prime_modes.py -o addopts=""
============================== 64 passed in 1.06s ==============================
```

Note: the repo's `pyproject.toml` configures pytest with `-n` (xdist)
and `--timeout` (pytest-timeout) plugins; these were not present in the
isolated sandbox, so `-o addopts=""` was used to neutralize the
plugin-dependent options for the wave verification run. The tests
themselves do not depend on either plugin and will pass in the normal
project test runner as well.

## Acceptance criteria

| Requirement | Status |
|-------------|--------|
| Tests cover at least 30 example ACI commands | ✅ 33 parametrized real-world cases + 8 negative + 7 positive surface + 13 other suites = 64 assertions |
| No false route to mobile_voice unless mobile/voice surface present | ✅ Mobile-voice guard test exercises Slack / Termux / Android only / owner approval / open draft PR / ship it / route through AOS / fix build — none route to Mobile Voice |
| Builder commands route to Builder | ✅ audit repo, fix build, use Claude, use Codex, review PR, open draft PR, Android only, run tests, ship it, rebase main |
| Strategy commands route to Strategy | ✅ launch blockers, growth strategy, positioning, investor pitch (specialist co-mention falls back to Strategy) |
| Critic/red-team commands route to Critic | ✅ red team, tear apart, stress test, challenge this, production ready |
| Mobile capture commands route to Mobile Voice | ✅ Hey Jay, voice note, from my phone, while jogging, while driving, while walking, on the move |
| Stdlib-only, deterministic, no LLM | ✅ Only `re`, `enum`, `dataclasses`, `collections.abc` |

## Remaining risks

- Keyword false positives in long bodies of text. Example: "I love PR
  culture" would Builder-score on the `pr` token. Mitigation deferred —
  classifier is intentionally simple; long-form text should be
  pre-summarized before classification.
- Paraphrases miss. "Pull this branch and test it" doesn't fire on
  "pull" (not in vocabulary). Acceptable for an MVP that doesn't call
  an LLM; vocabulary can be extended in future waves as real corpus
  feedback comes in.
- Implicit namespace-package import quirk: a small minority of older
  packaging / coverage tools may not discover `hermes_cli.jarvis_prime`
  without the explicit `__init__.py`. See out-of-scope note above.

## Rollback

```
git revert <wave-commit-sha>
# or, since no merge to main occurred:
git push origin --delete aci/wave-01-mode-classifier-hardening
```

The classifier is additive — deleting `hermes_cli/jarvis_prime/modes.py`,
`tests/test_jarvis_prime_modes.py`, and this report restores the
pre-wave state. No existing imports anywhere in the repo depend on the
new module.

## PR summary

> Wave 01 — JARVIS Prime mode classifier hardening. Adds a
> deterministic, stdlib-only keyword-scoring classifier
> (`hermes_cli/jarvis_prime/modes.py`) that routes ACI commands into
> the six operating modes from
> `docs/jarvis-prime-operating-system.md`, plus a 64-assertion test
> suite (`tests/test_jarvis_prime_modes.py`) covering the 16
> brief-named commands, mobile-voice surface guards, specialist
> extraction, and tie-break order. No LLM calls, no new dependencies,
> no changes to forbidden surfaces. Draft PR only.
