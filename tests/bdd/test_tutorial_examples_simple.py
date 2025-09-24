"""Simple BDD tests for key tutorial examples verification."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)


def test_json_pointer_generation_basic(temp_workspace):
    """Test basic JSON Pointer generation from tutorial Chapter 2."""
    # Create sample schema
    schema_content = """
components:
  schemas:
    User:
      type: object
      properties:
        name:
          type: string
      examples:
        - name: "Alice"
    Email:
      type: string
      format: email
      examples:
        - "alice@example.com"
"""
    schema_file = temp_workspace / "sample_schemas.yaml"
    schema_file.write_text(schema_content.strip())

    # Run generate command using subprocess to test actual CLI
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(teds_path),
            "generate",
            "sample_schemas.yaml#/components/schemas",
        ],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    print(f"Return code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    print(f"Files in workspace: {list(temp_workspace.iterdir())}")

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if test file was created
    expected_file = temp_workspace / "sample_schemas.components+schemas.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    # Check content
    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Email" in content
    assert "from_examples: true" in content


def test_json_path_config_file_method(temp_workspace):
    """Test JSON Path with configuration file from tutorial Chapter 2."""
    # Create sample schema
    schema_content = """
components:
  schemas:
    User:
      type: object
      examples:
        - name: "Alice"
    Product:
      type: object
      examples:
        - sku: "ABC123"
"""
    schema_file = temp_workspace / "sample_schemas.yaml"
    schema_file.write_text(schema_content.strip())

    # Create config file
    config_content = """
sample_schemas.yaml:
  paths: ["$.components.schemas.*"]
"""
    config_file = temp_workspace / "config.yaml"
    config_file.write_text(config_content.strip())

    # Run generate command
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [sys.executable, str(teds_path), "generate", "@config.yaml"],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if test file was created
    expected_file = temp_workspace / "sample_schemas.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    # Check content
    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Product" in content


def test_json_path_direct_yaml_argument(temp_workspace):
    """Test JSON Path with direct YAML argument from tutorial Chapter 2."""
    # Create sample schema
    schema_content = """
components:
  schemas:
    User:
      type: object
      examples:
        - name: "Alice"
    Email:
      type: string
      format: email
      examples:
        - "alice@example.com"
"""
    schema_file = temp_workspace / "sample_schemas.yaml"
    schema_file.write_text(schema_content.strip())

    # Run generate command with direct YAML argument
    yaml_config = '{"sample_schemas.yaml": {"paths": ["$.components.schemas.*"]}}'
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [sys.executable, str(teds_path), "generate", yaml_config],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if test file was created
    expected_file = temp_workspace / "sample_schemas.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    # Check content
    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Email" in content


def test_json_path_simple_list_format(temp_workspace):
    """Test JSON Path with simple list format from tutorial Chapter 2."""
    # Create sample schema
    schema_content = """
components:
  schemas:
    User:
      type: object
      examples:
        - name: "Alice"
$defs:
  Product:
    type: object
    examples:
      - sku: "ABC123"
"""
    schema_file = temp_workspace / "schema.yaml"
    schema_file.write_text(schema_content.strip())

    # Run generate command with simple list format
    # Write JSON config to a temporary file to avoid shell escaping issues
    import json

    config_data = {"schema.yaml": ["$.components.schemas.*", '$["$defs"].*']}
    config_file = temp_workspace / "temp_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)

    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [sys.executable, str(teds_path), "generate", f"@{config_file}"],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if test file was created
    expected_file = temp_workspace / "schema.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    # Check content
    content = expected_file.read_text()
    assert "schema.yaml#/components/schemas/User" in content
    assert "schema.yaml#/$defs/Product" in content


def test_basic_email_validation_from_tutorial(temp_workspace):
    """Test basic email validation from tutorial Chapter 1."""
    # Create email schema
    schema_content = """
type: string
format: email
"""
    schema_file = temp_workspace / "user_email.yaml"
    schema_file.write_text(schema_content.strip())

    # Create test specification
    test_content = """
version: "1.0.0"
tests:
  user_email.yaml#:
    valid:
      simple_email:
        description: "Basic valid email"
        payload: "alice@example.com"
      email_with_subdomain:
        description: "Email with subdomain"
        payload: "bob@mail.company.com"
    invalid:
      missing_at:
        description: "Email without @ symbol"
        payload: "alice.example.com"
      missing_domain:
        description: "Email without domain"
        payload: "alice@"
"""
    test_file = temp_workspace / "user_email.tests.yaml"
    test_file.write_text(test_content.strip())

    # Run verify command
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(teds_path),
            "verify",
            "user_email.tests.yaml",
            "--output-level",
            "all",
        ],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert (
        result.returncode == 1
    ), f"Verify command should report validation errors: {result.stderr}"

    # Check that output contains expected results
    output = result.stdout
    assert "simple_email" in output
    assert "email_with_subdomain" in output
    assert "missing_domain" in output


def test_template_variables_json_pointer(temp_workspace):
    """Test template variables with JSON Pointer from tutorial Chapter 6."""
    # Create schema
    schema_content = """
components:
  schemas:
    User:
      type: object
      examples:
        - name: "Alice"
"""
    schema_file = temp_workspace / "schema.yaml"
    schema_file.write_text(schema_content.strip())

    # Run generate with template variables
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(teds_path),
            "generate",
            "schema.yaml#/components/schemas={base}.{pointer}.custom.yaml",
        ],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if custom named file was created
    expected_file = temp_workspace / "schema.components+schemas.custom.yaml"
    assert expected_file.exists(), "Custom named test file was not created"

    # Check content
    content = expected_file.read_text()
    assert "schema.yaml#/components/schemas/User" in content


def test_pointer_sanitization_plus_signs(temp_workspace):
    """Test JSON Pointer sanitization with plus signs from tutorial Chapter 6."""
    # Create schema
    schema_content = """
components:
  schemas:
    User:
      type: object
      examples:
        - name: "Alice"
"""
    schema_file = temp_workspace / "api.yaml"
    schema_file.write_text(schema_content.strip())

    # Run generate command
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(teds_path),
            "generate",
            "api.yaml#/components/schemas/User",
        ],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if sanitized filename was created
    expected_file = temp_workspace / "api.components+schemas+User.tests.yaml"
    assert expected_file.exists(), "Sanitized filename test file was not created"


def test_defs_pointer_sanitization(temp_workspace):
    """Test $defs pointer sanitization from tutorial Chapter 6."""
    # Create schema
    schema_content = """
$defs:
  Address:
    type: object
    examples:
      - street: "Main St"
"""
    schema_file = temp_workspace / "schema.yaml"
    schema_file.write_text(schema_content.strip())

    # Run generate command
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [sys.executable, str(teds_path), "generate", "schema.yaml#/$defs/Address"],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert result.returncode == 0, f"Generate command failed: {result.stderr}"

    # Check if sanitized filename was created
    expected_file = temp_workspace / "schema.$defs+Address.tests.yaml"
    assert expected_file.exists(), "$defs sanitized filename test file was not created"
