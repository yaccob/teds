from __future__ import annotations

from pathlib import Path

from tests.utils import load_yaml_file, run_cli


def test_generate_with_relative_schema_in_subdir(tmp_path: Path, monkeypatch):
    # Create nested subdir with a minimal schema
    sub = tmp_path / "sub"
    sub.mkdir()
    schema = sub / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    A:
      type: string
      examples: [x]
""",
        encoding="utf-8",
    )

    # Run from tmp root, pass a relative path into a subdirectory
    rc, _out, err = run_cli(["generate", "sub/schema.yaml#/"], cwd=tmp_path)
    assert rc == 0, err

    # Expect default filename next to the schema
    out_file = sub / "schema.tests.yaml"
    assert out_file.exists()
    doc = load_yaml_file(out_file)
    # Contains group for '#/' and example-derived case
    keys = list((doc.get("tests") or {}).keys())
    assert any("schema.yaml#/" in k for k in keys) or any(
        "schema.yaml#/A" in k for k in keys
    )


def test_generate_source_config_with_subdir_schema(tmp_path: Path, monkeypatch):
    """Test source-centric YAML config with schema in subdirectory.

    This covers the real-world scenario where:
    - Schema files are in subdirectories
    - Generate command is executed from project root
    - Source-centric config references the subdirectory schema
    - Generated paths should be relative to the schema file
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

    # Create source-centric config file in project root
    config = tmp_path / "generate.yaml"
    config.write_text(
        """
schemas/api.yaml:
  paths:
    - "$.components.schemas.User.properties"
    - "$.components.schemas.User.properties.name"
  target: "schemas/api.tests.yaml"
""",
        encoding="utf-8",
    )

    # Run generate from project root with config file
    rc, _out, err = run_cli(["generate", "@generate.yaml"], cwd=tmp_path)
    assert rc == 0, err

    # Check that test file was created in expected location
    test_file = tmp_path / "schemas" / "api.tests.yaml"
    assert test_file.exists()

    # Verify generated content has correct schema references
    doc = load_yaml_file(test_file)
    tests = doc.get("tests", {})

    # Should contain references with proper relative paths
    expected_keys = [
        "api.yaml#/components/schemas/User/properties",
        "api.yaml#/components/schemas/User/properties/name",
    ]

    for expected_key in expected_keys:
        assert (
            expected_key in tests
        ), f"Expected key '{expected_key}' not found in {list(tests.keys())}"
