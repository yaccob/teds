from __future__ import annotations

from pathlib import Path

from teds_core.generate import generate_from
from tests.utils import load_yaml_file


def test_generate_from_function(tmp_path: Path):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    A:
      type: string
      examples: ["x"]
    B:
      type: integer
      minimum: 1
""",
        encoding="utf-8",
    )
    out = tmp_path / "out.tests.yaml"
    generate_from(f"{schema}#/", out)
    assert out.exists()
    doc = load_yaml_file(out)
    assert "tests" in doc and isinstance(doc["tests"], dict)
    # Should contain direct children A and B groups
    keys = list(doc["tests"].keys())
    assert any(str(schema) in k for k in keys)


def test_generate_from_with_relative_reference_in_subdirectory(tmp_path: Path):
    """Test generate_from() with relative schema reference in subdirectory."""
    # Create schema in subdirectory
    subdir = tmp_path / "schemas"
    subdir.mkdir()
    schema = subdir / "api.yaml"
    schema.write_text(
        """
$defs:
  User:
    type: object
    properties:
      name:
        type: string
        examples: ["John"]
""",
        encoding="utf-8",
    )

    # Create testspec file in project root
    testspec = tmp_path / "api.tests.yaml"

    # Should successfully resolve relative reference and generate tests
    generate_from("api.yaml#/$defs/User/properties/name", testspec)

    # Verify testspec was created and contains expected content
    assert testspec.exists()
    doc = load_yaml_file(testspec)
    assert "tests" in doc
    tests = doc["tests"]

    # generate_from() creates tests for children of the referenced node
    expected_tests = [
        "api.yaml#/$defs/User/properties/name/type",
        "api.yaml#/$defs/User/properties/name/examples",
    ]
    for expected_test in expected_tests:
        assert expected_test in tests
