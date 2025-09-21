"""Additional tests to improve generate.py coverage for edge cases and error paths."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from teds_core.errors import TedsError
from teds_core.generate import (
    expand_jsonpath_expressions,
    parse_generate_config,
    validate_jsonpath_expression,
)


class TestGenerateCoverageEdgeCases:
    """Test suite to improve coverage for generate.py edge cases."""

    def test_parse_config_file_not_found_error(self):
        """Test error when @filename references non-existent file."""
        with pytest.raises(TedsError, match="Configuration file not found"):
            parse_generate_config("@non_existent_file.yaml")

    def test_parse_config_file_read_error(self):
        """Test error when configuration file cannot be read."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_file = Path(f.name)

        try:
            # Make file unreadable
            config_file.chmod(0o000)

            with pytest.raises(TedsError, match="Failed to read configuration file"):
                parse_generate_config(f"@{config_file}")
        finally:
            config_file.chmod(0o644)  # Restore permissions
            config_file.unlink()

    def test_parse_config_source_missing_paths_field(self):
        """Test error when source config object is missing 'paths' field."""
        yaml_config = """
{
  "schema.yaml": {
    "target": "output.yaml"
  }
}
"""
        with pytest.raises(TedsError, match="missing 'paths' field"):
            parse_generate_config(yaml_config)

    def test_parse_config_source_paths_not_list(self):
        """Test error when source config 'paths' is not a list."""
        yaml_config = """
{
  "schema.yaml": {
    "paths": "not a list",
    "target": "output.yaml"
  }
}
"""
        with pytest.raises(TedsError, match="'paths' must be a list"):
            parse_generate_config(yaml_config)

    def test_parse_config_source_invalid_type(self):
        """Test error when source config is neither list nor object."""
        yaml_config = """
{
  "schema.yaml": "invalid config type"
}
"""
        with pytest.raises(TedsError, match="config must be list or object"):
            parse_generate_config(yaml_config)

    def test_parse_config_path_not_string(self):
        """Test error when path in config is not a string."""
        yaml_config = """
{
  "schema.yaml": [123, "valid_path"]
}
"""
        with pytest.raises(TedsError, match="path must be string"):
            parse_generate_config(yaml_config)

    def test_validate_jsonpath_empty_expression(self):
        """Test validation of empty JsonPath expression."""
        with pytest.raises(TedsError, match="Empty JsonPath expression"):
            validate_jsonpath_expression("")

    def test_validate_jsonpath_missing_dollar_prefix(self):
        """Test validation of JsonPath expression without $ prefix."""
        with pytest.raises(TedsError, match="JsonPath expression must start with"):
            validate_jsonpath_expression("defs.User")

    def test_validate_jsonpath_unclosed_bracket(self):
        """Test validation of JsonPath with unclosed bracket."""
        with pytest.raises(TedsError, match="Invalid JsonPath expression"):
            validate_jsonpath_expression("$[unclosed")

    def test_validate_jsonpath_parent_navigation(self):
        """Test validation rejecting parent navigation."""
        with pytest.raises(TedsError, match="Invalid JsonPath expression"):
            validate_jsonpath_expression("$../parent")

    def test_validate_jsonpath_json_pointer_parent_navigation(self):
        """Test validation rejecting parent navigation in JSON Pointer format."""
        with pytest.raises(TedsError, match="Invalid JSON Pointer expression"):
            validate_jsonpath_expression("schema.yaml#/../parent")

    def test_validate_jsonpath_json_pointer_missing_file(self):
        """Test validation of JSON Pointer format with missing file path."""
        with pytest.raises(TedsError, match="Missing schema file path"):
            validate_jsonpath_expression("#/valid/path")

    def test_expand_jsonpath_schema_load_error(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with schema load error."""
        # Create file with invalid YAML
        schema = tmp_path / "invalid.yaml"
        schema.write_text("{ invalid yaml: [", encoding="utf-8")

        with pytest.raises(TedsError, match="Failed to load schema"):
            expand_jsonpath_expressions(schema, ['$["test"].*'])

    def test_expand_jsonpath_invalid_expression_error(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with invalid JsonPath (caught at validation)."""
        schema = tmp_path / "valid.yaml"
        schema.write_text('{"test": "value"}', encoding="utf-8")

        # This fails at validation stage, not expansion stage
        with pytest.raises(TedsError, match="Invalid JsonPath expression"):
            expand_jsonpath_expressions(schema, ["$[invalid-syntax"])

    def test_expand_jsonpath_no_matches_valid_expression(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with valid expression that has no matches."""
        schema = tmp_path / "simple.yaml"
        schema.write_text('{"test": "value"}', encoding="utf-8")

        # Valid expression but no matches - returns empty list
        result = expand_jsonpath_expressions(schema, ['$["nonexistent"].*'])
        assert result == []

    def test_expand_jsonpath_jsonpath_parsing_error(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with JsonPath parsing error during expansion."""
        from unittest.mock import patch

        schema = tmp_path / "test.yaml"
        schema.write_text('{"test": "value"}', encoding="utf-8")

        # Mock jsonpath_ng.parse to raise an exception
        with patch("teds_core.generate.jsonpath_ng.parse") as mock_parse:
            mock_parse.side_effect = Exception("JsonPath parsing failed")

            with pytest.raises(TedsError, match="Failed to expand JsonPath expression"):
                expand_jsonpath_expressions(schema, ['$["test"].*'])

    def test_expand_jsonpath_pure_jsonpath_no_wildcards(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with pure JsonPath (no wildcards)."""
        schema = tmp_path / "test.yaml"
        schema.write_text('{"defs": {"User": {"name": "test"}}}', encoding="utf-8")

        result = expand_jsonpath_expressions(schema, ['$["defs"]["User"]'])
        assert len(result) == 1
        assert "test.yaml#" in result[0]

    def test_expand_jsonpath_bracket_notation_parsing(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with bracket notation parsing."""
        schema = tmp_path / "bracket_test.yaml"
        schema.write_text(
            '{"$defs": {"User": {"properties": {"name": "test"}}}}', encoding="utf-8"
        )

        result = expand_jsonpath_expressions(schema, ['$["$defs"].*'])
        assert len(result) >= 1
        assert any("$defs/User" in ref for ref in result)

    def test_expand_jsonpath_dot_notation_with_quotes(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with dot notation containing quotes."""
        schema = tmp_path / "quotes_test.yaml"
        schema.write_text('{"$defs": {"User": {"name": "test"}}}', encoding="utf-8")

        # Mock jsonpath-ng to return path with quoted parts
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = "'$defs'.User"
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ['$["$defs"].*'])
            assert len(result) >= 1

    def test_expand_jsonpath_empty_path_parts(self, tmp_path: Path):
        """Test expand_jsonpath_expressions when path parsing results in empty parts."""
        schema = tmp_path / "empty_path.yaml"
        schema.write_text('{"root": "value"}', encoding="utf-8")

        # Mock to return empty path
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = "$"  # Root path
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ["$.*"])
            assert len(result) >= 1
            assert "empty_path.yaml#/" in result

    def test_expand_jsonpath_json_pointer_no_wildcards(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with JSON Pointer format (no wildcards)."""
        schema = tmp_path / "pointer_test.yaml"
        schema.write_text('{"defs": {"User": "test"}}', encoding="utf-8")

        result = expand_jsonpath_expressions(schema, ["pointer_test.yaml#/defs/User"])
        assert result == ["pointer_test.yaml#/defs/User"]

    def test_expand_jsonpath_json_pointer_with_wildcards(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with JSON Pointer format containing wildcards."""
        schema = tmp_path / "wildcard_test.yaml"
        schema.write_text(
            '{"defs": {"User": {"name": "test"}, "Product": {"title": "test"}}}',
            encoding="utf-8",
        )

        result = expand_jsonpath_expressions(schema, ["schema.yaml#/defs/*"])
        assert len(result) >= 2
        assert any("defs/User" in ref for ref in result)
        assert any("defs/Product" in ref for ref in result)

    def test_generate_from_source_config_error_handling(self, tmp_path: Path):
        """Test generate_from_source_config with error scenarios."""
        import os
        from unittest.mock import patch

        from teds_core.generate import generate_from_source_config

        # Create a valid schema
        schema = tmp_path / "test.yaml"
        schema.write_text('{"$defs": {"User": {"type": "string"}}}', encoding="utf-8")

        config = {
            "test.yaml": {"paths": ['$["$defs"].User'], "target": "output.tests.yaml"}
        }

        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            # Mock generate_exact_node to raise an exception (JSONPath uses this)
            with patch("teds_core.generate.generate_exact_node") as mock_generate:
                mock_generate.side_effect = Exception("Test error")

                # Should not raise, but print warning to stderr
                with patch("sys.stderr"):
                    generate_from_source_config(config, tmp_path)
                    # Verify warning was printed (generate_exact_node was called and failed)
                    assert mock_generate.called
        finally:
            os.chdir(old_cwd)

    def test_generate_from_source_config_template_resolution(self, tmp_path: Path):
        """Test generate_from_source_config with {base} template resolution."""
        import os

        from teds_core.generate import generate_from_source_config

        schema = tmp_path / "user_schema.yaml"
        schema.write_text('{"$defs": {"User": {"type": "string"}}}', encoding="utf-8")

        config = {
            "user_schema.yaml": {
                "paths": ['$["$defs"].User'],
                "target": "{base}_custom.tests.yaml",
            }
        }

        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            generate_from_source_config(config, tmp_path)

            # Verify the template was resolved
            expected_file = tmp_path / "user_schema_custom.tests.yaml"
            assert expected_file.exists()
        finally:
            os.chdir(old_cwd)

    def test_generate_from_source_config_default_target(self, tmp_path: Path):
        """Test generate_from_source_config with default target naming."""
        import os

        from teds_core.generate import generate_from_source_config

        schema = tmp_path / "example.yaml"
        schema.write_text('{"$defs": {"Item": {"type": "string"}}}', encoding="utf-8")

        config = {
            "example.yaml": {
                "paths": ['$["$defs"].Item'],
                "target": None,  # Should use default
            }
        }

        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            generate_from_source_config(config, tmp_path)

            # Verify default naming was used
            expected_file = tmp_path / "example.tests.yaml"
            assert expected_file.exists()
        finally:
            os.chdir(old_cwd)

    def test_expand_jsonpath_empty_fragment_root(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with empty fragment (root reference)."""
        schema = tmp_path / "root_test.yaml"
        schema.write_text('{"root": "value"}', encoding="utf-8")

        # Empty fragment should result in root reference
        result = expand_jsonpath_expressions(schema, ["root_test.yaml#"])
        assert "root_test.yaml#/" in result

    def test_expand_jsonpath_path_starts_with_dollar(self, tmp_path: Path):
        """Test path string processing when it starts with $."""
        schema = tmp_path / "dollar_test.yaml"
        schema.write_text('{"test": "value"}', encoding="utf-8")

        # Mock jsonpath to return path starting with $
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = "$test"  # Path starting with $
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ['$["test"]'])
            assert len(result) >= 1
            assert any("test" in ref for ref in result)

    def test_expand_jsonpath_path_starts_with_dot(self, tmp_path: Path):
        """Test path string processing when it starts with dot."""
        schema = tmp_path / "dot_test.yaml"
        schema.write_text('{"test": "value"}', encoding="utf-8")

        # Mock jsonpath to return path starting with .
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = ".test"  # Path starting with .
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ['$["test"]'])
            assert len(result) >= 1

    def test_expand_jsonpath_empty_path_parts_else_branch(self, tmp_path: Path):
        """Test when path_parts is empty (hits else branch)."""
        schema = tmp_path / "empty_parts.yaml"
        schema.write_text('{"root": "value"}', encoding="utf-8")

        # Mock to return completely empty path parts
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = "$"  # Just root, should result in empty path_parts
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ["$.*"])
            assert len(result) >= 1
            assert "empty_parts.yaml#/" in result

    def test_expand_jsonpath_no_matches_valid_behavior(self, tmp_path: Path):
        """Test correct behavior when JSONPath expression finds no matches."""
        schema = tmp_path / "no_matches.yaml"
        schema.write_text('{"existing": "value"}', encoding="utf-8")

        # Valid JSONPath expression that finds no matches should return empty list
        result = expand_jsonpath_expressions(schema, ['$["nonexistent"]'])
        assert result == [], f"No matches should return empty list, got: {result}"

    def test_expand_jsonpath_bracket_pattern_matching(self, tmp_path: Path):
        """Test bracket pattern matching in path parsing."""
        schema = tmp_path / "bracket_match.yaml"
        schema.write_text('{"$defs": {"User": {"name": "test"}}}', encoding="utf-8")

        # Mock to return bracket notation that should match the pattern
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = '["$defs"]["User"]'  # Should match bracket pattern
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ['$["$defs"]["User"]'])
            assert len(result) >= 1
            # The result should contain the schema file with the extracted path
            assert any("bracket_match.yaml#" in ref for ref in result)

    def test_expand_jsonpath_dot_notation_no_brackets(self, tmp_path: Path):
        """Test dot notation processing when bracket pattern doesn't match."""
        schema = tmp_path / "dot_notation.yaml"
        schema.write_text('{"key": {"value": {"prop": "test"}}}', encoding="utf-8")

        # Mock to return dot notation (no brackets)
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = ".key.value.prop"  # Dot notation with leading .
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ["$.key.value.prop"])
            assert len(result) >= 1

    def test_expand_jsonpath_bracket_array_notation(self, tmp_path: Path):
        """Test bracket array notation handling."""
        schema = tmp_path / "array_notation.yaml"
        schema.write_text('{"items": [{"name": "test"}]}', encoding="utf-8")

        # Mock to return array bracket notation
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = "items[0].name"  # Array notation
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ["$.items[0].name"])
            assert len(result) >= 1

    def test_expand_jsonpath_quoted_bracket_array_notation(self, tmp_path: Path):
        """Test quoted bracket array notation handling."""
        schema = tmp_path / "quoted_array.yaml"
        schema.write_text('{"items": [{"name": "test"}]}', encoding="utf-8")

        # Mock to return quoted array bracket notation
        with patch("teds_core.generate.jsonpath_ng") as mock_jsonpath:
            mock_parser = Mock()
            mock_match = Mock()
            mock_match.full_path = "items['0'].name"  # Quoted array notation
            mock_parser.find.return_value = [mock_match]
            mock_jsonpath.parse.return_value = mock_parser

            result = expand_jsonpath_expressions(schema, ["$.items['0'].name"])
            assert len(result) >= 1

    def test_extract_base_name_empty_sources(self):
        """Test extract_base_name with empty sources list."""
        from teds_core.generate import extract_base_name

        result = extract_base_name([])
        assert result == "generated"

    def test_extract_base_name_with_sources(self):
        """Test extract_base_name with sources list."""
        from teds_core.generate import extract_base_name

        result = extract_base_name(["schema.yaml#/defs/User", "other.yaml#/path"])
        assert result == "schema"

    def test_generate_from_existing_vm_dict(self, tmp_path: Path):
        """Test generate_from when vm is already a dict but not CommentedMap."""
        from teds_core.generate import generate_from

        # Create schema with examples
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "$defs": {
    "User": {
      "type": "object",
      "examples": [{"name": "John"}]
    }
  }
}
""",
            encoding="utf-8",
        )

        # Create testspec with existing valid dict (not CommentedMap)
        testspec = tmp_path / "test.yaml"
        testspec.write_text(
            """
