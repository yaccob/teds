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

 - Email/URI/Date formats: Validators differ in how strictly they enforce JSON Schema `format`. A value might pass in one environment and fail in another. The tool flags such cases and suggests adding a `pattern` for determinism.
    - Real world:
      - OpenAPITools/openapi-generator: date-time leads to wrong client typing/handling in popular generators: https://github.com/OpenAPITools/openapi-generator/issues/9380
      - thephpleague/openapi-psr7-validator: date-time validation allowed non‑RFC3339 strings: https://github.com/thephpleague/openapi-psr7-validator/issues/247
    - How TeDS could help to avoid this kind of problem:
      - Add negative `date-time` cases (e.g., missing offset) and verify — WARNING/ERROR reveals divergence; enforce determinism via a `pattern`.

 - Boundary conditions: Off‑by‑one mistakes on `minimum`/`maximum`, `minLength`/`maxLength`, or `minItems`/`maxItems` are easy to miss when only examples are checked.
    - Real world:
      - Schemathesis/OpenAPI: empty array with `minItems: 0` treated as invalid (edge interpretation): https://github.com/schemathesis/schemathesis/issues/3056
      - Kubernetes API linter discussions around `MinItems` and array field pointers: https://github.com/kubernetes-sigs/kube-api-linter/issues/116
    - How TeDS could help to avoid this kind of problem:
      - Add cases at N−1, N, N+1 (e.g., empty vs. non‑empty arrays) so regressions surface and intent is explicit.
 - Enum drift: Narrowing/widening an `enum` without tests can introduce breaking changes (or unintended acceptance); negative cases make this explicit.
    - Real world:
      - open-api (express middleware) discussion: case-insensitive enums expected by clients: https://github.com/kogosoftwarellc/open-api/issues/755
      - swift-openapi-generator: request for case-insensitive enums: https://github.com/apple/swift-openapi-generator/issues/721
    - How TeDS could help to avoid this kind of problem:
      - Add a lowercase/variant invalid case. If it passes, you’ve exposed an acceptance gap; if it fails, you’ve documented strict casing for clients.
 - Additional properties: Forgetting `additionalProperties: false` can let unknown fields leak through; conversely, making it too strict can break clients — both caught by targeted cases.
    - Real world:
      - JSON schema: allOf with additionalProperties: https://stackoverflow.com/questions/22689900/json-schema-allof-with-additionalproperties
      - Understanding additionalProperties: https://stackoverflow.com/questions/16459954/understanding-the-additionalproperties-keyword-in-json-schema-draft-version-4
    - How TeDS could help to avoid this kind of problem:
      - Add an invalid case with an unknown field. If it’s accepted, the schema is too lax; if rejected, the test documents strictness and prevents accidental relaxations.
 - Pointer/Compositions: Deeply nested structures or `oneOf`/`anyOf` compositions often allow unintended instances; explicit invalid cases document and prevent regressions.
    - Real world:
      - Numerous issues and Q&As around `oneOf`/`anyOf` usage and expectations, e.g.: https://stackoverflow.com/questions/25014650/json-schema-example-for-oneof-objects
    - How TeDS could help to avoid this kind of problem:
      - Craft a no‑match and ambiguous‑match invalid case to lock in intent; you’ll catch ambiguity and refine `oneOf`/`anyOf`.

Bottom line: You specify the contract, you also test the contract — both what is allowed and what is forbidden. That improves quality and serves as living documentation.

## Install

- From source (dev):
  - `python3 -m venv .venv && . .venv/bin/activate`
  - `pip install -r requirements.txt`
  - Optional build: `pip install hatch && hatch build`

Installation from PyPI can be added later once releases are tagged.

## Quickstart

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

## CLI Tutorial

### Overview

The TeDS CLI centers around two commands: `verify` and `generate`. Paths are relative to the current working directory. By default, only local schemas are resolved; enable network access explicitly (see Network Access).

### Verify

`teds verify [--output-level all|warning|error] [-i|--in-place] [--allow-network] <SPEC>...`
  - Verifies testspec file(s) and prints normalized results to stdout unless `-i` is used (then writes back to the file).
  - Examples:
    - Verify a single file (default output level = warning):
      - `teds verify demo/sample_tests.yaml`
    - Verify multiple files and show only errors:
      - `teds verify a.yaml b.yaml --output-level error`
    - Write results back in place (in-place preserves all top-level metadata like `version` and only updates `tests`):
      - `teds verify demo/sample_tests.yaml -i`

#### Version gate:
- testspec `version` must match the supported MAJOR and not exceed the supported MINOR; otherwise RC=2 and no write.

#### Output levels:
- `all`: show everything
- `warning`: show WARNING/ERROR
- `error`: show only ERROR

#### Network:
- add `--allow-network` to enable HTTP/HTTPS `$ref` resolution (see Network notes below).

#### Warnings (user-defined and generated)

TeDS distinguishes between user-defined warnings and tool-generated warnings. In both cases a successful case (`result: SUCCESS`) is elevated to `result: WARNING` if any warnings are present — this helps you surface “it works, but be careful” situations in CI and reviews.

- User-defined warnings
  - Purpose: Let authors call out policy or integration caveats that should be visible in output without failing the case.
  - How: add a `warnings` array to a case with free‑form strings.
  - Example:
    ```yaml
    tests:
      schema.yaml#/Email:
        valid:
          "policy note":
            payload: alice@example.com
            warnings:
              - "Accepts plus-addressing, downstream system strips tags"
    ```
  - Effect: the case is marked with `result: WARNING` in the output; it shows up with `--output-level warning|all`.

