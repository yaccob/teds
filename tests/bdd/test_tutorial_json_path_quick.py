"""
Quick verification that JSON Path examples from tutorial work correctly.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

from teds_core.cli import main as cli_main


def run_teds_command(*args):
    """Helper function to run teds CLI commands in tests."""
    original_argv = sys.argv.copy()
    try:
        sys.argv = ["teds", *list(args)]
        cli_main()
        return 0
    except SystemExit as e:
        return e.code
    finally:
        sys.argv = original_argv


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


def test_json_path_config_file_method_works(temp_workspace):
    """Verify JSON Path @config.yaml method from tutorial works."""
    # Create schema
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

    # Run: teds generate @config.yaml
    exit_code = run_teds_command("generate", "@config.yaml")
    assert exit_code == 0, "JSON Path @config.yaml method failed"

    # Verify output
    expected_file = temp_workspace / "sample_schemas.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Product" in content
    print("✅ JSON Path @config.yaml method works!")


def test_json_path_direct_yaml_works(temp_workspace):
    """Verify JSON Path direct YAML argument from tutorial works."""
    # Create schema
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

    # Run: teds generate '{"sample_schemas.yaml": {"paths": ["$.components.schemas.*"]}}'
    yaml_config = '{"sample_schemas.yaml": {"paths": ["$.components.schemas.*"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "JSON Path direct YAML method failed"

    # Verify output
    expected_file = temp_workspace / "sample_schemas.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Email" in content
    print("✅ JSON Path direct YAML argument works!")


def test_json_path_simple_list_format_works(temp_workspace):
    """Verify JSON Path simple list format from tutorial works."""
    # Create schema with both components and $defs
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

    # Run: teds generate '{"schema.yaml": ["$.components.schemas.*", "$[\"$defs\"].*"]}'
    # Use config file to avoid shell escaping issues
    import json

    config_data = {"schema.yaml": ["$.components.schemas.*", '$["$defs"].*']}
    config_file = temp_workspace / "temp_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
    exit_code = run_teds_command("generate", f"@{config_file}")
    assert exit_code == 0, "JSON Path simple list format failed"

    # Verify results
    expected_file = temp_workspace / "schema.tests.yaml"
    assert expected_file.exists(), "Test file was not created"

    content = expected_file.read_text()
    assert "schema.yaml#/components/schemas/User" in content
    assert "schema.yaml#/$defs/Product" in content
    print("✅ JSON Path simple list format works!")


def test_json_path_custom_target_works(temp_workspace):
    """Verify JSON Path custom target from tutorial works."""
    # Create schema
    schema_content = """
$defs:
  User:
    type: object
    examples:
      - name: "Alice"
  Product:
    type: object
    examples:
      - sku: "ABC123"
"""
    schema_file = temp_workspace / "schema.yaml"
    schema_file.write_text(schema_content.strip())

    # Run: teds generate '{"schema.yaml": {"paths": ["$[\"$defs\"].*"], "target": "custom_tests.yaml"}}'
    # Use config file to avoid shell escaping issues
    import json

    config_data = {
        "schema.yaml": {"paths": ['$["$defs"].*'], "target": "custom_tests.yaml"}
    }
    config_file = temp_workspace / "temp_config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)
    exit_code = run_teds_command("generate", f"@{config_file}")
    assert exit_code == 0, "JSON Path custom target failed"

    # Verify custom target file was created
    expected_file = temp_workspace / "custom_tests.yaml"
    assert expected_file.exists(), "Custom target file was not created"

    content = expected_file.read_text()
    assert "schema.yaml#/$defs/User" in content
    assert "schema.yaml#/$defs/Product" in content
    print("✅ JSON Path custom target works!")


def test_json_path_vs_json_pointer_comparison(temp_workspace):
    """Verify both JSON Path and JSON Pointer work as documented."""
    # Create schema
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
    schema_file = temp_workspace / "comparison.yaml"
    schema_file.write_text(schema_content.strip())

    # Test JSON Path with wildcard
    yaml_config = '{"comparison.yaml": {"paths": ["$.components.schemas.*"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "JSON Path with wildcard failed"

    # Verify JSON Path output
    jsonpath_file = temp_workspace / "comparison.tests.yaml"
    assert jsonpath_file.exists(), "JSON Path test file was not created"

    jsonpath_content = jsonpath_file.read_text()
    assert "comparison.yaml#/components/schemas/User" in jsonpath_content
    assert "comparison.yaml#/components/schemas/Product" in jsonpath_content

    # Clean up for JSON Pointer test
    jsonpath_file.unlink()

    # Test JSON Pointer (no wildcard needed)
    exit_code = run_teds_command("generate", "comparison.yaml#/components/schemas")
    assert exit_code == 0, "JSON Pointer generation failed"

    # Verify JSON Pointer output (different filename format)
    pointer_file = temp_workspace / "comparison.components+schemas.tests.yaml"
    assert pointer_file.exists(), "JSON Pointer test file was not created"

    pointer_content = pointer_file.read_text()
    assert "comparison.yaml#/components/schemas/User" in pointer_content
    assert "comparison.yaml#/components/schemas/Product" in pointer_content

    print("✅ Both JSON Path and JSON Pointer work as documented!")
    print("✅ JSON Path uses wildcards, JSON Pointer auto-expands children!")


if __name__ == "__main__":
    print("Running focused JSON Path tutorial verification...")
    pytest.main([__file__, "-v", "-s"])