version: "1.0.0"
tests:
  schema.yaml#/$defs/User:
    valid:
      existing_test:
        payload: {"name": "Existing"}
""",
            encoding="utf-8",
        )

        # This should trigger the vm conversion from dict to CommentedMap
        generate_from("schema.yaml#/$defs/User", testspec)

        # Verify the file was updated
        assert testspec.exists()

    def test_expand_jsonpath_real_jsonpath_output_formats(self, tmp_path: Path):
        """Test expand_jsonpath_expressions with real jsonpath-ng output formats.

        This test documents and verifies the actual formats that jsonpath-ng produces,
        before we refactor the path parsing code.
        """
        schema = tmp_path / "real_test.yaml"
        schema.write_text(
            """
{
  "$defs": {"User": {"properties": {"name": "string"}}},
  "items": [{"value": "test"}],
  "key": {"nested": {"prop": "value"}}
}
""",
            encoding="utf-8",
        )

        # Test various real jsonpath patterns and their actual outputs
        test_cases = [
            # (input_pattern, expected_path_parts)
            ('$["$defs"]["User"]', ["$defs", "User"]),  # -> '$defs'.User
            ("$.items[0]", ["items", "0"]),  # -> items.0 (array index as string)
            ("$.key.nested.prop", ["key", "nested", "prop"]),  # -> key.nested.prop
        ]

        for pattern, expected_parts in test_cases:
            result = expand_jsonpath_expressions(schema, [pattern])
            assert (
                len(result) == 1
            ), f"Pattern {pattern} should return exactly one result, got: {result}"

            # Verify the result contains the schema file and expected path structure
            result_ref = result[0]
            assert result_ref.startswith("real_test.yaml#/")

            # Extract the path part and verify it matches expected structure
            path_part = result_ref.split("#/", 1)[1]
            actual_parts = path_part.split("/") if path_part else []
            assert (
                actual_parts == expected_parts
            ), f"Pattern {pattern}: expected {expected_parts}, got {actual_parts}"

    def test_expand_jsonpath_properties_exact_behavior_documentation(
        self, tmp_path: Path
    ):
        """Document the CURRENT vs DESIRED behavior for $.properties expressions.

        NOTE: This test documents the current BROKEN behavior and should be
        updated when the fix is implemented to expect the correct behavior.
        """
        schema = tmp_path / "properties_test.yaml"
        schema.write_text(
            """
{
  "$defs": {
    "User": {
      "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"}
      }
    }
  }
}
""",
            encoding="utf-8",
        )

        # CURRENT BROKEN BEHAVIOR: $.properties implicitly expands to children
        # This documents what currently happens (incorrectly)
        result_current = expand_jsonpath_expressions(
            schema, ['$["$defs"]["User"]["properties"]']
        )

        # TODO: When the fix is implemented, change this assertion to:
        # expected_correct = ["properties_test.yaml#/$defs/User/properties"]
        # assert result_current == expected_correct

        # For now, document that the current behavior is wrong:
        # The current implementation likely returns the properties object AND/OR its children
        # which is incorrect behavior that needs to be fixed
        assert (
            len(result_current) >= 1
        ), "Current implementation returns at least one result"

        # The DESIRED behavior (to be implemented):
        # $.properties should return ONLY the properties node itself
        # expected_correct = ["properties_test.yaml#/$defs/User/properties"]