- Generated warnings
  - Purpose: TeDS can attach structured warnings when it detects situations that are valid but fragile. Currently implemented for JSON Schema `format`:
    - Code: `format-divergence` — strict validators (that enforce `format`) reject an instance, while non‑strict validators accept it.
    - Output structure under the case:
      ```yaml
      warnings:
        - generated: |
            Relies on JSON Schema 'format' assertion (format: email).
            Validators that *enforce* 'format' will reject this instance.
            Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.
          code: format-divergence
      ```
  - How to act on generated warnings
    - Prefer explicitness: tighten the schema with a `pattern` that encodes your acceptance criteria (e.g., for `email`).
    - Re‑run TeDS — if the schema covers your intent, the warning disappears.
    - If the divergence is acceptable by design (e.g., non‑strict runtime), keep the warning as living documentation; it will remain visible at `--output-level warning|all`.

##### Notes
- Warnings do not cause `result: ERROR` and therefore do not turn the overall exit code to 2. They do, however, change a case’s `result` from SUCCESS → WARNING; with `--output-level error` they are filtered out.
- “Generated” warning entries are added by TeDS; reserve that shape (`{generated, code}`) for tool output. For user-authored warnings prefer plain strings.

#### In-Place Behavior

With `-i/--in-place`, TeDS writes only the `tests` section back to the file; all top-level metadata (e.g., `version`) remain as is. On version mismatch (unsupported MAJOR/MINOR), TeDS does not write and returns RC=2 with a clear message.

### Generate

`teds generate [--allow-network] REF[=TARGET] ...`
  - Generates testspec(s) for direct child schemas under a JSON Pointer.
  - Mapping syntax: each argument is `REF[=TARGET]`.
    - `REF`: `path/to/schema.yaml#/<json-pointer>`
      - Pointer defaults to `#/` (root) if omitted, so `schema.yaml` is equivalent to `schema.yaml#/`.
    - `TARGET`: optional literal path or template. If it’s a directory, the default filename is appended.
      - Relative targets resolve next to the schema file.
  - Default filename rules:
    - Pointer `#/` (root) → `{base}.tests.yaml`
    - Any other pointer → `{base}.{pointer}.tests.yaml` (pointer without leading `/`, sanitized)
    - "sanitized" uses `+` as segment separator and escapes `+` inside segments by doubling it (`++`). Example: `Email` → `components+schemas+Email`.
  - Template tokens (usable in TARGET): `{file}`, `{base}`, `{ext}`, `{dir}`, `{pointer}`, `{pointer_raw}`, `{pointer_strict}`, `{index}`
  - Examples (assume schema at `demo/sample_schemas.yaml`):
    - Omit TARGET (default filename next to schema):
      - `teds generate demo/sample_schemas.yaml#/components/schemas`
      - → writes `demo/sample_schemas.components+schemas.tests.yaml`
    - Omit pointer and target (root pointer + default filename):
      - `teds generate demo/sample_schemas.yaml`
      - → writes `demo/sample_schemas.tests.yaml`
    - Directory target (default filename appended):
      - `teds generate demo/sample_schemas.yaml#/=specs/`
      - → writes `demo/specs/sample_schemas.tests.yaml`
    - Template with sanitized pointer:
      - `teds generate demo/sample_schemas.yaml#/components/schemas=specs/{base}.{pointer}.tests.yaml`
      - → writes `demo/specs/sample_schemas.components+schemas.tests.yaml`
    - Template with raw pointer (nested directories):
      - `teds generate demo/sample_schemas.yaml#/=specs/{base}/{pointer_raw}.tests.yaml`
      - → writes `demo/specs/sample_schemas/components/schemas.tests.yaml`
  - Recommendation:
    - If you typically have exactly one schema root per file, and you target deeper roots (with `/` in the pointer), prefer a succinct literal mapping to keep filenames short, e.g.:
      - `teds generate demo/sample_schemas.yaml#/components/schemas={base}.test.yaml`
      - → writes `demo/sample_schemas.test.yaml`
    - This avoids long `{pointer}` tokens in filenames while still being deterministic.
  - Network: add `--allow-network` to enable HTTP/HTTPS `$ref` resolution (see Network notes below).

### Network Access

By default, TeDS resolves only local `file://` schemas. Enable remote `$ref`s with `--allow-network`.
  - Limits: global timeout and size cap (defaults: 5s, 5MiB per resource).
  - Overrides: CLI `--network-timeout`, `--network-max-bytes` or env `TEDS_NETWORK_TIMEOUT`, `TEDS_NETWORK_MAX_BYTES`.
  - Recommended for CI: keep default (local-only). If enabling network, ensure stability (pin URLs/versions) and mind SSRF/DoS considerations.

### Versioning & Compatibility

Tool uses Semantic Versioning and derives its version from Git tags (`vX.Y.Z`).
- `teds --version` prints tool version and the supported testspec major.

Testspecs require `version` (SemVer). The tool enforces:
  - MAJOR must match the tool’s supported major.
  - MINOR must be less than or equal to the tool’s supported minor.
  - PATCH is ignored for compatibility checks.
- On mismatch: RC=2, nothing is written. The error explains what to upgrade.

### References and prior art
- Python jsonschema `format` validation and `FormatChecker` (official docs): https://python-jsonschema.readthedocs.io/en/stable/validate/#validating-formats
- RFC 3339 `date-time` profile (official spec): https://www.rfc-editor.org/rfc/rfc3339
- E.164 phone number guidance (Stack Overflow): https://stackoverflow.com/questions/6478875/regular-expression-matching-e-164-formatted-phone-numbers
- JSON Schema additionalProperties (official guide): https://json-schema.org/understanding-json-schema/reference/object.html#additional-properties

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
