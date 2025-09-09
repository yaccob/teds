# TeDS CLI Tutorial — Step‑by‑Step

This hands‑on tutorial guides you through TeDS (Test‑Driven Schema Development). You will:

- Install and run the CLI
- Verify schema behavior using testspecs
- Generate tests from schema references
- Tighten schemas based on failing cases and warnings
- Use in‑place updates and control output for CI

Prerequisites:
- Python 3.10+
- A terminal (any shell works)
- Optional: virtualenv

If you are following along inside this repository, the `demo/` directory contains sample schemas and testspecs used below.

## 1) Setup

- Create a virtual environment (per your OS/shell, see Python’s venv docs) and install dependencies:
  - `python3 -m venv .venv && . .venv/bin/activate` (POSIX example)
  - `pip install -r requirements.txt`
- Verify the CLI is available:
  - `teds --version`

Expected output example:
```
teds X.Y.Z (testspec major: N)
```

## 2) Start here: two ways to begin

Pick the path that matches your situation:

- No schema yet (greenfield): start test‑driven
  - Write a small testspec that captures intent (valid/invalid examples) for a schema you’re about to design.
  - Create a minimal schema stub (e.g., type/object with a field) or evolve an empty file.
  - Run verification; iterate on the schema until the expectations pass.

- Existing schema (brownfield): seed tests from the schema and extend
  - Use `teds generate` to scaffold tests from `examples` under the relevant JSON Pointer(s).
  - Extend with explicit edge cases (invalid values, boundaries, enums).
  - Run verification; refine schema where expectations fail or warnings suggest tightening.

Both flows converge: you maintain a testspec next to your schema, use `teds verify` in CI, and evolve schemas safely.

## 3) Verify schema behavior with a testspec

The verifier uses your testspec to check that the schema accepts what it should and rejects what it must. It resolves referenced schemas, runs validations, and prints normalized results. Try it with the demo spec:

- `teds verify demo/sample_tests.yaml`

Notes:
- Exit codes: 0 (success), 1 (any case has result ERROR), 2 (hard failure: I/O/YAML/spec invalid/schema resolution/version gate).
- Control verbosity with `--output-level all|warning|error`.

Filter to only errors:
- `teds verify demo/sample_tests.yaml --output-level error`

Write results back into the same file (in‑place writes only the `tests` section, preserving top‑level metadata like `version`):
- `teds verify demo/sample_tests.yaml -i`

## 4) Generate tests from schemas

TeDS can scaffold tests from the examples in your schemas. Point it at a JSON Pointer under a schema file. Each direct child becomes a test group.

Basics:
- `teds generate path/to/schema.yaml` → uses root pointer `#/` and writes `{base}.tests.yaml` next to the schema.
- `teds generate path/to/schema.yaml#/components/schemas` → writes `{base}.components+schemas.tests.yaml`.

Try it with the demo:
- `teds generate demo/sample_schemas.yaml` → writes `demo/sample_schemas.tests.yaml`

Target control (literal path or template):
- Directory target (default filename appended):
  - `teds generate demo/sample_schemas.yaml#/=specs/`
- Template with sanitized pointer:
  - `teds generate demo/sample_schemas.yaml#/components/schemas=specs/{base}.{pointer}.tests.yaml`

Tips:
- If your file has a single root of interest, prefer a short literal target (e.g., `{base}.test.yaml`) to avoid long filenames with `{pointer}`.

## 5) Extend tests with explicit cases

Open the generated testspec and add focused cases under each schema ref. Example snippet:

```yaml
tests:
  demo/sample_schemas.yaml#/components/schemas/Email:
    valid:
      "simple":
        payload: alice@example.com
    invalid:
      "missing at":
        payload: alice.example.com
```

Run verification:
- `teds verify demo/sample_schemas.tests.yaml`

Interpret results:
- SUCCESS: schema accepted valid cases and rejected invalid ones.
- WARNING: successful case with warnings attached (see below).
- ERROR: expectation failed (e.g., invalid instance was accepted or valid instance was rejected).

## 6) Understand and act on warnings

TeDS flags fragile situations, especially around JSON Schema `format`.

- Generated warning (code `format-divergence`): instance is valid per non‑strict validators, but strict validators that enforce `format` would reject it.
- Recommendation: make acceptance deterministic by adding an explicit `pattern` in the schema to encode the intended format.

Workflow:
1. See WARNING with `code: format-divergence` in output
2. Tighten schema (e.g., add `pattern` for `email`)
3. Re‑run `teds verify` — the warning should disappear if the pattern matches your intent

Notes:
- Warnings do not change the overall exit code to 2, but they elevate a case result to WARNING and are shown at `--output-level warning|all`.

## 7) Use in‑place and output control for CI

- In‑place normalization keeps specs tidy and reviewable:
  - `teds verify your.tests.yaml -i`
- CI‑friendly filtering:
  - `--output-level error` to show only blocking failures
- Exit codes enable gating:
  - 0 → pass, 1 → failing expectations, 2 → hard failure (treat as infrastructure error)

## 8) Network access (optional)

By default, only local `file://` refs are resolved.

- Enable HTTP/HTTPS `$ref`s if needed:
  - `teds verify spec.yaml --allow-network`
  - `teds generate schema.yaml#/path --allow-network`
- Limits and overrides:
  - Timeout and max bytes per resource (defaults: 5s, 5MiB). Override via CLI flags `--network-timeout`, `--network-max-bytes` or env `TEDS_NETWORK_TIMEOUT`, `TEDS_NETWORK_MAX_BYTES`.
- Recommendation for CI: keep network disabled for reproducibility; if enabling, pin versions/URLs.

## 9) Versioning and compatibility

- Tool uses Semantic Versioning; `teds --version` prints tool version and supported testspec major.
- Testspecs require `version: MAJOR.MINOR.PATCH` at top‑level. The tool enforces MAJOR equality and MINOR ≤ supported.
- On mismatch: exit 2 and no write with a clear message.

## 10) Troubleshooting

- Exit code 2 and error about schema/ref: check paths, JSON Pointers, and whether network is required (add `--allow-network` if using remote refs).
- Duplicate key error when parsing YAML: remove or fix duplicate mapping keys; the loader is strict by design.
- Generated files not where expected: review mapping `REF[=TARGET]`, relative targets resolve next to the schema file.

## 11) Next steps

- Add targeted boundary and enum cases (N−1/N/N+1, casing variants) to document and lock intent.
- Integrate into CI: run `teds verify **/*.tests.yaml --output-level error` and use exit code for gating.
- Keep specs close to schemas for reviewability; use in‑place updates (`-i`) to normalize.

## References and prior art

- Python jsonschema `format` validation and `FormatChecker`: https://python-jsonschema.readthedocs.io/en/stable/validate/#validating-formats
- RFC 3339 `date-time` profile: https://www.rfc-editor.org/rfc/rfc3339
- E.164 phone number guidance: https://stackoverflow.com/questions/6478875/regular-expression-matching-e-164-formatted-phone-numbers
- JSON Schema `additionalProperties`: https://json-schema.org/understanding-json-schema/reference/object.html#additional-properties
