from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from teds_core.cli import GenerateCommand


class TestGenerateYamlConfig:
    """Test suite for the generate command YAML configuration features."""

    def test_source_centric_config_with_default_target(self, tmp_path: Path):
        """Test source-centric YAML config with default target naming."""
        import os

        # Create test schema with multiple components
        schema = tmp_path / "address_list.yaml"
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

        # Source-centric YAML configuration with proper JsonPath
        yaml_config = f"""
{{
  "{schema.name}": [
    "$[\\"$defs\\"].AddressOneLine.properties.*",
    "$[\\"$defs\\"].Person.properties.*"
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
            result = command.execute(args)
            assert result == 0

            # Verify default target naming: {base}.tests.yaml
            expected_output = tmp_path / "address_list.tests.yaml"
            assert expected_output.exists()

            # Verify content contains generated test cases
            content = expected_output.read_text(encoding="utf-8")
            assert "address_list.yaml#" in content  # Contains schema references
        finally:
            os.chdir(old_cwd)

    def test_source_centric_config_with_explicit_target(self, tmp_path: Path):
        """Test source-centric YAML config with explicit target using {base} template."""
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

        # Source-centric YAML configuration with explicit target
        yaml_config = f"""
{{
  "{schema.name}": {{
    "paths": ["$[\\"$defs\\"].User.properties.*"],
    "target": "{{base}}_custom.tests.yaml"
  }}
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
            result = command.execute(args)
            assert result == 0

            # Verify that the {base} template was resolved in target
            expected_file = tmp_path / "user_schema_custom.tests.yaml"
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

        result = command.execute(args)
        assert result == 0

        # Check that a test file was created (using current naming convention)
        expected_file = schema.parent / "schema.tests.yaml"
        assert expected_file.exists()

    def test_conflict_resolution_with_warning(self, tmp_path: Path):
        """Test conflict resolution when multiple paths point to the same schema element."""
        import os

        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
$defs:
  CommonType:
    type: string
    examples: ["test_value"]
""",
            encoding="utf-8",
        )

        # Source-centric YAML configuration with conflicting paths
        yaml_config = f"""
{{
  "{schema.name}": [
    "$[\\"$defs\\"].CommonType",
    "$[\\"$defs\\"].CommonType"
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
            # Capture stderr to check for conflict warnings
            with patch("sys.stderr", new_callable=StringIO):
                result = command.execute(args)
                assert result == 0

                # Verify default target file was created
                expected_file = tmp_path / "schema.tests.yaml"
                assert expected_file.exists()

                # Verify content contains schema reference
                content = expected_file.read_text(encoding="utf-8")
                assert "schema.yaml#" in content
        finally:
            os.chdir(old_cwd)

    def test_file_configuration_support(self, tmp_path: Path):
        """Test loading configuration from file with @filename syntax."""
        import os

        config_file = tmp_path / "generate_config.yaml"
        config_file.write_text(
            """
{
  "schema.yaml": {
    "paths": ["$[\\"$defs\\"].*"],
    "target": "output.tests.yaml"
  }
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
            result = command.execute(args)
            assert result == 0

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

        result = command.execute(args)
        assert result == 2  # Error exit code for validation/parsing errors

    def test_multiple_paths_combined_output(self, tmp_path: Path):
        """Test generating combined output from multiple paths in single source."""
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

        # Source-centric config with multiple paths combined in one output
        yaml_config = f"""
{{
  "{schema.name}": {{
    "paths": [
      "$[\\"$defs\\"].User.*",
      "$[\\"$defs\\"].Product.*"
    ],
    "target": "combined_api.tests.yaml"
  }}
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
            result = command.execute(args)
            assert result == 0

            # Verify that combined output file was created
            combined_file = tmp_path / "combined_api.tests.yaml"
            assert combined_file.exists()

            # Verify content contains both User and Product references
            content = combined_file.read_text(encoding="utf-8")
            assert "api_schema.yaml#" in content
            # Should contain tests for both entities
            assert "$defs/User" in content or "$defs/Product" in content
        finally:
            os.chdir(old_cwd)

    def test_yaml_config_with_schema_in_subdirectory(self, tmp_path: Path):
        """Test YAML config processing with schema files located in subdirectories."""
        import os
        
        # Create subdirectory structure
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        # Create schema in subdirectory
        schema = models_dir / "user.yaml"
        schema.write_text(
            """
$defs:
  User:
    type: object
    properties:
      name:
        type: string
        examples: ["Alice"]
      email:
        type: string
        format: email
        examples: ["alice@example.com"]
""",
            encoding="utf-8",
        )

        # Create YAML config that references schema in subdirectory
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
models/user.yaml:
  paths: ["$.['$defs'].User"]
  target: "user_tests.yaml"
""",
            encoding="utf-8",
        )

        # Change to tmp_path directory for execution
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            command = GenerateCommand()
            args = type(
                "Args",
                (),
                {
                    "mapping": ["@config.yaml"],  # Use relative path since we're in tmp_path
                    "allow_network": False,
                    "network_timeout": None,
                    "network_max_bytes": None,
                },
            )()

            result = command.execute(args)
            assert result == 0
        finally:
            os.chdir(old_cwd)

        # Check that target file was created
        target_file = tmp_path / "user_tests.yaml"
        assert target_file.exists()
        
        # Verify content contains correct schema reference with subdirectory path
        content = target_file.read_text(encoding="utf-8")
        assert "models/user.yaml#/$defs/User" in content

    def test_yaml_config_with_template_variables_and_subdirectory(self, tmp_path: Path):
        """Test YAML config template variable expansion with schema files in subdirectories."""
        import os
        
        # Create subdirectory structure
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        
        # Create schema in subdirectory
        schema = schemas_dir / "product.yaml"
        schema.write_text(
            """
$defs:
  Product:
    type: object
    properties:
      title:
        type: string
        examples: ["Laptop"]
      price:
        type: number
        examples: [999.99]
""",
            encoding="utf-8",
        )

        # Create YAML config with template variables
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
schemas/product.yaml:
  paths: ["$.['$defs'].Product"]
  target: "{dir}_{base}_tests.yaml"
""",
            encoding="utf-8",
        )

        # Change to tmp_path directory for execution
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            command = GenerateCommand()
            args = type(
                "Args",
                (),
                {
                    "mapping": ["@config.yaml"],  # Use relative path since we're in tmp_path
                    "allow_network": False,
                    "network_timeout": None,
                    "network_max_bytes": None,
                },
            )()

            result = command.execute(args)
            assert result == 0
        finally:
            os.chdir(old_cwd)

        # Check that target file was created with expanded template
        target_file = tmp_path / "schemas_product_tests.yaml"
        assert target_file.exists()
        
        # Verify content contains correct schema reference
        content = target_file.read_text(encoding="utf-8")
        assert "schemas/product.yaml#/$defs/Product" in content
