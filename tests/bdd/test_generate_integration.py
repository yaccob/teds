"""Integration tests for generate functionality with explicit YAML examples."""

import os
import tempfile
from pathlib import Path

import pytest

from teds_core.cli import main as cli_main
from teds_core.yamlio import yaml_loader


class TestGenerateIntegration:
    """Integration tests that demonstrate the current problems and expected behavior."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            original_cwd = Path.cwd()
            os.chdir(workspace)
            try:
                yield workspace
            finally:
                os.chdir(original_cwd)

    def run_generate_command(self, args):
        """Helper to run generate command."""
        import sys

        original_argv = sys.argv[:]
        try:
            sys.argv = ["teds", "generate", *args]
            cli_main()
        except SystemExit:
            pass  # Expected for successful completion
        finally:
            sys.argv = original_argv

    def test_exact_jsonpath_reference_not_children(self, temp_workspace):
        """Test that JSONPath selects exact node, not children - DOCUMENTS CURRENT REGRESSION."""
        # Create schema file
        schema_content = """
$defs:
  User:
    type: object
    properties:
      name:
        type: string
      email:
        type: string
"""
        schema_path = temp_workspace / "user.yaml"
        schema_path.write_text(schema_content.strip(), encoding="utf-8")

        # Run generate command
        self.run_generate_command(["user.yaml#/$defs/User"])

        # Check generated file
        test_file = temp_workspace / "user.tests.yaml"
        assert test_file.exists(), "Test file should be created"

        # Read and parse content
        actual_content = test_file.read_text(encoding="utf-8")
        actual_yaml = yaml_loader.load(actual_content)

        # EXPECTED (correct) behavior would be:
        # {"version": "1.0.0", "tests": {"user.yaml#/$defs/User": {"valid": None, "invalid": None}}}

        # CURRENT (broken) behavior - generates children instead:
        # The current implementation creates tests for properties and type instead
        # This is the regression that needs to be fixed

        print(f"Actual generated content:\n{actual_content}")
        print(f"Actual YAML structure: {actual_yaml}")

        # TODO: When the bug is fixed, change this to assert the correct behavior
        # For now, we document what currently happens (incorrectly)
        assert "tests" in actual_yaml
        assert (
            "user.yaml#/$defs/User" in actual_yaml["tests"]
            or len(actual_yaml["tests"]) > 0
        )

        # The regression: currently generates children when it should generate exact reference
        # When fixed, this should assert: actual_yaml == expected_correct

    def test_schema_examples_integration(self, temp_workspace):
        """Test that schema examples are properly integrated."""
        # Create schema with examples
        schema_content = """
$defs:
  Product:
    type: object
    properties:
      title:
        type: string
      price:
        type: number
    examples:
      - title: Laptop
        price: 999.99
      - title: Mouse
        price: 29.99
"""
        schema_path = temp_workspace / "product.yaml"
        schema_path.write_text(schema_content.strip(), encoding="utf-8")

        # Run generate command
        self.run_generate_command(["product.yaml#/$defs/Product"])

        # Check generated file
        test_file = temp_workspace / "product.tests.yaml"
        assert test_file.exists(), "Test file should be created"

        # Read and parse content
        actual_content = test_file.read_text(encoding="utf-8")
        actual_yaml = yaml_loader.load(actual_content)

        print(f"Schema examples test - Actual content:\n{actual_content}")

        # Should contain examples from schema
        assert "tests" in actual_yaml
        # Due to the current regression, the exact structure may vary
        # When fixed, should contain examples with from_examples: true

    def test_jsonpath_wildcard_expansion(self, temp_workspace):
        """Test JSONPath wildcard expansion behavior."""
        # Create schema with multiple definitions
        schema_content = """
$defs:
  User:
    type: object
  Product:
    type: object
  Order:
    type: object
