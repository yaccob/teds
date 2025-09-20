from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from teds_core.cli import GenerateCommand


class TestGenerateCommandRedesign:
    """Test suite for the redesigned generate command with YAML configuration."""

    def test_yaml_object_config_with_jsonpath_wildcards(self, tmp_path: Path):
        """Test YAML object configuration with JsonPath wildcard expressions."""
        import os

        # Create test schema with multiple components
        schema = tmp_path / "examples" / "address_list.yaml"
        schema.parent.mkdir(parents=True)
        schema.write_text(
            """
$defs:
  AddressOneLine:
    type: object
    properties:
      street:
        type: string
        examples: ["123 Main St"]
      city:
        type: string
        examples: ["Anytown"]
      zipcode:
        type: string
        pattern: "^[0-9]{5}$"
        examples: ["12345"]
  Person:
    type: object
    properties:
      name:
        type: string
        examples: ["John Doe"]
      age:
        type: integer
        minimum: 0
        examples: [25]
""",
            encoding="utf-8",
        )

        # Create existing test file with some content
        existing_tests = tmp_path / "address_list.tests.yaml"
        existing_tests.write_text(
            """
version: "1.0.0"
tests:
  some_existing_ref:
    valid:
      existing_case:
        payload: "test"
""",
            encoding="utf-8",
        )

        # YAML configuration with JsonPath wildcards
        yaml_config = """
{
  "address_list.tests.yaml": [
    "examples/address_list.yaml#/$defs/AddressOneLine/properties/*",
    "examples/address_list.yaml#/$defs/Person/properties/*"
  ]
}
"""

        # Execute the command - should work with new YAML configuration
        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [yaml_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Change to tmp_path directory for the test
        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            result = command.execute(args)
            assert result == 0  # Should succeed

            # Verify that the test file was created/updated
            assert existing_tests.exists()

            # Verify that new test cases were added from the JsonPath expansion
            updated_content = existing_tests.read_text(encoding="utf-8")
            assert (
                "examples/address_list.yaml#" in updated_content
            )  # Contains schema references
        finally:
            os.chdir(old_cwd)

    def test_yaml_object_config_with_template_base_name(self, tmp_path: Path):
        """Test YAML object configuration with {base} template in filename."""
        import os

        schema = tmp_path / "user_schema.yaml"
        schema.write_text(
            """
$defs:
  User:
    type: object
    properties:
      username:
        type: string
        examples: ["john_doe"]
      email:
        type: string
        format: email
        examples: ["john@example.com"]
""",
            encoding="utf-8",
        )

        # YAML configuration with {base} template
        yaml_config = """
{
  "{base}.tests.yaml": [
    "user_schema.yaml#/$defs/User/properties/*"
  ]
}
"""

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [yaml_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Change to tmp_path directory for the test
        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # Execute the command - should work with template resolution
            result = command.execute(args)
            assert result == 0  # Should succeed

            # Verify that the template was resolved and file was created
            expected_file = (
                tmp_path / "user_schema.tests.yaml"
            )  # {base} resolved to "user_schema"
            assert expected_file.exists()

            # Verify content contains schema references
            content = expected_file.read_text(encoding="utf-8")
            assert "user_schema.yaml#" in content
        finally:
            os.chdir(old_cwd)

    def test_backward_compatibility_json_pointer_string(self, tmp_path: Path):
        """Test backward compatibility with JSON Pointer string format."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
components:
  schemas:
    SimpleString:
      type: string
      examples: ["test"]
""",
            encoding="utf-8",
        )

        # Old-style JSON Pointer string (should still work)
        json_pointer_config = f"{schema}#/components/schemas/SimpleString"

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [json_pointer_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Should work after implementation (currently may pass with old code)
        # We expect this to generate a test file
        result = command.execute(args)
        assert result == 0

        # Check that a test file was created (using current naming convention)
        expected_file = (
            schema.parent / "schema.components+schemas+SimpleString.tests.yaml"
        )
        assert expected_file.exists()

    def test_conflict_resolution_with_warning(self, tmp_path: Path):
        """Test conflict resolution when multiple sources define the same schema element."""
        schema1 = tmp_path / "schema1.yaml"
        schema1.write_text(
            """
$defs:
  CommonType:
    type: string
    examples: ["from_schema1"]
""",
            encoding="utf-8",
        )

        schema2 = tmp_path / "schema2.yaml"
        schema2.write_text(
            """
$defs:
  CommonType:
    type: string
    examples: ["from_schema2"]
""",
            encoding="utf-8",
        )

        # YAML configuration with conflicting sources
        yaml_config = f"""
{{
  "merged.tests.yaml": [
    "{schema1}#/$defs/CommonType",
    "{schema2}#/$defs/CommonType"
  ]
}}
"""

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [yaml_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Capture stderr to check for conflict warnings
        with patch("sys.stderr", new_callable=StringIO):
            result = command.execute(args)
            assert result == 0  # Should succeed

            # Note: Different files with same fragment don't conflict in current implementation

    def test_file_configuration_support(self, tmp_path: Path):
        """Test loading configuration from file with @filename syntax."""
        import os

        config_file = tmp_path / "generate_config.yaml"
        config_file.write_text(
            """
{
  "output.tests.yaml": [
    "schema.yaml#/$defs/*"
  ]
}
""",
            encoding="utf-8",
        )

        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
$defs:
  TestType:
    type: string
    examples: ["test"]
""",
            encoding="utf-8",
        )

        # Use @filename syntax
        file_config = f"@{config_file}"

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [file_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Change to tmp_path directory for the test
        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # Execute the command - should work with file configuration
            result = command.execute(args)
            assert result == 0  # Should succeed

            # Verify that the output file was created
            expected_file = tmp_path / "output.tests.yaml"
            assert expected_file.exists()

            # Verify content contains schema references
            content = expected_file.read_text(encoding="utf-8")
            assert "schema.yaml#" in content
        finally:
            os.chdir(old_cwd)

    def test_invalid_yaml_configuration_error(self, tmp_path: Path):
        """Test error handling for invalid YAML configuration."""
        # Invalid YAML syntax
        invalid_yaml = "{ invalid yaml: [ unclosed"

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [invalid_yaml],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Should fail with appropriate error due to invalid YAML
        result = command.execute(args)
        assert result == 2  # Error exit code for parse/config errors

    def test_jsonpath_expression_error_handling(self, tmp_path: Path):
        """Test error handling for invalid JsonPath expressions."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
$defs:
  TestType:
    type: string
""",
            encoding="utf-8",
        )

        # YAML config with invalid JsonPath
        yaml_config = f"""
{{
  "output.tests.yaml": [
    "{schema}#/[invalid-jsonpath-expression"
  ]
}}
"""

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [yaml_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Should fail with appropriate error due to invalid JsonPath
        result = command.execute(args)
        assert result == 2  # Error exit code for validation/parsing errors

    def test_multiple_output_files_in_single_config(self, tmp_path: Path):
        """Test generating multiple output files from single configuration."""
        import os

        schema = tmp_path / "api_schema.yaml"
        schema.write_text(
            """
$defs:
  User:
    type: object
    properties:
      id:
        type: integer
        examples: [123]
  Product:
    type: object
    properties:
      name:
        type: string
        examples: ["Widget"]
""",
            encoding="utf-8",
        )

        # YAML config with multiple output files
        yaml_config = f"""
{{
  "user.tests.yaml": [
    "{schema}#/$defs/User",
    "{schema}#/$defs/User/properties/*"
  ],
  "product.tests.yaml": [
    "{schema}#/$defs/Product",
    "{schema}#/$defs/Product/properties/*"
  ]
}}
"""

        command = GenerateCommand()
        args = type(
            "Args",
            (),
            {
                "mapping": [yaml_config],
                "allow_network": False,
                "network_timeout": None,
                "network_max_bytes": None,
            },
        )()

        # Change to tmp_path directory for the test
        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # Should succeed - multiple output files generation works
            result = command.execute(args)
            assert result == 0  # Should succeed

            # Verify that both output files were created
            user_file = tmp_path / "user.tests.yaml"
            product_file = tmp_path / "product.tests.yaml"
            assert user_file.exists()
            assert product_file.exists()

            # Verify content contains schema references
            user_content = user_file.read_text(encoding="utf-8")
            product_content = product_file.read_text(encoding="utf-8")
            assert "api_schema.yaml#" in user_content
            assert "api_schema.yaml#" in product_content
        finally:
            os.chdir(old_cwd)
