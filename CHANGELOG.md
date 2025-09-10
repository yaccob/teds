# Changelog

All notable user-facing changes for released versions.

## 0.2.5 — 2025-09-09

- fix(generate): resolve schema refs using absolute file paths when planning output mappings to avoid double-joining `base_dir` (e.g., running from a parent directory). Adds a regression test for relative schema paths in subdirectories.

## 0.2.4 — 2025-09-09

- docs: extract “Why this matters” details into a separate page and link from README.
- ci/ruleset: require package-smoke in default branch ruleset; add package-smoke gating.

## 0.1.23

- Validation: output always includes a complete testspec with a top-level `version` matching the supported testspec version.
- Demos: updated to include `version` so they are valid testspecs.

## 0.1.17

- Packaging: include `spec_schema.yaml` in the wheel so `teds verify` works from installed packages without the repository present.
- No changes to CLI usage or options.

## 0.1.5

- Documentation improvements. No functional changes.

## 0.1.4

- Initial public release.
- CLI: `teds verify` to validate testspecs; `teds generate` to scaffold tests from schema refs.
- Tests: output filtering (`--output-level`), in-place updates (`-i`), and exit codes aligned with validation results.
