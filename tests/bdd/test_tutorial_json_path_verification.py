"""
Verification tests for JSON Path examples from the tutorial.

This test suite validates that all JSON Path examples documented in the tutorial
actually work as described, addressing concerns about the accuracy of the
documentation.
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


def test_json_path_config_file_method(temp_workspace):
    """
    Test JSON Path Method 1: Configuration Files (@file syntax)
    From tutorial Chapter 2, section "JSON Path (Alternative Method)"
    """
    # Create schema as documented in tutorial
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

    # Create config file as documented in tutorial
    config_content = """
sample_schemas.yaml:
  paths: ["$.components.schemas.*"]
"""
    config_file = temp_workspace / "config.yaml"
    config_file.write_text(config_content.strip())

    # Run command as documented: teds generate @config.yaml
    exit_code = run_teds_command("generate", "@config.yaml")
    assert exit_code == 0, "Generate command with @config.yaml failed"

    # Verify expected output file was created
    expected_file = temp_workspace / "sample_schemas.tests.yaml"
    assert expected_file.exists(), "Expected test file was not created"

    # Verify content contains expected schema references
    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Product" in content


def test_json_path_direct_yaml_argument(temp_workspace):
    """
    Test JSON Path Method 2: Direct YAML/JSON Arguments
    From tutorial Chapter 2, documented example:
    teds generate '{"sample_schemas.yaml": {"paths": ["$.components.schemas.*"]}}'
    """
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

    # Run command exactly as documented in tutorial
    yaml_config = '{"sample_schemas.yaml": {"paths": ["$.components.schemas.*"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "Direct YAML argument generation failed"

    # Verify results
    expected_file = temp_workspace / "sample_schemas.tests.yaml"
    assert expected_file.exists(), "Expected test file was not created"

    content = expected_file.read_text()
    assert "sample_schemas.yaml#/components/schemas/User" in content
    assert "sample_schemas.yaml#/components/schemas/Email" in content


def test_json_path_specific_targets(temp_workspace):
    """
    Test JSON Path with specific targets
    From tutorial example:
    teds generate '{"api.yaml": {"paths": ["$.components.schemas.User", "$.components.schemas.Product"]}}'
    """
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
    Tag:
      type: string
      examples:
        - "important"
"""
    schema_file = temp_workspace / "api.yaml"
    schema_file.write_text(schema_content.strip())

    # Run command as documented
    yaml_config = '{"api.yaml": {"paths": ["$.components.schemas.User", "$.components.schemas.Product"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "Specific targets generation failed"

    # Verify results
    expected_file = temp_workspace / "api.tests.yaml"
    assert expected_file.exists(), "Expected test file was not created"

    content = expected_file.read_text()
    assert "api.yaml#/components/schemas/User" in content
    assert "api.yaml#/components/schemas/Product" in content
    # Should NOT contain Tag (not specified in paths)
    assert "api.yaml#/components/schemas/Tag" not in content


def test_json_path_custom_target_file(temp_workspace):
    """
    Test JSON Path with custom target file
    From tutorial example:
    teds generate '{"schema.yaml": {"paths": ["$[\"$defs\"].*"], "target": "custom_tests.yaml"}}'
    """
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

    # Run command with custom target as documented
    yaml_config = '{"schema.yaml": {"paths": ["$[\\"$defs\\"].*"], "target": "custom_tests.yaml"}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "Custom target generation failed"

    # Verify custom target file was created
    expected_file = temp_workspace / "custom_tests.yaml"
    assert expected_file.exists(), "Custom target file was not created"

    content = expected_file.read_text()
    assert "schema.yaml#/$defs/User" in content
    assert "schema.yaml#/$defs/Product" in content


def test_json_path_simple_list_format(temp_workspace):
    """
    Test JSON Path Method 3: Simple List Format
    From tutorial example:
    teds generate '{"schema.yaml": ["$.components.schemas.*", "$[\"$defs\"].*"]}'
    """
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

    # Run command with simple list format as documented
    yaml_config = '{"schema.yaml": ["$.components.schemas.*", "$[\\"$defs\\"].*"]}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "Simple list format generation failed"

    # Verify results
    expected_file = temp_workspace / "schema.tests.yaml"
    assert expected_file.exists(), "Expected test file was not created"

    content = expected_file.read_text()
    assert "schema.yaml#/components/schemas/User" in content
    assert "schema.yaml#/$defs/Product" in content


