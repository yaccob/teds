# Development Notes — Current Workstream

This file tracks implementation decisions and near‑term TODOs for TeDS, so future sessions can pick up where we left off.

## Reporting (MVP)

- Purpose: Render human‑readable reports from verify results using built‑in templates.
- CLI:
  - List templates (top‑level option):
    - `teds --list-templates`
    - Prints built‑in template IDs and descriptions; exits immediately.
  - Render reports via verify:
    - `teds verify --report TEMPLATE_ID[=OUTFILE] <SPEC>... [--output-level L]`
    - Reports always write files (never stdout), independent of `-i`.
    - Exit code matches verify semantics: 0 (success), 1 (cases with ERROR), 2 (hard failures).
- Default output filenames (when `=OUTFILE` is omitted):
  - Single spec: `{spec_stem}.report.{ext}`
  - Multiple specs: `{spec_stem}.{template_base}.report.{ext}`
  - `{ext}` inferred from template ID (`.html` → `html`, otherwise `md`). `{template_base}` is the part before the first dot (e.g., `summary`).
- Templates:
  - Mapping is defined in `template_map.yaml` (packaged):
    - Each entry has: `id` (CLI ID), `path` (relative file path for the engine), `description`.
  - Built‑ins live under `templates/` (packaged via hatch `force-include`).
  - Current IDs: `summary.md`, `summary.html`.
- Data passed to templates:
  - The normalized verify structure per spec (same as printed by verify): `{ version, tests: { ref: { valid, invalid } } }`.
  - Tool meta: `{ version, spec_supported, spec_recommended }` for headers.
  - One report per spec is rendered using the same template.
- Security/IO:
  - No network, local files only.
  - HTML auto‑escape enabled for `.html/.htm` templates.

## Status

- Branch: `feat/report-cli`
- Tests: 25 passed locally.
- Packaging:
  - `templates/` and `template_map.yaml` included in wheels (installed under the package; loader uses `read_text_resource`).

## Agreed Conventions

- Reports are not printed to stdout; verify’s YAML remains on stdout unless reporting is used.
- Top‑level `--list-templates` behaves like `--help/--version` (no other actions performed).
- No user‑template paths yet; only built‑in template IDs. (User templates to be discussed later.)

## Next Steps (TODO)

- User templates: support a user‑provided `.j2` path (design TBD; likely a separate flag or ID prefix).
- JSON export (data‑only) for external renderers.
- Template ergonomics: small Jinja filters/helpers for common counts, while keeping raw data available.
- README: add a short “Reports” section (usage, defaults, template listing).
- More built‑in templates (e.g., per‑ref detail, warnings/errors focus).

## Test Coverage Strategy

- Two separate coverage gates in CI (no combined report):
  - Unit (tests/unit): `--cov` over in‑process modules, target ≥ 75% (initial), to be raised incrementally.
  - CLI (tests/cli): end‑to‑end subprocess tests, target ≥ 60% (initial).
- Threshold plan:
  - Raise Unit to 85% once additional unit tests cover validate/version/refs/generate error paths and branches.
  - Keep CLI threshold realistic; improve gradually as more scenarios are exercised.
- Notes:
  - CLI coverage is harder to push very high due to subprocess nature; it complements (not replaces) Unit coverage.
  - We do not require a combined coverage number.

## Branch/PR Workflow (reminder)

- No direct pushes to `master`.
- Short‑lived feature branches; PR + green CI before merge; Squash‑merge.
