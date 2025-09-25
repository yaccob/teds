from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


class TestGenerateConfigurationParser:
    """Test suite for the new generate command configuration parser."""

    def test_parse_yaml_string_to_object(self):
        """Test parsing YAML string to source-centric configuration object."""
        from teds_core.generate import parse_generate_config

        yaml_string = """
{
  "schema.yaml": [
    "$[\\"$defs\\"].Type1",
    "$[\\"$defs\\"].Type2.properties.*"
  ],
  "other_schema.yaml": [
    "$[\\"$defs\\"].*"
  ]
}
"""

        result = parse_generate_config(yaml_string)
        assert isinstance(result, dict)
        assert "schema.yaml" in result
        assert "other_schema.yaml" in result
        assert isinstance(result["schema.yaml"]["paths"], list)

    def test_parse_yaml_string_to_json_pointer(self):
        """Test parsing YAML string that evaluates to JSON Pointer - now normalized to dict."""
        from teds_core.generate import parse_generate_config

        # Simple JSON Pointer string
        json_pointer_string = "schema.yaml#/components/schemas/User"

        result = parse_generate_config(json_pointer_string)
        assert isinstance(result, dict)
        expected = {
            "schema.yaml": {
                "paths": ['$["components"]["schemas"]["User"].*'],
                "target": None,
            }
        }
        assert result == expected

    def test_parse_json_pointer_root_reference(self):
        """Test JSON Pointer root reference normalization."""
        from teds_core.generate import parse_generate_config

        result = parse_generate_config("schema.yaml#/")
        expected = {"schema.yaml": {"paths": ["$.*"], "target": None}}
        assert result == expected

    def test_parse_json_pointer_nested_path(self):
        """Test JSON Pointer with nested path normalization."""
        from teds_core.generate import parse_generate_config

        result = parse_generate_config("api.yaml#/components/schemas/User/properties")
        expected = {
            "api.yaml": {
                "paths": ['$["components"]["schemas"]["User"]["properties"].*'],
                "target": None,
            }
        }
        assert result == expected

    def test_parse_json_pointer_missing_file_path(self):
        """Test JSON Pointer without file path raises error."""
        from teds_core.errors import TedsError
        from teds_core.generate import parse_generate_config

        # Use quotes to prevent YAML comment parsing
        with pytest.raises(TedsError, match="Missing schema file path"):
            parse_generate_config('"#/components/schemas"')

    def test_parse_string_without_fragment_is_valid(self):
        """Test string without # is valid per RFC 3986 (references whole document)."""
        from teds_core.generate import parse_generate_config

        result = parse_generate_config("just-a-string")
        expected = {"just-a-string": {"paths": ["$.*"], "target": None}}
        assert result == expected

    def test_parse_file_reference_syntax(self):
        """Test parsing @filename syntax for configuration files."""
        from teds_core.generate import parse_generate_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
{
  "from_file.tests.yaml": [
    "schema.yaml#/$defs/*"
  ]
}
"""
            )
            config_file = Path(f.name)

        try:
            file_reference = f"@{config_file}"

            result = parse_generate_config(file_reference)
            assert isinstance(result, dict)
            assert "from_file.tests.yaml" in result
        finally:
            config_file.unlink()

    def test_parse_invalid_yaml_error(self):
        """Test error handling for invalid YAML syntax."""
        from teds_core.errors import TedsError
        from teds_core.generate import parse_generate_config

        invalid_yaml = "{ broken: [ syntax"

        with pytest.raises(TedsError, match="Invalid YAML configuration"):
            parse_generate_config(invalid_yaml)

    def test_parse_unsupported_type_error(self):
        """Test error handling for unsupported YAML types."""
        from teds_core.errors import TedsError
        from teds_core.generate import parse_generate_config

        # YAML that parses to unsupported type (list instead of string/object)
        unsupported_yaml = '["item1", "item2"]'

        with pytest.raises(TedsError, match="Configuration must be object or string"):
            parse_generate_config(unsupported_yaml)

    def test_source_centric_template_resolution(self):
        """Test template variable resolution in source-centric configuration."""
        from teds_core.generate import parse_generate_config

        # Source-centric configuration with {base} template in target
        yaml_config = """
{
  "user_schema.yaml": {
    "paths": ["$[\\"$defs\\"].User"],
    "target": "{base}.custom.tests.yaml"
  }
}
"""

        result = parse_generate_config(yaml_config)
        assert isinstance(result, dict)
        assert "user_schema.yaml" in result
        assert result["user_schema.yaml"]["target"] == "{base}.custom.tests.yaml"

    def test_conflict_detection_logic(self):
        """Test conflict detection between multiple sources."""
        from teds_core.generate import detect_conflicts

        sources = [
            "schema1.yaml#/$defs/CommonType",
            "schema1.yaml#/$defs/CommonType",  # Conflict: same ref appears twice
            "schema1.yaml#/$defs/UniqueType",  # No conflict
        ]

        conflicts = detect_conflicts(sources)
        assert len(conflicts) == 1  # Only one conflict
        conflict_ref, indices = conflicts[0]
        assert conflict_ref == "schema1.yaml#/$defs/CommonType"
        assert len(indices) == 2  # Two conflicting sources
        assert indices == [0, 1]  # Indices of duplicate references

    def test_base_name_extraction_multiple_sources(self):
        """Test base name extraction when multiple source files are involved."""
        from teds_core.generate import extract_base_name

        sources = [
            "user_schema.yaml#/$defs/User",
            "product_schema.yaml#/$defs/Product",
            "order_schema.yaml#/$defs/Order",
        ]

        base_name = extract_base_name(sources)
        assert base_name == "user_schema"  # Uses first source file's stem
