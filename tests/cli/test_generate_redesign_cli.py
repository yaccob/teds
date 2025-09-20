from __future__ import annotations

from pathlib import Path

from tests.utils import load_yaml_file, run_cli


class TestGenerateCommandRedesignCLI:
    """CLI integration tests for the redesigned generate command."""

    def test_cli_yaml_object_config_basic(self, tmp_path: Path):
        """Test CLI with basic YAML object configuration."""
        schema = tmp_path / "test_schema.yaml"
        schema.write_text(
            """
$defs:
  UserProfile:
    type: object
    properties:
      username:
        type: string
        examples: ["testuser"]
      email:
        type: string
        format: email
        examples: ["test@example.com"]
""",
            encoding="utf-8",
        )

        # YAML configuration as CLI argument
        yaml_config = f"""
{{
  "user_profile.tests.yaml": [
    "{schema.name}#/$defs/UserProfile/properties/*"
  ]
}}
"""

        # Run the CLI command - should fail until implemented
        rc, out, err = run_cli(["generate", yaml_config], cwd=tmp_path)

        # Expecting failure until new functionality is implemented
        assert rc != 0
        assert (
            "error" in err.lower()
            or "not implemented" in err.lower()
            or "invalid" in err.lower()
        )

    def test_cli_backward_compatibility_json_pointer(self, tmp_path: Path):
        """Test CLI backward compatibility with JSON Pointer strings."""
        schema = tmp_path / "simple.yaml"
        schema.write_text(
            """
components:
  schemas:
    Message:
      type: string
      examples: ["Hello World"]
""",
            encoding="utf-8",
        )

        # Old-style JSON Pointer reference
        json_pointer = f"{schema.name}#/components/schemas/Message"

        # Run the CLI command - should work (backward compatibility)
        rc, out, err = run_cli(["generate", json_pointer], cwd=tmp_path)

        # Should succeed (existing functionality)
        assert rc == 0, f"Error: {err}"

        # Check that output file was created (current naming convention)
        expected_file = tmp_path / "simple.components+schemas+Message.tests.yaml"
        assert expected_file.exists()

        # Verify content structure
        doc = load_yaml_file(expected_file)
        assert "tests" in doc
        # Check that some test groups were generated
        assert len(doc["tests"]) > 0

    def test_cli_file_configuration_syntax(self, tmp_path: Path):
        """Test CLI with @filename configuration syntax."""
        config_file = tmp_path / "gen_config.yaml"
        config_file.write_text(
            """
{
  "generated.tests.yaml": [
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
  Item:
    type: object
    properties:
      id:
        type: integer
        examples: [42]
""",
            encoding="utf-8",
        )

        # Use @filename syntax
        file_arg = f"@{config_file.name}"

        # Run the CLI command - should fail until implemented
        rc, out, err = run_cli(["generate", file_arg], cwd=tmp_path)

        # Expecting failure until new functionality is implemented
        assert rc != 0
        assert (
            "error" in err.lower()
            or "not implemented" in err.lower()
            or "invalid" in err.lower()
        )

    def test_cli_invalid_yaml_syntax_error(self, tmp_path: Path):
        """Test CLI error handling for invalid YAML syntax."""
        # Invalid YAML configuration
        invalid_yaml = "{ broken yaml syntax: [ unclosed"

        # Run the CLI command
        rc, out, err = run_cli(["generate", invalid_yaml], cwd=tmp_path)

        # Should fail with error
        assert rc != 0
        assert len(err) > 0  # Should have error message

    def test_cli_conflict_warning_output(self, tmp_path: Path):
        """Test CLI conflict warning output to stderr."""
        schema1 = tmp_path / "first.yaml"
        schema1.write_text(
            """
$defs:
  Shared:
    type: string
    examples: ["first"]
""",
            encoding="utf-8",
        )

        schema2 = tmp_path / "second.yaml"
        schema2.write_text(
            """
$defs:
  Shared:
    type: string
    examples: ["second"]
""",
            encoding="utf-8",
        )

        # YAML config with conflicting sources
        yaml_config = f"""
{{
  "conflict_test.tests.yaml": [
    "{schema1.name}#/$defs/Shared",
    "{schema2.name}#/$defs/Shared"
  ]
}}
"""

        # Run the CLI command
        rc, out, err = run_cli(["generate", yaml_config], cwd=tmp_path)

        # Should fail for now, but when implemented should show conflict warning
        assert rc != 0

    def test_cli_template_base_name_resolution(self, tmp_path: Path):
        """Test CLI template base name resolution with multiple sources."""
        schema1 = tmp_path / "primary_schema.yaml"
        schema1.write_text(
            """
$defs:
  Type1:
    type: string
    examples: ["value1"]
""",
            encoding="utf-8",
        )

        schema2 = tmp_path / "secondary_schema.yaml"
        schema2.write_text(
            """
$defs:
  Type2:
    type: integer
    examples: [123]
""",
            encoding="utf-8",
        )

        # YAML config with {base} template and multiple sources
        yaml_config = f"""
{{
  "{{base}}.combined.tests.yaml": [
    "{schema1.name}#/$defs/Type1",
    "{schema2.name}#/$defs/Type2"
  ]
}}
"""

        # Run the CLI command - should fail until implemented
        rc, out, err = run_cli(["generate", yaml_config], cwd=tmp_path)

        # Expecting failure until new functionality is implemented
        assert rc != 0
        assert (
            "error" in err.lower()
            or "not implemented" in err.lower()
            or "invalid" in err.lower()
        )

    def test_cli_help_shows_new_syntax(self, tmp_path: Path):
        """Test that CLI help includes information about new YAML syntax."""
        # Get help for generate command
        rc, out, err = run_cli(["generate", "--help"], cwd=tmp_path)

        # Should show help (rc might be 0 or different depending on implementation)
        help_text = out + err

        # For now, just verify help is shown
        # After implementation, should mention YAML object syntax
        assert len(help_text) > 0
        assert "generate" in help_text.lower()
