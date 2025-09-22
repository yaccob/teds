from __future__ import annotations

from pathlib import Path

from teds_core.generate import generate_from, generate_from_source_config
from tests.utils import load_yaml_file


class TestGenerateOutputFilename:
    def test_default_output_filename_without_target(self, tmp_path: Path):
        """Test default output filename should be {base}.tests.yaml"""
        schema = tmp_path / "address_list.yaml"
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

        # Generate without explicit target - should use default filename
        generate_from(
            f"{schema.name}#/$defs", schema.parent / "address_list.tests.yaml"
        )

        # Default filename should be {base}.tests.yaml
        expected_file = tmp_path / "address_list.tests.yaml"
        assert expected_file.exists()

        # Verify content is correct
        doc = load_yaml_file(expected_file)
        assert "tests" in doc

    def test_explicit_target_file(self, tmp_path: Path):
        """Test explicit target file specification"""
        schema = tmp_path / "api.yaml"
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

        config = {
            "api.yaml": {
                "paths": ["$.components.schemas.User"],
                "target": "custom_output.tests.yaml",
            }
        }

        generate_from_source_config(config, tmp_path)

        # Should create file with explicit name
        expected_file = tmp_path / "custom_output.tests.yaml"
        assert expected_file.exists()

        # Verify content
        doc = load_yaml_file(expected_file)
        assert "tests" in doc

    def test_target_file_with_base_template(self, tmp_path: Path):
        """Test target file with {base} template substitution"""
        schema = tmp_path / "user_schema.yaml"
        schema.write_text(
            """
$defs:
  Person:
    type: object
    properties:
      email:
        type: string
        format: email
""",
            encoding="utf-8",
        )

        config = {
            "user_schema.yaml": {
                "paths": ['$["$defs"]["Person"]'],
                "target": "{base}_generated.tests.yaml",
            }
        }

        generate_from_source_config(config, tmp_path)

        # Should substitute {base} with schema basename
        expected_file = tmp_path / "user_schema_generated.tests.yaml"
        assert expected_file.exists()

        # Verify content
        doc = load_yaml_file(expected_file)
        assert "tests" in doc
