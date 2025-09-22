"""BDD tests for template integer payload handling."""

import os
import tempfile
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/template_integer_handling.feature")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_context():
    """Shared context for BDD tests."""
    return {}


@given("I have a test spec with integer payloads")
def test_spec_with_integers(temp_dir, test_context):
    """Create a test spec that includes integer payloads that trigger the truncate error."""
    # Create a schema with simple structure
    schema_content = """
components:
  schemas:
    NumberTest:
      type: object
      properties:
        value:
          type: integer
          minimum: 1
      required: [value]
      additionalProperties: false
"""

    # Create test spec with integer payloads that will trigger the error
    testspec_content = """
version: "1.0.0"
tests:
  schema.yaml#/components/schemas/NumberTest:
    valid:
      positive_integer:
        payload: 42
        description: "Simple integer payload"
      large_integer:
        payload: 999999
        description: "Large integer that exceeds truncate length"
    invalid:
      zero_value:
        payload: 0
        description: "Zero should be invalid due to minimum constraint"
      negative_value:
        payload: -1
        description: "Negative should be invalid"
"""

    schema_path = temp_dir / "schema.yaml"
    testspec_path = temp_dir / "testspec.yaml"

    schema_path.write_text(schema_content.strip())
    testspec_path.write_text(testspec_content.strip())

    test_context["schema_path"] = schema_path
    test_context["testspec_path"] = testspec_path
    test_context["temp_dir"] = temp_dir


@given("I have a test spec with mixed payload types including integers")
def test_spec_with_mixed_types(temp_dir, test_context):
    """Create a test spec with mixed payload types including integers."""
    # Create a schema that accepts various types
    schema_content = """
components:
  schemas:
    MixedTest:
      oneOf:
        - type: integer
          minimum: 1
        - type: string
          minLength: 1
        - type: object
          properties:
            id:
              type: integer
"""

    # Create test spec with mixed payload types
    testspec_content = """
version: "1.0.0"
tests:
  schema.yaml#/components/schemas/MixedTest:
    valid:
      integer_payload:
        payload: 42
        description: "Integer payload"
      string_payload:
        payload: "test string"
        description: "String payload"
      object_payload:
        payload: {"id": 123}
        description: "Object payload with integer property"
    invalid:
      zero_integer:
        payload: 0
        description: "Invalid integer"
      empty_string:
        payload: ""
        description: "Invalid string"
"""

    schema_path = temp_dir / "schema.yaml"
    testspec_path = temp_dir / "testspec.yaml"

    schema_path.write_text(schema_content.strip())
    testspec_path.write_text(testspec_content.strip())

    test_context["schema_path"] = schema_path
    test_context["testspec_path"] = testspec_path
    test_context["temp_dir"] = temp_dir


@when("I generate a comprehensive AsciiDoc report")
def generate_comprehensive_report(test_context):
    """Generate a comprehensive AsciiDoc report using the CLI."""
    import subprocess

    testspec_path = test_context["testspec_path"]
    temp_dir = test_context["temp_dir"]
    # Report will be named based on testspec filename: testspec.report.adoc
    report_path = temp_dir / "testspec.report.adoc"

    # Change to the testspec directory so relative schema paths work
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        # Use the main script path from the project root
        teds_script = Path(__file__).resolve().parents[2] / "teds.py"

        result = subprocess.run(
            [
                "python",
                str(teds_script),
                "verify",
                "--output-level",
                "all",
                "--report",
                "comprehensive.adoc",
                str(testspec_path.name),  # Use relative path
            ],
            capture_output=True,
            text=True,
            cwd=temp_dir,
        )

        test_context["cli_result"] = result
        test_context["report_path"] = report_path

    finally:
        os.chdir(original_cwd)


@then("the report should be generated successfully")
def report_generated_successfully(test_context):
    """Verify the report was generated without errors."""
    result = test_context["cli_result"]

    # The CLI should not fail with hard errors (return code 2)
    assert result.returncode != 2, f"CLI failed with hard error: {result.stderr}"

    # Check that no integer type error occurred
    assert "object of type 'int' has no len()" not in result.stderr
    assert "TypeError" not in result.stderr


@then("the report should contain formatted integer values")
def report_contains_integer_values(test_context):
    """Verify the report contains properly formatted integer values."""
    report_path = test_context["report_path"]

    # The report should have been created
    assert report_path.exists(), "Report file was not created"

    # Read the report content
    report_content = report_path.read_text()

    # Should contain our integer payloads properly formatted
    assert "42" in report_content
    assert "999999" in report_content


@then("the report should handle all payload types correctly")
def report_handles_all_types(test_context):
    """Verify the report handles mixed payload types correctly."""
    report_path = test_context["report_path"]

    assert report_path.exists(), "Report file was not created"

    report_content = report_path.read_text()

    # Should contain all our different payload types
    assert "42" in report_content  # integer
    assert "test string" in report_content  # string
    # YAML formatted object (multiline format)
    assert "id: 123" in report_content  # object with YAML formatting


@then("no \"object of type 'int' has no len()\" error should occur")
def no_integer_type_error(test_context):
    """Verify no integer type error occurred."""
    result = test_context["cli_result"]

    # Specifically check for the truncate error
    assert "object of type 'int' has no len()" not in result.stderr
    assert "AttributeError" not in result.stderr
