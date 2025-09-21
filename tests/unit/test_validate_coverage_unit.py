"""Additional tests to improve validate.py coverage for edge cases and error paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from teds_core.validate import validate_doc, validate_file


class TestValidateCoverageEdgeCases:
    """Test suite to improve coverage for validate.py edge cases."""

    def test_validate_doc_empty_tests_section(self, tmp_path: Path):
        """Test validate_doc when tests section is empty."""
        doc = {"version": "1.0.0", "tests": {}}  # Empty tests dict

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_file_spec_validation_error(self, tmp_path: Path):
        """Test validate_file when testspec validation fails."""
        # Create invalid testspec (missing version)
        testspec = tmp_path / "invalid.yaml"
        testspec.write_text(
            """
tests:
  some_ref:
    valid: {}
""",
            encoding="utf-8",
        )

        # This should fail spec validation (missing version)
        with patch("sys.stderr"):
            rc = validate_file(testspec, output_level="all", in_place=False)
            assert rc == 2

    def test_validate_doc_builder_failure(self, tmp_path: Path):
        """Test validate_doc when validator builder fails."""
        # Create doc with non-existent schema reference
        doc = {
            "version": "1.0.0",
            "tests": {
                "nonexistent.yaml#": {"valid": {"test_case": {"payload": "test"}}}
            },
        }

        with patch("sys.stderr"):
            output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
            assert rc == 2  # Hard failure due to schema resolution error

    def test_validate_doc_with_parse_payload_flag(self, tmp_path: Path):
        """Test validate_doc with parse_payload: true."""
        # Create simple schema
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: integer", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "valid": {
                        "number_test": {
                            "payload": "123",  # String that should parse to number
                            "parse_payload": True,
                        }
                    }
                }
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_doc_with_description_override(self, tmp_path: Path):
        """Test validate_doc with explicit description."""
        # Create simple schema
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "valid": {
                        "test_case": {
                            "payload": "test string",
                            "description": "Custom description",
                        }
                    }
                }
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_doc_mismatched_expectations(self, tmp_path: Path):
        """Test validate_doc for mismatched expectations (invalid success, valid error)."""
        # Create schema that accepts only strings
        schema = tmp_path / "string_only.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "invalid": {
                        "should_fail_but_passes": {
                            "payload": "this is valid string"  # Valid but in invalid section
                        }
                    },
                    "valid": {
                        "should_pass_but_fails": {
                            "payload": 123  # Invalid but in valid section
                        }
                    },
                }
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 1  # Should have validation errors

    def test_validate_doc_with_warnings(self, tmp_path: Path):
        """Test validate_doc when items contain user warnings."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "valid": {
                        "test_case": {
                            "payload": "valid string",
                            "warnings": ["user warning message"],
                        }
                    }
                }
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_doc_output_level_filtering(self, tmp_path: Path):
        """Test validate_doc with different output levels."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "valid": {"passing_case": {"payload": "valid string"}}
                }
            },
        }

        # Test error level filtering
        output, rc = validate_doc(doc, tmp_path, output_level="error", in_place=False)
        assert rc == 0

    def test_validate_doc_invalid_items_type(self, tmp_path: Path):
        """Test validate_doc when test items is not a dict."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {f"{schema.name}#": "not a dict"},  # Invalid items type
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0  # Should handle gracefully

    def test_validate_doc_generated_warnings(self, tmp_path: Path):
        """Test validate_doc with generated warnings in warnings list."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "valid": {
                        "test_with_generated_warning": {
                            "payload": "valid string",
                            "warnings": [
                                "user warning",
                                {
                                    "generated": "tool warning",
                                    "message": "auto-generated",
                                },
                            ],
                        }
                    }
                }
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_doc_null_payload(self, tmp_path: Path):
        """Test validate_doc with null payload."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: [string, null]", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {"valid": {"null_payload_test": {"payload": None}}}
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_doc_from_examples_skip(self, tmp_path: Path):
        """Test validate_doc skipping from_examples cases."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        doc = {
            "version": "1.0.0",
            "tests": {
                f"{schema.name}#": {
                    "valid": {
                        "example_case": {
                            "payload": "example value",
                            "from_examples": True,
                        },
                        "normal_case": {"payload": "normal value"},
                    }
                }
            },
        }

        output, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
        assert rc == 0

    def test_validate_file_invalid_spec_version(self, tmp_path: Path):
        """Test validate_file with invalid spec version."""
        testspec = tmp_path / "invalid_version.yaml"
        testspec.write_text(
            """
version: "invalid.version.format"
tests:
  some_ref:
    valid: {}
""",
            encoding="utf-8",
        )

        with patch("sys.stderr"):
            rc = validate_file(testspec, output_level="all", in_place=False)
            assert rc == 2

    def test_validate_file_unsupported_spec_version(self, tmp_path: Path):
        """Test validate_file with unsupported spec version."""
        testspec = tmp_path / "unsupported_version.yaml"
        testspec.write_text(
            """
version: "99.0.0"
tests:
  some_ref:
    valid: {}
""",
            encoding="utf-8",
        )

        with patch("sys.stderr"):
            rc = validate_file(testspec, output_level="all", in_place=False)
            assert rc == 2

    def test_validate_file_stdout_output(self, tmp_path: Path):
        """Test validate_file outputting to stdout when not in_place."""
        schema = tmp_path / "schema.yaml"
        schema.write_text("type: string", encoding="utf-8")

        testspec = tmp_path / "test.yaml"
        testspec.write_text(
            f"""
version: "1.0.0"
tests:
  {schema.name}#:
    valid:
      test_case:
        payload: "valid string"
""",
            encoding="utf-8",
        )

        with patch("sys.stdout"):
            rc = validate_file(testspec, output_level="all", in_place=False)
            assert rc == 0
