# Changelog

All notable user-facing changes for released versions.

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

