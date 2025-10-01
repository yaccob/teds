"""Unit tests for schema path resolution in generate_from_source_config()."""

from __future__ import annotations

from pathlib import Path

import pytest

from teds_core.errors import TedsError
from teds_core.generate import generate_from_source_config
from tests.utils import load_yaml_file


class TestSchemaPathResolution:
    """Test that schema paths are always resolved relative to base_dir (CWD), not target directory."""

    def test_schema_path_resolved_relative_to_cwd_not_target_dir(self, tmp_path: Path):
        """Test that schema paths are resolved relative to CWD, even with explicit targets in subdirectories."""
        # Setup directory structure:
        # tmp_path/
        #   ├── schema.yaml (schema file)
        #   └── subdir/
        #       └── output.yaml (target file)

        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
$defs:
  User:
    type: object
    properties:
      name:
        type: string
""",
            encoding="utf-8",
        )

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Configuration with explicit target in subdirectory
        config = {
            "schema.yaml": {"paths": ["$['$defs'].*"], "target": "subdir/output.yaml"}
        }

        # Generate from config - should resolve schema.yaml relative to tmp_path (CWD)
        # This should succeed because schema.yaml exists at tmp_path/schema.yaml
        generate_from_source_config(config, tmp_path)

        # Verify output file was created in the correct target location
        output_file = subdir / "output.yaml"
        assert output_file.exists()

        # Verify the reference in the test file is correct (relative to test file location)
        doc = load_yaml_file(output_file)
        assert "tests" in doc
        test_keys = list(doc["tests"].keys())
        assert len(test_keys) > 0

        # The reference should be relative to the test file location (../schema.yaml)
        expected_ref = "../schema.yaml#/$defs/User"
        assert (
            expected_ref in test_keys
        ), f"Expected reference '{expected_ref}' not found in test keys: {test_keys}"

    def test_schema_path_resolution_fails_when_schema_not_found_relative_to_cwd(
        self, tmp_path: Path
    ):
        """Test that schema path resolution fails when schema doesn't exist relative to CWD."""
        # Setup directory structure that would pass with old logic but fail with new logic:
        # tmp_path/
        #   └── subdir/
        #       ├── schema.yaml (schema file - old logic would find this)
        #       └── output.yaml (target file)
        #
        # Note: No schema.yaml at tmp_path/schema.yaml (new logic should fail)

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Create schema file in subdir (old logic would find this, new logic shouldn't)
        schema_file = subdir / "schema.yaml"
        schema_file.write_text(
            """
$defs:
  User:
    type: object
    properties:
      name:
        type: string
""",
            encoding="utf-8",
        )

        # Configuration with target in same subdirectory as schema
        config = {
            "schema.yaml": {  # This references schema.yaml but it doesn't exist at CWD level
                "paths": ["$['$defs'].*"],
                "target": "subdir/output.yaml",
            }
        }

        # This should fail because schema.yaml doesn't exist at tmp_path/schema.yaml
        # With the new logic, schema paths are always resolved relative to CWD
        with pytest.raises(TedsError, match="Failed to load schema"):
            generate_from_source_config(config, tmp_path)

    def test_schema_path_with_relative_reference_in_config(self, tmp_path: Path):
        """Test schema path resolution when config contains relative paths."""
        # Setup directory structure:
        # tmp_path/
        #   ├── models/
        #   │   └── user.yaml (schema file)
        #   └── tests/
        #       └── user_tests.yaml (target file)

        models_dir = tmp_path / "models"
        models_dir.mkdir()
        schema_file = models_dir / "user.yaml"
        schema_file.write_text(
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

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        # Configuration with relative schema path and target
        config = {
            "models/user.yaml": {
                "paths": ["$['$defs'].*"],
                "target": "tests/user_tests.yaml",
            }
        }

        # Generate from config - should resolve models/user.yaml relative to tmp_path (CWD)
        generate_from_source_config(config, tmp_path)

        # Verify output file was created
        output_file = tests_dir / "user_tests.yaml"
        assert output_file.exists()

        # Verify the reference in the test file
        doc = load_yaml_file(output_file)
        test_keys = list(doc["tests"].keys())

        # The reference should be relative to the test file location (../models/user.yaml)
        expected_ref = "../models/user.yaml#/$defs/User"
        assert (
            expected_ref in test_keys
        ), f"Expected reference '{expected_ref}' not found in test keys: {test_keys}"