def test_json_path_array_indices(temp_workspace):
    """
    Test JSON Path with array indices
    From tutorial JSON Path examples section showing array access like "$.allOf[0]"
    """
    # Create schema with allOf structure
    schema_content = """
$defs:
  User:
    allOf:
      - type: object
        properties:
          name:
            type: string
        examples:
          - name: "Alice"
      - type: object
        properties:
          email:
            type: string
        examples:
          - email: "alice@example.com"
"""
    schema_file = temp_workspace / "schema.yaml"
    schema_file.write_text(schema_content.strip())

    # Test array index access
    yaml_config = '{"schema.yaml": {"paths": ["$[\\"$defs\\"].User.allOf[0]"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "Array index generation failed"

    # Verify results
    expected_file = temp_workspace / "schema.tests.yaml"
    assert expected_file.exists(), "Expected test file was not created"

    content = expected_file.read_text()
    assert "schema.yaml#/$defs/User/allOf/0" in content


def test_json_path_wildcard_expansion(temp_workspace):
    """
    Test JSON Path wildcard expansion
    Verifies that wildcards expand only at the specified level as documented
    """
    # Create nested schema structure
    schema_content = """
components:
  schemas:
    User:
      properties:
        profile:
          properties:
            name:
              type: string
              examples:
                - "Alice"
            age:
              type: number
              examples:
                - 25
    Product:
      properties:
        details:
          properties:
            title:
              type: string
              examples:
                - "Product Name"
            price:
              type: number
              examples:
                - 19.99
"""
    schema_file = temp_workspace / "nested.yaml"
    schema_file.write_text(schema_content.strip())

    # Test that wildcard expands only at the wildcard level (properties level)
    yaml_config = '{"nested.yaml": {"paths": ["$.components.schemas.*.properties"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "Wildcard expansion failed"

    # Verify results
    expected_file = temp_workspace / "nested.tests.yaml"
    assert expected_file.exists(), "Expected test file was not created"

    content = expected_file.read_text()
    assert "nested.yaml#/components/schemas/User/properties" in content
    assert "nested.yaml#/components/schemas/Product/properties" in content

    # Should NOT contain deeper nested properties (profile, details level)
    assert "nested.yaml#/components/schemas/User/properties/profile" not in content
    assert "nested.yaml#/components/schemas/Product/properties/details" not in content


def test_json_path_vs_json_pointer_difference(temp_workspace):
    """
    Test that demonstrates the key difference between JSON Path and JSON Pointer
    as documented in tutorial:
    - JSON Pointer: #/components/schemas → finds schemas directly at this location
    - JSON Path: $.components.schemas.* → requires * wildcard to select multiple items
    """
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

    # Test JSON Path - requires explicit wildcard
    yaml_config = '{"comparison.yaml": {"paths": ["$.components.schemas.*"]}}'
    exit_code = run_teds_command("generate", yaml_config)
    assert exit_code == 0, "JSON Path with wildcard failed"

    # Verify it finds both schemas
    expected_file = temp_workspace / "comparison.tests.yaml"
    assert expected_file.exists(), "JSON Path test file was not created"

    content = expected_file.read_text()
    assert "comparison.yaml#/components/schemas/User" in content
    assert "comparison.yaml#/components/schemas/Product" in content

    # Clean up for JSON Pointer test
    expected_file.unlink()

    # Test JSON Pointer - no wildcard needed, expands children automatically
    exit_code = run_teds_command("generate", "comparison.yaml#/components/schemas")
    assert exit_code == 0, "JSON Pointer generation failed"

    # Verify JSON Pointer created appropriate file
    pointer_file = temp_workspace / "comparison.components+schemas.tests.yaml"
    assert pointer_file.exists(), "JSON Pointer test file was not created"

    pointer_content = pointer_file.read_text()
    assert "comparison.yaml#/components/schemas/User" in pointer_content
    assert "comparison.yaml#/components/schemas/Product" in pointer_content

    print("✅ Both JSON Path and JSON Pointer methods work as documented!")
    print(
        "✅ JSON Path wildcards and JSON Pointer auto-expansion both function correctly!"
    )


if __name__ == "__main__":
    # Quick standalone test to verify examples work
    print("Running JSON Path tutorial verification tests...")
    pytest.main([__file__, "-v"])
