# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeDS (Test-Driven Schema Development Tool) is a CLI for verifying JSON Schema contracts using YAML test specifications. The tool validates both positive cases (data that should be accepted) and negative cases (data that must be rejected).

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

# Run CLI tests with coverage (fail-under=60%)
pytest tests/cli --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing --cov-fail-under=60 -q

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
- `tests/cli/`: End-to-end CLI integration tests (target: 60%+ coverage)
- Dual coverage approach: separate thresholds for unit vs CLI testing

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