# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeDS (Test-Driven Schema Development Tool) is a CLI for verifying JSON Schema contracts using YAML test specifications. The tool validates both positive cases (data that should be accepted) and negative cases (data that must be rejected).

## 🚨 CRITICAL: Coverage Must Be Maintained!

**MANDATORY BEFORE EVERY COMMIT:**
```bash
pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing --cov-fail-under=75 -q
```

**Never commit unless:**
1. ✅ All tests pass
2. ✅ Coverage ≥ 75% (maintain 94%+ if possible)
3. ✅ Coverage report reviewed

**Baseline Branch:** `working-baseline-94percent-coverage` (94.64% coverage, 59 tests)
**The tests exist for a reason - USE THEM!**

## Core Commands

### Development Setup
```bash
# Create virtualenv and install dependencies
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests (quick)
pytest -q

# Run unit tests with coverage (fail-under=73%)
pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing --cov-fail-under=73 -q

# Run CLI integration tests (no coverage requirement)
pytest tests/cli -v

# Using hatch
hatch run test
```

### CLI Usage
```bash
# Run via module (development)
python teds.py verify <testspec.yaml>
python teds.py generate <schema.yaml#/path>

# After install
teds verify <testspec.yaml>
teds generate <schema.yaml#/path>
```

### Building
```bash
# Install hatch and build
pip install hatch
hatch build
```

## Architecture

### Core Modules (`teds_core/`)
- **cli.py**: Command-line interface and argument parsing
- **validate.py**: Core validation logic for testspecs against schemas
- **generate.py**: Test generation from schema examples and structure
- **refs.py**: JSON Schema reference resolution and loading
- **report.py**: Template-based reporting (HTML/Markdown)
- **yamlio.py**: YAML loading/dumping with strict parsing
- **errors.py**: Custom exception hierarchy
- **version.py**: Version management and testspec compatibility
- **resources.py**: Resource loading utilities

### Key Concepts
- **Testspecs**: YAML files containing test cases with `valid` and `invalid` sections for schema references
- **Schema refs**: JSON pointers to specific schema definitions (e.g., `schema.yaml#/components/schemas/User`)
- **Versioning**: Testspec format has independent SemVer from the tool version
- **Templates**: Jinja2 templates for report generation (in `templates/` directory)

### Test Structure
- `tests/unit/`: Fast unit tests for individual modules (target: 73%+ coverage, achieved: 94%+)
- `tests/cli/`: End-to-end CLI integration tests (no coverage requirement - focus on workflow validation)
- Unit tests provide comprehensive coverage; CLI tests validate end-to-end functionality

### Coverage Exclusion Strategy

Infrastructure and fallback code that is difficult to test reliably is marked with coverage pragmas:

- `# pragma: no cover` - Single line exclusions
- `# pragma: no cover start/stop` - Block exclusions

**Excluded code categories:**
- CLI entry points (`if __name__ == "__main__"`)
- I/O error handling (file read/write failures)
- Network error handling (HTTP timeouts, connection failures)
- Schema validation internal errors
- Git command fallbacks in version detection
- Resource loading fallbacks
- YAML parsing error recovery

**Rationale:** These code paths handle system-level failures that are environment-dependent and difficult to reproduce consistently in unit tests. They represent defensive programming rather than core business logic.

### Entry Points
- Main CLI: `teds_core.cli:main`
- Development shim: `teds.py` (can run as `python teds.py`)

### Build Configuration
- Uses hatchling with hatch-vcs for version management from Git tags
- Packages include: `spec_schema.yaml`, `teds_compat.yaml`, `templates/`, `template_map.yaml`
- Dependencies: jsonschema, referencing, ruamel.yaml, semver, Jinja2

## Development Workflow (Makefile-based)

**Maven/Gradle-style workflow established via Makefile:**

```bash
# Fast development cycle
make test          # Unit tests only (fast, for development)
make test-unit     # Same as above
make dev-install   # Install in development mode (pip install -e .)

# Full validation cycle
make test-cli      # CLI integration tests (slower)
make test-schema   # Validate spec_schema.yaml against spec_schema.tests.yaml
make test-full     # All tests (required for packaging)

# Packaging & release
make package       # Build distribution packages (requires all tests)
make clean         # Remove build artifacts
make coverage      # Generate HTML coverage report
make dev-version   # Show current version info
make status        # Project status overview

# Automated Release Management
make release-patch # Create patch release (0.2.5 → 0.2.6) - most common
make release-minor # Create minor release (0.2.5 → 0.3.0) - new features
make release-major # Create major release (0.2.5 → 1.0.0) - breaking changes
make check-clean   # Verify working directory is clean for release
```

**Release Workflow & Version Management:**

The automated release workflow ensures safe, predictable releases:

