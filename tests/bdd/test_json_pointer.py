"""BDD tests for JSON Pointer CLI generation using pytest-bdd."""

import os
import tempfile
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from teds_core.cli import main as cli_main
from teds_core.yamlio import yaml_loader

# Load all scenarios from the feature file
scenarios("features/json_pointer_tests.feature")


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        original_cwd = Path.cwd()
        os.chdir(workspace)
        try:
            yield workspace
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def schema_files(temp_workspace):
    """Store created schema files for reference."""
    return {}


@pytest.fixture
def test_files(temp_workspace):
    """Store generated test files for verification."""
    return {}


@given("I have a working directory")
def working_directory_setup(temp_workspace):
    """Set up working directory."""
    pass


@given(parsers.parse('I have a subdirectory "{dirname}"'))
def create_subdirectory(temp_workspace, dirname):
    """Create a subdirectory."""
    subdir = temp_workspace / dirname
    subdir.mkdir(parents=True, exist_ok=True)


@given(parsers.parse('I have a schema file "{filename}" with content:'))
def create_schema_file(temp_workspace, schema_files, filename, docstring):
    """Create a schema file with given content."""
    content = docstring
    schema_path = temp_workspace / filename
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove yaml language marker if present
    if content.strip().startswith("yaml"):
        content = "\n".join(content.strip().split("\n")[1:])

    schema_path.write_text(content.strip(), encoding="utf-8")
    schema_files[filename] = schema_path
    return schema_path


@given(
    parsers.parse('I have an existing test file "{filename}" with content:'),
    target_fixture="existing_test",
)
def create_existing_test_file(temp_workspace, test_files, filename):
    """Create an existing test file with given content."""

    def _create_with_content(content):
        test_path = temp_workspace / filename
        test_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove yaml language marker if present
        if content.strip().startswith("yaml"):
            content = "\n".join(content.strip().split("\n")[1:])

        test_path.write_text(content.strip(), encoding="utf-8")
        test_files[filename] = test_path
        return test_path

    return _create_with_content


@when(parsers.parse("I run the generate command: `{command}`"))
def run_generate_command(temp_workspace, command):
    """Execute the generate command."""
    # Extract command arguments
    # Remove 'teds generate ' prefix
    args_str = command.replace("teds generate ", "").strip()

    # Handle quoted arguments and --output flags
    import shlex

    args = shlex.split(args_str)

    # Prepare sys.argv for CLI
    import sys

    original_argv = sys.argv[:]
    exit_code = None
    try:
        sys.argv = ["teds", "generate", *args]
        cli_main()
        exit_code = 0
    except SystemExit as e:
        exit_code = e.code
    finally:
        sys.argv = original_argv

    # CRITICAL: The command must succeed for the BDD test to be valid
    # If exit code is not 0, the command failed and we should fail the test
    if exit_code != 0:
        raise AssertionError(
            f"Generate command failed with exit code {exit_code}: {command}"
        )


@then(parsers.parse('a test file "{filename}" should be created with content:'))
def verify_test_file_created(temp_workspace, test_files, filename, docstring):
    """Verify that a test file was created with expected content."""
    expected_content = docstring
    test_path = temp_workspace / filename

    # Debug: Show what files exist before assertion
    print(f"\n=== DEBUG: Looking for {filename} in {temp_workspace} ===")
    print("All files in workspace:")
    generated_test_files = []
    for p in temp_workspace.rglob("*"):
        if p.is_file():
            print(f"  {p}")
            if p.name.endswith(".tests.yaml"):
                generated_test_files.append(p)
    print(f"Expected file path: {test_path}")
    print(f"File exists: {test_path.exists()}")

    # Check if a different test file was generated and show its content
    if generated_test_files and not test_path.exists():
        actual_generated_file = generated_test_files[0]
        print(f"\n=== ACTUAL GENERATED FILE: {actual_generated_file} ===")
        actual_content = actual_generated_file.read_text(encoding="utf-8")
        print(actual_content)
        print("=== END CONTENT ===")

        # CRITICAL: Check for absolute paths in the generated content
        print("DEBUG: Checking for absolute paths in generated content")
        if "/private/" in actual_content or "/var/folders/" in actual_content:
            print("🚨 FOUND ABSOLUTE PATHS!")
        else:
            print("✅ No absolute paths found")

    assert test_path.exists(), f"Test file {filename} was not created"

    # Read actual content
    actual_content = test_path.read_text(encoding="utf-8")

    # Show actual content for debugging
    print(f"\n=== ACTUAL GENERATED CONTENT for {filename} ===")
    print(actual_content)
    print("=== END CONTENT ===")

    # Remove yaml language marker if present
    if expected_content.strip().startswith("yaml"):
        expected_content = "\n".join(expected_content.strip().split("\n")[1:])

    # CRITICAL: Check for absolute paths in schema references - this is what the test should validate!
    # If actual content contains absolute paths, the test should fail
    print("DEBUG: Checking content for absolute paths")
    if ":" in actual_content and ("/" in actual_content):
        import re

        # Look for absolute path patterns in YAML keys (schema references)
        absolute_path_pattern = r'["\']?(/[^:\s]+\.yaml#[^:\s]*)["\']?:'
        absolute_matches = re.findall(absolute_path_pattern, actual_content)
        print(f"DEBUG: Found absolute path matches: {absolute_matches}")
        if absolute_matches:
            raise AssertionError(
                f"Generated test file contains absolute paths in schema references: {absolute_matches}\nExpected relative paths only.\nActual content:\n{actual_content}"
            )

    # Parse both as YAML for comparison
    actual_yaml = yaml_loader.load(actual_content)
    expected_yaml = yaml_loader.load(expected_content.strip())

    assert (
        actual_yaml == expected_yaml
    ), f"Test file content mismatch.\nExpected:\n{expected_content}\nActual:\n{actual_content}"

    # Store for further verification
    test_files[filename] = test_path


@then(
    parsers.parse('the test file "{filename}" should be updated with content:'),
    target_fixture="updated_test_file",
)
def verify_test_file_updated(temp_workspace, test_files, filename):
    """Verify that a test file was updated with expected content."""

    def _verify_with_content(expected_content):
        test_path = temp_workspace / filename
        assert test_path.exists(), f"Test file {filename} was not updated"

        # Read actual content
        actual_content = test_path.read_text(encoding="utf-8")

        # Remove yaml language marker if present
        if expected_content.strip().startswith("yaml"):
            expected_content = "\n".join(expected_content.strip().split("\n")[1:])

        # Parse both as YAML for comparison
        actual_yaml = yaml_loader.load(actual_content)
        expected_yaml = yaml_loader.load(expected_content.strip())

        assert (
            actual_yaml == expected_yaml
        ), f"Test file content mismatch.\nExpected:\n{expected_content}\nActual:\n{actual_content}"

        # Store for further verification
        test_files[filename] = test_path
        return test_path

    return _verify_with_content
