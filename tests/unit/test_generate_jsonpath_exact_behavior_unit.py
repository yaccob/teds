"""Tests for exact JSONPath behavior - no implicit wildcard expansion.

These tests define the desired behavior where JSONPath expressions like
$.properties should address exactly the properties node itself, NOT its children.

NOTE: These tests are expected to FAIL initially until the correct implementation
is in place. They define the target behavior, not the current broken behavior.
"""

from __future__ import annotations

from pathlib import Path

from teds_core.generate import expand_jsonpath_expressions


class TestJsonPathExactBehavior:
    """Test suite for exact JSONPath behavior without implicit wildcards."""

    def test_properties_node_exact_addressing(self, tmp_path: Path):
        """$.properties should address only the properties node itself, not its children."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "$defs": {
    "User": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "age": {"type": "integer", "minimum": 0}
      }
    }
  }
}
""",
            encoding="utf-8",
        )

        # $.properties should return exactly ONE result: the properties object itself
        result = expand_jsonpath_expressions(
            schema, ['$["$defs"]["User"]["properties"]']
        )

        # Expected: exactly one reference to the properties node
        expected = ["schema.yaml#/$defs/User/properties"]
        assert (
            result == expected
        ), f"Expected exactly one properties node reference, got: {result}"

    def test_properties_vs_properties_wildcard_distinction(self, tmp_path: Path):
        """Clear distinction between $.properties and $.properties.* behavior."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "User": {
    "properties": {
      "name": {"type": "string"},
      "email": {"type": "string"}
    }
  }
}
""",
            encoding="utf-8",
        )

        # Without wildcard: should return only the properties object
        result_exact = expand_jsonpath_expressions(schema, ['$["User"]["properties"]'])
        expected_exact = ["schema.yaml#/User/properties"]
        assert (
            result_exact == expected_exact
        ), f"$.properties should return properties node only, got: {result_exact}"

        # With explicit wildcard: should return all children of properties
        result_wildcard = expand_jsonpath_expressions(
            schema, ['$["User"]["properties"].*']
        )
        expected_wildcard = [
            "schema.yaml#/User/properties/name",
            "schema.yaml#/User/properties/email",
        ]
        # Note: order might vary, so compare as sets
        assert set(result_wildcard) == set(
            expected_wildcard
        ), f"$.properties.* should return property children, got: {result_wildcard}"

    def test_multiple_properties_nodes_exact_addressing(self, tmp_path: Path):
        """When multiple properties nodes exist, $.properties should find all of them exactly."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "$defs": {
    "User": {
      "properties": {
        "name": {"type": "string"}
      }
    },
    "Product": {
      "properties": {
        "title": {"type": "string"},
        "price": {"type": "number"}
      }
    }
  }
}
""",
            encoding="utf-8",
        )

        # This should find both properties nodes, but not their children
        result = expand_jsonpath_expressions(schema, ['$["$defs"].*.properties'])
        expected = [
            "schema.yaml#/$defs/User/properties",
            "schema.yaml#/$defs/Product/properties",
        ]
        # Order might vary, compare as sets
        assert set(result) == set(
            expected
        ), f"Should find both properties nodes exactly, got: {result}"

    def test_single_property_exact_addressing(self, tmp_path: Path):
        """Addressing a single property by name should return exactly that property."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "User": {
    "properties": {
      "name": {"type": "string", "description": "User's name"},
      "email": {"type": "string", "format": "email"}
    }
  }
}
""",
            encoding="utf-8",
        )

        # Address exactly the 'name' property
        result = expand_jsonpath_expressions(
            schema, ['$["User"]["properties"]["name"]']
        )
        expected = ["schema.yaml#/User/properties/name"]
        assert (
            result == expected
        ), f"Should return exactly the name property, got: {result}"

    def test_root_level_properties_exact_addressing(self, tmp_path: Path):
        """Root-level properties node should be addressed exactly."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "type": "object",
  "properties": {
    "username": {"type": "string"},
    "password": {"type": "string"}
  }
}
""",
            encoding="utf-8",
        )

        # Address the root-level properties object
        result = expand_jsonpath_expressions(schema, ['$["properties"]'])
        expected = ["schema.yaml#/properties"]
        assert (
            result == expected
        ), f"Should return exactly the root properties node, got: {result}"

    def test_nested_object_exact_addressing(self, tmp_path: Path):
        """Nested objects should be addressed exactly without expanding children."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "User": {
    "properties": {
      "address": {
        "type": "object",
        "properties": {
          "street": {"type": "string"},
          "city": {"type": "string"}
        }
      }
    }
  }
}
""",
            encoding="utf-8",
        )

        # Address the nested address object properties
        result = expand_jsonpath_expressions(
            schema, ['$["User"]["properties"]["address"]["properties"]']
        )
        expected = ["schema.yaml#/User/properties/address/properties"]
        assert (
            result == expected
        ), f"Should return exactly the nested properties node, got: {result}"

    def test_array_index_exact_addressing(self, tmp_path: Path):
        """Array indices should be addressed exactly."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "examples": [
    {"name": "Alice"},
    {"name": "Bob"}
  ]
}
""",
            encoding="utf-8",
        )

        # Address exactly the first example
        result = expand_jsonpath_expressions(schema, ['$["examples"][0]'])
        expected = ["schema.yaml#/examples/0"]
        assert (
            result == expected
        ), f"Should return exactly the first array element, got: {result}"

    def test_dot_notation_exact_addressing(self, tmp_path: Path):
        """Dot notation should work exactly like bracket notation."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "User": {
    "properties": {
      "name": {"type": "string"}
    }
  }
}
""",
            encoding="utf-8",
        )

        # Both notations should produce the same result
        result_bracket = expand_jsonpath_expressions(
            schema, ['$["User"]["properties"]']
        )
        result_dot = expand_jsonpath_expressions(schema, ["$.User.properties"])

        expected = ["schema.yaml#/User/properties"]
        assert result_bracket == expected, f"Bracket notation failed: {result_bracket}"
        assert result_dot == expected, f"Dot notation failed: {result_dot}"
        assert (
            result_bracket == result_dot
        ), "Bracket and dot notation should produce identical results"

    def test_no_implicit_iteration_behavior(self, tmp_path: Path):
        """JSONPath should not implicitly iterate over object properties."""
        schema = tmp_path / "schema.yaml"
        schema.write_text(
            """
{
  "definitions": {
    "StringType": {"type": "string"},
    "NumberType": {"type": "number"},
    "BooleanType": {"type": "boolean"}
  }
}
""",
            encoding="utf-8",
        )

        # $.definitions should return the definitions object, not iterate over its contents
        result = expand_jsonpath_expressions(schema, ["$.definitions"])
        expected = ["schema.yaml#/definitions"]
        assert (
            result == expected
        ), f"Should return definitions object exactly, got: {result}"

        # Only explicit wildcard should iterate
        result_wildcard = expand_jsonpath_expressions(schema, ["$.definitions.*"])
        expected_wildcard = [
            "schema.yaml#/definitions/StringType",
            "schema.yaml#/definitions/NumberType",
            "schema.yaml#/definitions/BooleanType",
        ]
        assert set(result_wildcard) == set(
            expected_wildcard
        ), f"Explicit wildcard should iterate, got: {result_wildcard}"

    def test_path_resolution_with_subdirectory_schema(self, tmp_path: Path):
        """Test path resolution with schemas in subdirectories.

        When schemas are in subdirectories, generated references should use
        relative paths from the schema file location.
        """
        # Create subdirectory with schema
        sub = tmp_path / "schemas"
        sub.mkdir()
        schema = sub / "api.yaml"
        schema.write_text(
            """
components:
  schemas:
    User:
      type: object
      properties:
        name:
          type: string
          examples: ["John"]
        age:
          type: integer
          examples: [25]
""",
            encoding="utf-8",
        )

        # Test JSONPath expressions with schema in subdirectory
        result = expand_jsonpath_expressions(
            schema,
            [
                "$.components.schemas.User.properties",
                "$.components.schemas.User.properties.name",
            ],
        )

        # Should generate relative paths from schema file location
        expected = [
            "api.yaml#/components/schemas/User/properties",
            "api.yaml#/components/schemas/User/properties/name",
        ]

        assert set(result) == set(
            expected
        ), f"Expected relative paths {expected}, got: {result}"
