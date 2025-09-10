# Repository Guidelines

## Project Structure & Module Organization
- `teds.py`: CLI shim; re-exports API and CLI.
- `teds_core/`: TeDS package (CLI + helpers)
  - `yamlio.py` (YAML loader/dumper)
  - `refs.py` (schema refs, example collection)
  - `validate.py` (validation pipeline, file ops)
  - `generate.py` (scaffold tests from schema examples)
  - `cli.py` (argparse + main())
- `spec_schema.yaml`: Schema for the testspec format used by the tool.
- `demo/`: Demo assets — `sample_schemas.yaml` (schemas) and `sample_tests.yaml` (testspecs).
- `.venv/`: Optional local virtualenv (not checked in).

## Build, Demo, and Development Commands
- Create env: `python3 -m venv .venv && . .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Build package: `pip install hatch && hatch build` (uses hatchling + hatch-vcs; version from Git tag)
- Verify a testspec: `teds verify demo/sample_tests.yaml`
  - Use `--output-level all|warning|error` to filter results; add `-i` to rewrite the testspec in place.
- Generate specs (map syntax):
  - Omit target (default name next to the schema file): `teds generate demo/sample_schemas.yaml#/components/schemas`
  - Omit pointer and target (defaults to `#/` and `sample_schemas.tests.yaml` in the schema directory): `teds generate demo/sample_schemas.yaml`
  - Literal: `teds generate demo/sample_schemas.yaml#/components/schemas=demo/generated_tests.yaml`
  - Directory default name: `teds generate demo/sample_schemas.yaml#/=specs/`
  - Template: `teds generate demo/sample_schemas.yaml#/components/schemas=specs/{base}.{pointer}.tests.yaml`
  - Default filename: root pointer `#/` → `{base}.tests.yaml`; otherwise `{base}.{pointer}.tests.yaml` (pointer without leading `/`, sanitized).
  - Resolution: omitted or relative TARGETs are resolved against the schema file's directory.
- Exit code reflects errors (useful for CI). Requires Python 3.10+.

## Versioning
- Semantic Versioning via Git tags `vX.Y.Z` (tool version derives from tag).
- CLI prints: `teds --version` → `teds X.Y.Z (testspec major: N)`.
- Testspecs require top-level `version: "MAJOR.MINOR.PATCH"`; tool enforces matching MAJOR.

## Coding Style & Naming Conventions
- Python, 4‑space indents, PEP 8, type‑annotated functions. Use `snake_case` for symbols.
- Keep functions small and pure; print diagnostics to `stderr` (as in `schema_path:` output).
- Prefer explicit schemas and examples; avoid dynamic imports or network access.

## Testing Guidelines
- Real tests live in `tests/` and use `pytest` to self-test the CLI and helpers.
- Tests are self-contained and create temporary YAML fixtures; they do not depend on `demo/`.
- Run: `pytest -q` (optionally `-k <pattern>` to filter).
- Golden tests: see `tests/cases/*` — case directories are behavior-focused (e.g., `format_divergence`, `output_filtering_and_inplace`). Each case has `schema.yaml`, `spec.yaml`, and `expected*.yaml`; tests compare parsed YAML structures and verify exit codes.
- Demos remain under `demo/` for illustrative data and manual runs.
- Test style: small, focused tests; tmp paths for I/O; import helpers directly (`validate_doc`, `validate_file`, `generate_from`).
- Tests-first principle:
  - For bug fixes and new features, write a failing test first that exposes the behavior, confirm it fails, then implement the fix/feature until the test passes.
  - Do not rewrite history to reorder fix/test after the fact; keep the timeline truthful for easier analysis.

## Developer Hygiene (Agents)
- Do not create temporary files or directories in the project root during manual reproduction or debugging.
- Use `pytest`'s `tmp_path` fixture or `tempfile.TemporaryDirectory()` for ad‑hoc experiments.
- If you need a scratch workspace, keep it under a temporary directory outside the repo, not as `sandbox_*` in the root.

### Session continuity
- Persist active plans, decisions, and in‑progress feature notes in `DEV_NOTES.md` (not in AGENTS.md).
- Treat `DEV_NOTES.md` as the living log for ongoing work so ending a session does not lose context.
- Keep AGENTS.md for stable, repo‑wide conventions and long‑lived guidance only.

## Commit & Pull Request Guidelines
- Git history is minimal; adopt Conventional Commits (`feat:`, `fix:`, `docs:`, etc.).
- PRs should include: clear description, linked issues, sample commands you ran, and before/after behavior when applicable.
- Keep changes focused; update or add tests in `tests/` and demos in `demo/` to demonstrate behavior.

## Branching & PR Workflow (Agents)
- Default branch is `master`. Do not push directly to `master`.
- Create short‑lived branches per change:
  - `feat/<scope>-<summary>`, `fix/<scope>`, `docs/<scope>`, `chore/<scope>`.
- Open a PR and wait for CI to pass before merging.
- Prefer Squash‑Merge to keep history minimal and aligned with Conventional Commits.
- Ensure:
  - Tests pass locally (`pytest -q`) before opening/merging PRs.
  - Docs updated when behavior/CLI changes.
  - SemVer impact considered (breaking → major, feature → minor, fix → patch).

## Security & Configuration Tips
- The tool resolves only `file://` URIs; keep schemas local. Do not embed secrets in YAML.
- YAML loader rejects duplicate keys; prefer explicit patterns (e.g., add `pattern` for strict formats).
