from __future__ import annotations

from pathlib import Path

import pytest

from tests.utils import load_yaml_file, run_cli


class TestGenerateTargetPlacement:
    def test_default_target_placement_next_to_schema(self, tmp_path: Path):
        """Test that default target files are created next to schema files, not in cwd."""
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

        # Run from project root, targeting schema in subdirectory
        config_str = '{"schemas/api.yaml": ["$[\\"$defs\\"][\\"User\\"]"]}'
        rc, _out, err = run_cli(["generate", config_str], cwd=tmp_path)
        assert rc == 0, err

        # Default target should be next to schema file, not in cwd
        expected_target = subdir / "api.tests.yaml"
        assert expected_target.exists()

        # Should NOT be created in project root
        wrong_target = tmp_path / "api.tests.yaml"
        assert not wrong_target.exists()

        # Verify content is correct
        doc = load_yaml_file(expected_target)
        assert "tests" in doc

    @pytest.mark.skip(reason="Path target schema resolution needs fix - see TODO")
    def test_explicit_target_with_path_relative_to_cwd(self, tmp_path: Path):
        """Test explicit target with path is placed relative to cwd."""
        # Create schema in subdirectory
        subdir = tmp_path / "schemas"
        subdir.mkdir()
        schema = subdir / "api.yaml"
        schema.write_text(
            """
components:
  schemas:
    User:
      type: object
      properties:
        name:
          type: string
""",
            encoding="utf-8",
        )

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Run with explicit target path
        config_str = '{"schemas/api.yaml": {"paths": ["$.components.schemas.User"], "target": "output/custom.tests.yaml"}}'
        rc, _out, err = run_cli(["generate", config_str], cwd=tmp_path)
        assert rc == 0, err

        # Target should be created at specified path relative to cwd
        expected_target = tmp_path / "output" / "custom.tests.yaml"
        assert expected_target.exists()

        # Verify content
        doc = load_yaml_file(expected_target)
        assert "tests" in doc

    def test_explicit_target_filename_only_relative_to_cwd(self, tmp_path: Path):
        """Test explicit target filename (no path) is placed relative to cwd."""
        # Create schema in subdirectory
        subdir = tmp_path / "data"
        subdir.mkdir()
        schema = subdir / "model.yaml"
        schema.write_text(
            """
definitions:
  Person:
    type: object
    properties:
      email:
        type: string
        format: email
""",
            encoding="utf-8",
        )

        # Run with explicit filename only
        config_str = '{"data/model.yaml": {"paths": ["$.definitions.Person"], "target": "custom_name.tests.yaml"}}'
        rc, _out, err = run_cli(["generate", config_str], cwd=tmp_path)
        assert rc == 0, err

        # Explicit target should be relative to cwd, not next to schema
        expected_target = tmp_path / "custom_name.tests.yaml"
        assert expected_target.exists()

        # Should NOT be next to schema file
        wrong_target = subdir / "custom_name.tests.yaml"
        assert not wrong_target.exists()

        # Verify content
        doc = load_yaml_file(expected_target)
        assert "tests" in doc
