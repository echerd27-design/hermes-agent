# Wave 01 — JARVIS Prime Mode Classifier Hardening

## Summary

JARVIS Prime sits above the AOS Council and routes every inbound
message into an operating mode. Before this wave there was no
classifier on disk — ACI commands fell through to whatever ad-hoc
handling the caller wired up. This wave ships a deterministic,
stdlib-only classifier with 65 passing test assertions covering all
16 real-world commands named in the brief plus 18 supplemental cases
across mobile-voice guard, specialist extraction, tie-break order, and
API contract checks.

The classifier ships with **five modes** (the set named in the Wave 01
acceptance criteria): Companion, Strategy, Critic, Builder, Mobile
Voice. The JARVIS Prime doc lists six modes including Operator; per
user direction during planning, Operator was folded into Builder
(routing, specialist activation, surface coordination) and Strategy
(owner-gate decisions). Specialist activations (HazMat / Nourish /
Logistics) are still surfaced separately via
`Classification.specialists` so callers can run the specialist alongside
the chosen mode.

## Design notes

**Algorithm.** Normalize text (lowercase, strip punctuation, collapse
whitespace). Two scoring passes: a phrase pass (whole-word substring
match, default weight 3, weight 6 for red-team/contrarian "override"
phrases) and a token pass (weight 1 per single-word vocabulary hit).
A specialist-extraction pass populates `Classification.specialists` for
HazMat / Nourish / Logistics triggers and nudges Builder by 1. A
mobile-voice guard zeros the Mobile Voice score unless an explicit
voice/movement surface phrase or token was seen. Ties resolve via the
priority chain
`MOBILE_VOICE -> BUILDER -> CRITIC -> STRATEGY -> COMPANION`.
If every mode scores 0, the result is Companion.

**Why scoring instead of regex routing.** A scoring model handles
co-occurring signals gracefully ("red team this monetization plan"
mixes a Critic override with a Strategy phrase — Critic wins because
its phrase weighs 6 vs Strategy's 3). Single-keyword routing would
either over-trigger or under-trigger depending on order.

**Mobile-voice guard.** The brief is explicit: no false route to Mobile
Voice unless a mobile/voice surface is present. Slack, Termux, and
Android-only are platform surfaces but not voice surfaces, so they are
deliberately excluded from the surface set. "Hey Jay", "voice note",
"from my phone", "while jogging", "on the move", etc. all activate the
surface.

**Red-team override.** "Red team", "tear apart", "challenge this",
"devil's advocate", "stress test", and "red-team" get phrase weight 6
so they win against a single co-occurring Strategy or Builder phrase
without needing a hard override branch.

**Strategy-heavy bias.** Per user clarification, ambiguous
launch/readiness language routes to Strategy:
- `"production ready"` → Strategy (was originally drafted as Critic)
- `"launch blockers"` → Strategy
- `"owner approval"` → Strategy (decision-making moment)

**Stdlib only.** Imports: `re`, `enum`, `dataclasses`,
`collections.abc`. No LLM call, no third-party dependency, no I/O.

## Borderline decisions log

Resolved with the user during planning + post-PR clarification:

| Question | Decision |
|----------|----------|
| Where do specialist-activation keywords (HazMat Command, Nourish) route? | **Builder**, with the active specialist also exposed via `Classification.specialists`. (Original plan said Operator → Builder/Strategy fold collapsed this to Builder.) |
| `"production ready"` routing | **Strategy** (was originally Critic). Strategy-heavy bias treats readiness as a launch/business call. |
| `"launch blockers"` routing | **Strategy** (positioning/scope question). |
| `"owner approval"` routing | **Strategy** (the decision-making moment that an owner gate represents). |
| `"route through AOS"`, `"HazMat Command"`, `"Termux"`, `"Slack"`, `"activate the council"` | **Builder** (concrete coordination/execution surfaces). |
| Operator as a separate mode? | **No** — folded into Builder + Strategy. The Wave 01 acceptance criteria explicitly name five modes (Builder, Strategy, Critic, Mobile Voice, Companion). |
| API shape | `Classification` dataclass returning the winning `Mode`, per-mode score map, per-mode matched-keyword tuples, and a `specialists` tuple. |
| Branch name | `aci/wave-01-mode-classifier-hardening` — user-confirmed override of the harness default. |

## Out-of-scope notes

- **`hermes_cli/jarvis_prime/__init__.py` was added in a follow-up
  commit.** The wave's first push omitted it on the theory that
  PEP 420 implicit namespace packaging would let CI find the new
  subpackage. The `test` CI job then failed at collection time
  (`hermes_cli.jarvis_prime` was not resolvable under the parent
  regular package). The fix is a one-file addition that re-exports
  the public surface (`Mode`, `Classification`, `classify`,
  `classify_mode`). It does not change any forbidden config file.
- **Operator mode was not added to the enum** even though the JARVIS
  Prime doc lists it, per the user's "skip Operator; fold into others"
  direction. If a future wave needs the explicit Operator route, it
  would re-introduce the enum value and split the Builder phrase /
  token tables.
- **No edits made** to `gateway/**`, `apps/android/**`,
  `hermes_cli/main.py`, `pyproject.toml`, `uv.lock`, `README.md`, or
  GitHub workflows.

## Changed files

- `hermes_cli/jarvis_prime/__init__.py` *(new, re-exports public surface)*
- `hermes_cli/jarvis_prime/modes.py` *(new, ~250 lines)*
- `tests/test_jarvis_prime_modes.py` *(new, 5 test suites, 65 assertions)*
- `docs/aci/reports/W01_MODE_CLASSIFIER_HARDENING.md` *(this report)*

## Tests run

```
$ python -m compileall hermes_cli/jarvis_prime/modes.py
Compiling 'hermes_cli/jarvis_prime/modes.py'...
(no errors)

$ pytest tests/test_jarvis_prime_modes.py -o addopts=""
============================== 65 passed in 1.09s ==============================
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
| Tests cover at least 30 example ACI commands | ✅ 33 parametrized real-world cases + 32 other assertions = 65 total |
| No false route to mobile_voice unless mobile/voice surface present | ✅ Guard tested with Slack / Termux / Android only / owner approval / open draft PR / ship it / route through AOS / fix build — none route to Mobile Voice |
| Builder commands route to Builder | ✅ audit repo, fix build, use Claude, use Codex, review PR, open draft PR, Android only, run tests, ship it, rebase main, route through AOS, HazMat Command, activate the council |
| Strategy commands route to Strategy | ✅ launch blockers, growth strategy, positioning, investor pitch, production ready, owner approval |
| Critic/red-team commands route to Critic | ✅ red team, tear apart, stress test, challenge this, weak assumption |
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
- The Operator-fold means specialist activations (HazMat / Nourish /
  Logistics) all land in Builder. Callers that need to differentiate
  "build for HazMat" vs "route to HazMat specialist" should read the
  `Classification.specialists` tuple rather than relying on the mode
  alone.

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
> (`hermes_cli/jarvis_prime/modes.py`) returning five modes (Companion,
> Strategy, Critic, Builder, Mobile Voice) plus a `specialists` tuple
> for HazMat / Nourish / Logistics activations. 65 test assertions
> across 5 suites covering all 16 brief-named commands, mobile-voice
> surface guards, specialist extraction, tie-break order, and API
> contract. No LLM calls, no new dependencies, no changes to forbidden
> surfaces. Draft PR only.
