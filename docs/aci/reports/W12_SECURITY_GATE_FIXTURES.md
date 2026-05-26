# Wave 12 — JARVIS Prime Security Gate Fixtures

## Wave

Wave 12 — Security Gate fixtures and validation tests for JARVIS Prime.

## Branch

`aci/wave-12-security-gate-fixtures`

## Scope

Land safe, fake test fixtures that mirror the eight risky-change categories the JARVIS Prime Security Gate is supposed to catch, plus a pytest module that validates them. The Security Gate is defined in `docs/jarvis-verification-gates.md`. No production code is modified.

Allowed paths (only these files were added):

- `tests/fixtures/jarvis_security_packets/*.json`
- `tests/test_jarvis_prime_security_packets.py`
- `docs/aci/reports/W12_SECURITY_GATE_FIXTURES.md`

Forbidden paths (unchanged, verified clean): `hermes_cli/**`, `gateway/**`, `apps/android/**`, `pyproject.toml`, `uv.lock`, GitHub workflows, JARVIS skills, JARVIS docs, `tests/conftest.py`.

## Fixture catalogue

| File | Category | Expected decision | Owner approval required |
| --- | --- | --- | --- |
| `secret_added.json` | `secret_added` | `fail` | false |
| `env_edit.json` | `env_edit` | `owner_approval` | true |
| `dependency_changed.json` | `dependency_changed` | `owner_approval` | true |
| `network_call_added.json` | `network_call_added` | `fail` | false |
| `owner_gated_deploy.json` | `owner_gated_deploy` | `owner_approval` | true |
| `app_store_submission.json` | `app_store_submission` | `owner_approval` | true |
| `public_posting.json` | `public_posting` | `owner_approval` | true |
| `dns_change.json` | `dns_change` | `owner_approval` | true |

Each category maps directly to a line in the Security Gate or Owner Approval Gate sections of `docs/jarvis-verification-gates.md`.

## Schema reference

Each fixture is a JSON object with the following shape:

```json
{
  "packet_id": "w12-<category-with-dashes>",
  "category": "<one of the eight required categories>",
  "gate": "Security Gate",
  "expected_decision": "pass | fail | owner_approval",
  "owner_approval_required": true,
  "summary": "Short human-readable description of the proposed change.",
  "fake": true,
  "change": {
    "kind": "file_edit | shell_command | external_message | dns_record",
    "path": "examples/<fake-path>",
    "diff_excerpt": "+ ...fake diff or command..."
  },
  "rationale": "Citation to the docs/jarvis-verification-gates.md rule being exercised.",
  "safety_markers": ["EXAMPLE", "FAKE", "..."]
}
```

Every fixture sets `fake: true`, targets the `Security Gate`, declares its `expected_decision`, and lists `safety_markers` (e.g. `EXAMPLE`, `FAKE`, `DO-NOT-USE`, `0000`) embedded in any field that could otherwise look like real data.

## Safety guarantees

The validation test in `tests/test_jarvis_prime_security_packets.py` enforces three layers of safety on every fixture:

1. **No real-looking secrets.** The serialized fixture text is scanned with regexes for AWS access keys (`AKIA…`, `ASIA…`), GitHub PATs (`ghp_…`, `gho_…`, `github_pat_…`), Slack tokens (`xox[baprs]-…`), OpenAI-style keys (`sk-…`), Google API keys (`AIza…`), and PEM private-key headers. Any hit fails the test.
2. **No opaque hex/base64 strings without a safety marker.** Any contiguous hex string of 32+ characters must contain `EXAMPLE`, `FAKE`, `DO-NOT-USE`, or `0000`. This catches accidentally-pasted hashes or tokens that don't match a known vendor format.
3. **No real third-party hosts.** Any URL inside a fixture must resolve to a reserved or test-safe host: `example.com`, `example.org`, `example.net`, `example.invalid`, `localhost`, `127.0.0.1`, `::1`, RFC 1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), or RFC 5737 TEST-NET ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`).

In addition, the test asserts the union of `category` values across all fixtures equals the eight required categories — no missing, no extras — and that each `packet_id` matches its filename.

## Tests added

- `tests/test_jarvis_prime_security_packets.py`
  - `test_fixtures_directory_exists`
  - `test_category_coverage_matches_task_list`
  - `test_fixture_shape_and_safety` (parametrized over the eight fixtures)
  - `test_fixture_packet_id_matches_filename` (parametrized over the eight fixtures)

The test module imports only `json`, `pathlib`, `re`, and `pytest`. It does not import any JARVIS, Hermes, or gateway runtime — consistent with the wave constraint that "tests use existing gate APIs only" (there is no Python gate API in the current repo; the gates exist as documentation and process discipline).

## Verification

Commands run:

- `pytest tests/test_jarvis_prime_security_packets.py -v`
- `python -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('tests/fixtures/jarvis_security_packets').glob('*.json')]"`

Results are captured in the PR description.

## Remaining risks

- **No runtime enforcement.** These fixtures describe what the Security Gate should reject or escalate; they do not by themselves prevent a real risky change from landing. A future wave can build a gate evaluator that consumes packet-shaped inputs and uses these fixtures as its golden set.
- **Schema is repo-local.** The schema is documented here and pinned by the test; it is not a published contract. If JARVIS Prime grows a real packet protocol, the schema should be re-pointed there and the fixtures updated in lockstep.

## Rollback

Delete the three allowed paths:

```
rm -rf tests/fixtures/jarvis_security_packets
rm tests/test_jarvis_prime_security_packets.py
rm -rf docs/aci/reports/W12_SECURITY_GATE_FIXTURES.md
```

No other files were modified, so rollback has no cross-cutting effects.

## Out of scope / cross-wave notes

- No JARVIS Prime, AOS Council, or Hermes runtime changes.
- No additions to `pyproject.toml`, `uv.lock`, or any dependency manifest.
- No real secrets, real `.env` content, real network calls, real deploys, real app store submissions, real public posts, or real DNS changes occurred or were planned. Every fixture describes a hypothetical proposed change for the gate to evaluate.
- No PR will be merged from this wave without owner approval.
