# TeDS — Test‑Driven Schema Development Tool

TeDS (<u>**Te**</u>st‑<u>**D**</u>riven <u>**S**</u>chema Development Tool) is a CLI to specify and test your API contracts as YAML: verify that your JSON Schemas accept what they should and reject what they must, and generate tests from schema refs.

## Why this tool?

APIs live and die by their contracts. A schema is a promise: it defines the shape of data and which values are allowed. In practice, teams often check only the “happy path” (examples) — linters like Redocly can verify that. What’s usually missing is verifying the negative space: that the schema actually rejects what must be rejected. This tool focuses on both sides of the promise.

What it gives you:

- Contract verification as tests:
  - Positive cases: ensure the schema accepts data it should accept (including example‑based cases).
  - Negative cases: ensure the schema rejects data it must reject (explicit “invalid” cases, plus useful warnings for “format” divergences).
- Repeatable and readable specs:
  - Tests are YAML, live next to your schemas, versioned in Git, and easy to review.
  - Output is deterministic and CI‑friendly; in‑place updates keep files short and curated.
- Generation from real schemas:
  - Seed “valid” tests directly from `examples` in your schemas; extend with explicit edge cases as needed.

## Best Practice: Test‑Driven Schema Development (TeDS)

TeDS promotes writing small, focused tests for your schemas — before or alongside the schema changes — and keeping them in version control. Benefits:

- Early detection of breaking changes and ambiguity (especially with formats, boundaries, enums, additionalProperties, oneOf/anyOf).
- Living documentation: explicit valid/invalid cases clarify intent for reviewers and consumers.
- CI stability: deterministic validation and predictable outputs prevent regressions and flakiness.
- Safer evolution: refactors and migrations are guarded by negative tests that catch unintended acceptance.
- Shared understanding: developers, reviewers and integrators discuss examples, not abstractions.

TeDS fits how most API developers already think. In practice you start from intent: which payloads must be valid, and which must be rejected? With TeDS you write those expectations down first (valid and invalid examples), run the verifier, and then refine the schema until the expectations are met. This short feedback loop makes the schema a faithful reflection of the contract you have in mind — and the tests become living documentation that guards it over time.

### Why this matters (concrete scenarios):

 - Email/URI/Date formats: Validators differ in how strictly they enforce JSON Schema `format`. A value might pass in one environment and fail in another. For details, see [Formats (deep dive)](docs/why_this_matters.md#formats-email-uri-date-time).

 - Boundary conditions: Off‑by‑one mistakes on `minimum`/`maximum`, `minLength`/`maxLength`, or `minItems`/`maxItems` are easy to miss when only examples are checked. For details, see [Boundary Conditions (deep dive)](docs/why_this_matters.md#boundary-conditions-minmax-lengths-items).

 - Enum drift: Narrowing/widening an `enum` without tests can introduce breaking changes (or unintended acceptance); negative cases make this explicit. For details, see [Enum Drift (deep dive)](docs/why_this_matters.md#enum-drift-casing-widening-narrowing).

 - Additional properties: Forgetting `additionalProperties: false` can let unknown fields leak through; conversely, making it too strict can break clients — both caught by targeted cases. For details, see [Additional Properties (deep dive)](docs/why_this_matters.md#additional-properties-unknown-fields).

 - Pointer/Compositions: Deeply nested structures or `oneOf`/`anyOf` compositions often allow unintended instances; explicit invalid cases document and prevent regressions. For details, see [Pointers & Compositions (deep dive)](docs/why_this_matters.md#pointers--compositions-oneofanyof).

Bottom line: You specify the contract, you also test the contract — both what is allowed and what is forbidden. That improves quality and serves as living documentation.

## Install

- From source (dev):
  - Create a virtualenv and activate it according to your OS/shell (see Python’s venv docs). Then:
    - `pip install -r requirements.txt`
    - Optional build: `pip install hatch && hatch build`

Installation from PyPI can be added later once releases are tagged.

## Quickstart

Note: Commands are shell‑agnostic. Only virtualenv activation differs across platforms (see Python venv docs).

### Testspec Format

Top‑level YAML document:

```yaml
version: "1.0.0"   # required SemVer; must match tool’s supported MAJOR and not exceed supported MINOR
tests:
  <ref>:            # e.g. schema.yaml#/Foo
    valid:   { <cases> }
    invalid: { <cases> }
```

Case objects may contain:
- `description`: string
- `payload`: any
- `parse_payload`: boolean (if true, `payload` is parsed as YAML/JSON)
- `result`: SUCCESS|WARNING|ERROR
- `message`: string (error message)
- `validation_message`: string (validator message)
- `payload_parsed`: any (emitted when parse_payload is true)
- `from_examples`: boolean (derived by generator)
- `warnings`: [string | {generated, code}]

The schema is in `spec_schema.yaml`. TeDS validates your testspec against this schema.

#### Strict YAML parsing:
- duplicate keys are rejected to avoid ambiguity.

### Verify a testspec:
- `teds verify demo/sample_tests.yaml`

### Generate testspec(s) from schema refs:
- `teds generate demo/sample_schemas.yaml#/components/schemas`
  → writes `demo/sample_schemas.components+schemas.tests.yaml`

### Public API–inspired demos:
Verify negative and positive contract cases:
- `teds verify demo/public_specs.yaml`
- Schemas: `demo/public_schemas.yaml` (email contact, ISO date-time, phone E.164, currency+amount, strict user object)
- Specs:   `demo/public_specs.yaml` (explicit invalid/valid cases highlighting typical pitfalls)

### Exit codes:
- 0: success
- 1: verification produced cases with `result: ERROR`
- 2: hard failures (I/O, YAML parse, invalid testspec schema, schema/ref resolution, version mismatch, unexpected)

## Tutorial

Looking for a step‑by‑step introduction? Read the full tutorial:

- Tutorial: [docs/tutorial.md](docs/tutorial.md)

## Versioning & Compatibility

- Testspec versioning is independent of the app’s SemVer. The app declares a supported testspec range via a bundled manifest (`teds_compat.yaml`).
- `teds --version` prints: `teds <app> (spec supported: 1.0–1.N; recommended: 1.N)`
- Gate rules when verifying or writing specs:
  - Major must match the supported major.
  - Minor must be less than or equal to the supported max minor; otherwise exit code 2.
  - The testspec is strictly validated against `spec_schema.yaml`; unknown fields/structures fail fast.
- Generation stamps the recommended testspec version (from the manifest) at `version:` to reduce churn while remaining forward‑compatible.

## Development

- Create env: `python3 -m venv .venv && . .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run tests: `pytest -q` or `hatch run test`
- Build (wheel/sdist): `pip install hatch && hatch build` (uses hatchling + hatch-vcs, version from Git tag)

## Contributing

- Conventional Commits (feat, fix, docs, etc.).
- Keep changes focused; update or add tests under `tests/`.

## Security Notes

- External refs (HTTP/HTTPS): disabled by default for reproducibility and safety.
  - Opt-in with `--allow-network` to resolve remote `$ref`s.
  - Limits: global timeout and size cap (defaults: 5s, 5MiB per resource).
  - Overrides: CLI `--network-timeout`, `--network-max-bytes` or env `TEDS_NETWORK_TIMEOUT`, `TEDS_NETWORK_MAX_BYTES`.
  - Recommended for CI: keep default (local-only). If enabling network, ensure stability (pin URLs/versions) and mind SSRF/DoS considerations.
