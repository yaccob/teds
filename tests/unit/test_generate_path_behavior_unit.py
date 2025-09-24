"""Unit tests for generate path behavior - relative vs absolute paths in generated test files."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from teds_core.cli import main as cli_main
from teds_core.generate import generate_from
from tests.utils import load_yaml_file


def test_generate_from_produces_relative_paths_in_testspec(tmp_path: Path):
    """Test that generate_from() produces relative schema references in generated testspec."""
    # Create schema in subdirectory
    subdir = tmp_path / "models"
    subdir.mkdir()
    schema = subdir / "user.yaml"
    schema.write_text(
        """
$defs:
  User:
    type: object
    properties:
      id:
        type: string
      name:
        type: string
""",
        encoding="utf-8",
    )

    # Create testspec in same subdirectory
    testspec = subdir / "user.tests.yaml"

    # Generate tests for $defs children
    generate_from("user.yaml#/$defs", testspec)

    # Verify testspec was created
    assert testspec.exists()
    doc = load_yaml_file(testspec)
    assert "tests" in doc

    # CRITICAL: Check that schema references in testspec are RELATIVE, not absolute
    tests = doc["tests"]
    schema_refs = list(tests.keys())

    # Should have relative reference to user.yaml, not absolute path
    assert len(schema_refs) == 1
    schema_ref = schema_refs[0]

    # MUST be relative path
    assert (
        schema_ref == "user.yaml#/$defs/User"
    ), f"Expected relative path 'user.yaml#/$defs/User', got '{schema_ref}'"

    # MUST NOT contain absolute path markers
    assert "/private/" not in schema_ref, f"Found absolute path marker in {schema_ref}"
    assert (
        "/var/folders/" not in schema_ref
    ), f"Found absolute path marker in {schema_ref}"
    assert not schema_ref.startswith(
        "/"
    ), f"Schema reference starts with absolute path: {schema_ref}"


def test_generate_from_with_complex_subdirectory_structure(tmp_path: Path):
    """Test relative path generation with complex directory structures."""
    # Create nested directory structure
    api_dir = tmp_path / "api" / "v1" / "schemas"
    api_dir.mkdir(parents=True)

    schema = api_dir / "user.yaml"
    schema.write_text(
        """
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        profile:
          type: object
          properties:
            name:
              type: string
""",
        encoding="utf-8",
    )

    # Generate testspec in same directory
    testspec = api_dir / "user.tests.yaml"
    generate_from("user.yaml#/components/schemas", testspec)

    # Verify relative paths
    assert testspec.exists()
    doc = load_yaml_file(testspec)
    tests = doc["tests"]

    # Should have relative reference, not absolute
    schema_refs = list(tests.keys())
    assert len(schema_refs) == 1
    schema_ref = schema_refs[0]

    # MUST be relative to the testspec location
    assert (
        schema_ref == "user.yaml#/components/schemas/User"
    ), f"Expected relative path, got '{schema_ref}'"
    assert not schema_ref.startswith(
        "/"
    ), f"Schema reference contains absolute path: {schema_ref}"


def test_generate_from_cross_directory_reference_produces_relative_paths(
    tmp_path: Path,
):
    """Test that cross-directory references still produce relative paths."""
    # Schema in one directory
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    schema = schema_dir / "model.yaml"
    schema.write_text(
        """
$defs:
  Item:
    type: object
    properties:
      id:
        type: string
""",
        encoding="utf-8",
    )

    # Testspec in different directory
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    testspec = test_dir / "model.tests.yaml"

    # Generate with relative reference that crosses directories
    # This simulates CLI behavior where we provide relative paths
    generate_from("../schemas/model.yaml#/$defs", testspec)

    assert testspec.exists()
    doc = load_yaml_file(testspec)
    tests = doc["tests"]

    schema_refs = list(tests.keys())
    assert len(schema_refs) == 1
    schema_ref = schema_refs[0]

    # Should preserve the relative path structure used in the reference
    assert (
        schema_ref == "../schemas/model.yaml#/$defs/Item"
    ), f"Expected relative cross-directory path, got '{schema_ref}'"
    assert not schema_ref.startswith(
        "/"
    ), f"Schema reference contains absolute path: {schema_ref}"


def test_cli_generate_command_produces_relative_paths(tmp_path: Path):
    """Test that CLI generate command produces relative paths in generated test files."""
    # Setup: Create schema in subdirectory
    subdir = tmp_path / "models"
    subdir.mkdir()
    schema = subdir / "user.yaml"
    schema.write_text(
        """
$defs:
  User:
    type: object
    properties:
      id:
        type: string
""",
        encoding="utf-8",
    )

    # Change to tmp_path directory (simulate CLI usage)
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        # Execute CLI command: teds generate models/user.yaml#/$defs
        original_argv = sys.argv.copy()
        sys.argv = ["teds", "generate", "models/user.yaml#/$defs"]

        exit_code = None
        try:
            cli_main()
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code
        finally:
            sys.argv = original_argv

        # Should succeed
        assert exit_code == 0, f"CLI command failed with exit code {exit_code}"

        # Check generated file
        testspec = subdir / "user.tests.yaml"
        assert testspec.exists(), f"Expected test file {testspec} was not created"

        # CRITICAL: Verify that schema references are RELATIVE
        doc = load_yaml_file(testspec)
        tests = doc["tests"]
        schema_refs = list(tests.keys())

        assert len(schema_refs) == 1
        schema_ref = schema_refs[0]

        # MUST be relative path, NOT absolute
        assert (
            schema_ref == "user.yaml#/$defs/User"
        ), f"CLI produced absolute path: {schema_ref}"
        assert not schema_ref.startswith(
            "/"
        ), f"Schema reference starts with absolute path: {schema_ref}"
        assert (
            "/private/" not in schema_ref
        ), f"Found absolute path marker in CLI output: {schema_ref}"
        assert (
            "/var/folders/" not in schema_ref
        ), f"Found absolute path marker in CLI output: {schema_ref}"

    finally:
        # Restore original working directory
        os.chdir(original_cwd)
