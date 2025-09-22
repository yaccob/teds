# TeDS — Test‑Driven Schema Development Tool

TeDS (<u>**Te**</u>st‑<u>**D**</u>riven <u>**S**</u>chema Development Tool) is a CLI to specify and test your JSON Schema contracts using YAML test specifications. Verify that your schemas accept what they should and reject what they must.

## Why TeDS?

APIs live and die by their contracts. Most teams only test the "happy path" — but what about ensuring your schema actually rejects invalid data? TeDS fills this gap by testing both sides of your schema contract:

- **Positive cases**: Schema accepts valid data (including examples)
- **Negative cases**: Schema rejects invalid data (explicit invalid cases)
- **Contract clarity**: Tests serve as living documentation
- **CI integration**: Deterministic validation prevents regressions

## Quick Start

### Installation

```bash
# From PyPI (recommended)
pip install teds

# From source (development)
git clone https://github.com/yaccob/teds.git
cd teds
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

### Basic Usage

```bash
# Verify a test specification
teds verify demo/sample_tests.yaml

# Generate tests from schema examples
teds generate demo/sample_schemas.yaml#/components/schemas

# Generate reports
teds verify demo/sample_tests.yaml --report default.html
```

## Core Concepts

### Test Specifications

TeDS uses YAML files to define what should be valid or invalid for your schemas:

```yaml
version: "1.0.0"
tests:
  schema.yaml#/User:
    valid:
      simple_user:
        description: Basic valid user
        payload:
          id: "12345"
          name: "Alice"
          email: "alice@example.com"
    invalid:
      missing_email:
        description: User without required email
        payload:
          id: "12345"
          name: "Alice"
```

### Schema References

Point to specific schemas using JSON Pointer syntax:
- `schema.yaml#/User` - Root level User schema
- `api.yaml#/components/schemas/User` - OpenAPI style reference
- `definitions.yaml#/$defs/Address` - JSON Schema 2020-12 style

## Commands

### Verify Test Specifications

```bash
# Basic verification
teds verify my_tests.yaml

# Filter output levels
teds verify my_tests.yaml --output-level error    # Only errors
teds verify my_tests.yaml --output-level warning  # Warnings and errors
teds verify my_tests.yaml --output-level all      # Everything

# Update test files in place
teds verify my_tests.yaml --in-place

# Generate reports
teds verify my_tests.yaml --report default.html
teds verify my_tests.yaml --report default.md
teds verify my_tests.yaml --report default.adoc
```

### Generate Test Specifications

```bash
# Generate from schema root
teds generate schema.yaml

# Generate from specific path
teds generate api.yaml#/components/schemas

# Multiple targets
teds generate schema1.yaml schema2.yaml#/definitions
```

## Reports

TeDS generates professional validation reports in multiple formats:

- **default.adoc** - AsciiDoc with color-coded status and complete YAML payloads
- **default.html** - HTML with responsive design and syntax highlighting
- **default.md** - Markdown with emoji status indicators
- **summary.md** - Compact summary with counts and references
- **summary.html** - Simple HTML summary

Reports show complete test results with clean YAML formatting and clear message separation.

## Exit Codes

- **0** - Success (all tests passed)
- **1** - Validation failures (some tests had ERROR results)
- **2** - Hard failures (I/O errors, invalid testspec, schema resolution issues)

## Tutorial

For a comprehensive step-by-step guide, see the [complete tutorial](https://yaccob.github.io/teds/tutorial.html).

## Development

```bash
# Clone repository
git clone https://github.com/yaccob/teds.git
cd teds

# Setup
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest -q

# Build
pip install hatch && hatch build
```

## Security & Network Access

By default, TeDS only resolves local file references for security and reproducibility. Enable network access for remote `$ref` resolution:

```bash
teds verify spec.yaml --allow-network
teds generate schema.yaml --allow-network
```

Network access includes timeouts and size limits. Override via environment:
- `TEDS_NETWORK_TIMEOUT` (seconds, default: 5)
- `TEDS_NETWORK_MAX_BYTES` (bytes, default: 5MB)

## Contributing

- Use [Conventional Commits](https://conventionalcommits.org/) (feat, fix, docs, etc.)
- Keep changes focused and add tests under `tests/`
- Run tests before submitting: `pytest -q`

## License

[Add license information]
