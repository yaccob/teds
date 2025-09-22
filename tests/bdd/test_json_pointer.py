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


@given(
    parsers.parse('I have a schema file "{filename}" with content:'),
    target_fixture="created_schema",
)
def create_schema_file(temp_workspace, schema_files, filename):
    """Create a schema file with given content."""

    def _create_with_content(content):
        schema_path = temp_workspace / filename
        schema_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove yaml language marker if present
        if content.strip().startswith("yaml"):
            content = "\n".join(content.strip().split("\n")[1:])

        schema_path.write_text(content.strip(), encoding="utf-8")
        schema_files[filename] = schema_path
        return schema_path

    return _create_with_content


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
    try:
        sys.argv = ["teds", "generate", *args]
        cli_main()
    except SystemExit:
        # Expected for successful completion
        pass
    finally:
        sys.argv = original_argv


@then(
    parsers.parse('a test file "{filename}" should be created with content:'),
    target_fixture="verified_test_file",
)
def verify_test_file_created(temp_workspace, test_files, filename):
    """Verify that a test file was created with expected content."""

    def _verify_with_content(expected_content):
        test_path = temp_workspace / filename
        assert test_path.exists(), f"Test file {filename} was not created"

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