1. **Prerequisites**: Clean working directory + all tests passing
2. **Version Calculation**: Automatically increments from current Git tag
3. **Tagging**: Creates annotated Git tag with conventional commit message
4. **Building**: Automatically builds distribution packages
5. **Next Steps**: Provides commands for publishing

**Release Types:**
- **Patch** (`make release-patch`): Bug fixes, documentation updates (0.2.5 → 0.2.6)
- **Minor** (`make release-minor`): New features, backward-compatible changes (0.2.5 → 0.3.0)
- **Major** (`make release-major`): Breaking changes, major API changes (0.2.5 → 1.0.0)

**Publishing Steps** (after successful release):
```bash
# Review the release
git show v0.2.6

# Publish to remote
git push origin v0.2.6

# Upload to PyPI (when ready)
twine upload dist/*
```

**Development Versions**: Between releases, hatch-vcs auto-generates development versions like `0.2.6.dev11+g09137808c` from Git state.

## Test Architecture & Separation of Concerns

**spec_schema.tests.yaml structure follows clear responsibility separation:**

- **`spec_schema.yaml#`**: Only top-level structure (required fields: version, tests; correct types)
- **`$defs/SchemaToTest`**: Only own properties (additionalProperties: false, valid/invalid field structure)
- **`$defs/CaseSet`**: Only container logic (object|null type validation, additionalProperties to CaseObject)
- **`$defs/CaseObject`**: All detailed validation rules (field types, constraints, warnings structure, conditional schemas)

**Key principle**: Each level tests only its own concerns, avoiding redundancy and maintaining clear boundaries.

**Key-as-payload parsing feature:** When `payload` field is missing from a test case, the test case key itself is parsed as YAML and used as the payload. Example: `"null": {description: "Null test"}` → key `"null"` is parsed as YAML `null` value and used as payload.

## TeDS Tool Purpose & Philosophy

**🎯 CRITICAL UNDERSTANDING:** TeDS validates whether **JSON Schemas meet the expectations** defined in test specifications. It does NOT validate whether test specifications are correct - the test specs define the business requirements/expectations, and TeDS verifies that schemas fulfill those expectations. This is the core value proposition.

## Test-Driven Development (TDD) Best Practices

**🚨 CRITICAL TDD RULE:** When doing test-driven development, **write tests that describe desired functionality and fail initially**. Do NOT write tests that expect errors (like `ImportError`, `NotImplementedError`) - these are not real tests.

**Correct TDD approach:**
1. Write tests that describe what the functionality should do
2. Run tests to verify they fail (due to missing implementation)
3. Implement the production code to make tests pass
4. Do NOT change the tests after implementation - only change production code

**Example of wrong approach (❌):**
```python
def test_new_feature():
    with pytest.raises(NotImplementedError):  # ❌ Wrong!
        some_function()
```

**Example of correct approach (✅):**
```python
def test_new_feature():
    result = some_function("input")        # ✅ Describes desired behavior
    assert result == "expected_output"     # ✅ Tests actual functionality
```

**Key principle:** Tests should verify that the implementation works correctly, not that it fails as expected. Tests define the contract/specification that the code must fulfill.

## 🚨 MANDATORY TDD WORKFLOW

**ALWAYS follow this exact sequence - NO EXCEPTIONS:**

1. **Test First (ALWAYS)**: Write the test that describes the desired functionality
2. **Test Must Fail**: Run the test to verify it fails (due to missing implementation)
3. **Implement Fix**: Write only the production code needed to make the test pass
4. **Test Must Pass**: Verify the test now passes
5. **NEVER Modify Test**: Once implementation is done, NEVER change the test

**This is non-negotiable TDD and must be followed permanently.**

**Example workflow:**
```bash
# 1. Write failing test
pytest tests/unit/test_new_feature.py::test_my_feature -v  # Must fail

# 2. Implement fix in production code
# Edit the actual implementation files

# 3. Verify test passes
pytest tests/unit/test_new_feature.py::test_my_feature -v  # Must pass

# 4. NEVER touch the test again
```

## Recent Development History

**Major features completed:**
1. ✅ Added comprehensive JSON Schema examples to spec_schema.yaml (following Draft 2020-12 standards)
2. ✅ Fixed CLI generator bug: now produces relative paths instead of absolute paths for better portability
3. ✅ Implemented comprehensive $defs test cases with proper separation of concerns
4. ✅ Established Maven/Gradle-style development workflow with Makefile
5. ✅ Maintained 94.6% test coverage throughout all changes

**Branch status:** Working on `working-baseline-94percent-coverage` with all recent improvements committed.

## Commit Standards

- ❌ NO Claude attribution markers (`🤖 Generated with [Claude Code]`, `Co-Authored-By: Claude`, `via [Happy]`)
- ❌ NO generated-with noise in commit messages - focus on technical content only
- ✅ Focus on technical changes and their business purpose
- ✅ Keep git history clean and informative
- ✅ Always run coverage verification before committing