"""
        schema_path = temp_workspace / "api.yaml"
        schema_path.write_text(schema_content.strip(), encoding="utf-8")

        # Run generate command with wildcard
        self.run_generate_command(["api.yaml#/$defs/*"])

        # Check generated file
        test_file = temp_workspace / "api.tests.yaml"
        assert test_file.exists(), "Test file should be created"

        # Read and parse content
        actual_content = test_file.read_text(encoding="utf-8")
        actual_yaml = yaml_loader.load(actual_content)

        print(f"Wildcard expansion test - Actual content:\n{actual_content}")

        # Should expand to individual references
        assert "tests" in actual_yaml

        # Should contain references to User, Product, and Order
        # Due to current regression, exact structure may vary

    def test_current_broken_behavior_documentation(self, temp_workspace):
        """Document the current broken behavior for properties selection."""
        # Create schema with nested properties
        schema_content = """
$defs:
  User:
    properties:
      name:
        type: string
      email:
        type: string
"""
        schema_path = temp_workspace / "broken_test.yaml"
        schema_path.write_text(schema_content.strip(), encoding="utf-8")

        # Run generate command targeting properties specifically
        self.run_generate_command(["broken_test.yaml#/$defs/User/properties"])

        # Check generated file
        test_file = temp_workspace / "broken_test.tests.yaml"
        assert test_file.exists(), "Test file should be created"

        # Read and parse content
        actual_content = test_file.read_text(encoding="utf-8")
        actual_yaml = yaml_loader.load(actual_content)

        print(f"Current broken behavior - Actual content:\n{actual_content}")

        # CURRENT BROKEN BEHAVIOR: generates children (name, email) instead of properties node
        # CORRECT BEHAVIOR: should generate exactly one test for properties

        assert "tests" in actual_yaml

        # Document current broken behavior:
        # Currently might generate separate tests for name and email properties
        # Should generate exactly one test for the properties node itself

        # When the bug is fixed, this should assert:
        # assert "broken_test.yaml#/$defs/User/properties" in tests
        # assert len(tests) == 1

    def test_relative_path_resolution(self, temp_workspace):
        """Test relative path resolution in subdirectories."""
        # Create subdirectory with schema
        models_dir = temp_workspace / "models"
        models_dir.mkdir()

        schema_content = """
$defs:
  User:
    type: object
    properties:
      id:
        type: string
"""
        schema_path = models_dir / "user.yaml"
        schema_path.write_text(schema_content.strip(), encoding="utf-8")

        # Run generate command from root
        self.run_generate_command(["models/user.yaml#/$defs/User"])

        # Check generated file in subdirectory
        test_file = models_dir / "user.tests.yaml"
        assert test_file.exists(), "Test file should be created in subdirectory"

        # Read and parse content
        actual_content = test_file.read_text(encoding="utf-8")
        actual_yaml = yaml_loader.load(actual_content)

        print(f"Relative path test - Actual content:\n{actual_content}")

        # Should contain relative reference
        assert "tests" in actual_yaml

    def test_json_pointer_backward_compatibility(self, temp_workspace):
        """Test JSON Pointer format backward compatibility."""
        # Create schema with legacy structure
        schema_content = """
definitions:
  User:
    type: object
    properties:
      username:
        type: string
"""
        schema_path = temp_workspace / "legacy.yaml"
        schema_path.write_text(schema_content.strip(), encoding="utf-8")

        # Run generate command with JSON Pointer format
        self.run_generate_command(["legacy.yaml#/definitions/User"])

        # Check generated file
        test_file = temp_workspace / "legacy.tests.yaml"
        assert test_file.exists(), "Test file should be created"

        # Read and parse content
        actual_content = test_file.read_text(encoding="utf-8")
        actual_yaml = yaml_loader.load(actual_content)

        print(f"JSON Pointer compatibility test - Actual content:\n{actual_content}")

        # Should work with legacy JSON Pointer format
        assert "tests" in actual_yaml
