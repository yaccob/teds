"""BDD tests for essential CLI functionality using pytest-bdd."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from teds_core.yamlio import yaml_loader

# Load all scenarios from the feature file
scenarios("features/cli_essentials.feature")


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


@pytest.fixture
def cli_result():
    """Store CLI command results."""
    return {"returncode": None, "stdout": None, "stderr": None}


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
    schema_path = temp_workspace / filename
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove yaml language marker if present
    content = docstring
    if content and content.strip().startswith("yaml"):
        content = "\n".join(content.strip().split("\n")[1:])

    schema_path.write_text(content.strip() if content else "", encoding="utf-8")
    schema_files[filename] = schema_path


@when(parsers.parse("I run the CLI command: `{command}`"))
def run_cli_command(temp_workspace, cli_result, command):
    """Execute a CLI command using subprocess."""
    # Extract the actual command (remove backticks and handle quoting)
    cmd_parts = []

    if command.startswith("./teds.py"):
        # Use the teds.py script from the repo root with current Python interpreter
        teds_path = Path(__file__).parent.parent.parent / "teds.py"
        import sys

        cmd_parts = [sys.executable, str(teds_path)]
        # Add the rest of the command
        rest = command[len("./teds.py") :].strip()
        if rest:
            # Handle complex quoting - split on spaces but keep quoted strings together
            import shlex

            cmd_parts.extend(shlex.split(rest))
    else:
        # Generic command handling
        import shlex

        cmd_parts = shlex.split(command)

    # Run the command
    result = subprocess.run(
        cmd_parts, cwd=temp_workspace, capture_output=True, text=True
    )

    cli_result["returncode"] = result.returncode
    cli_result["stdout"] = result.stdout
    cli_result["stderr"] = result.stderr

    # Debug output for troubleshooting
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        print(f"Command: {' '.join(cmd_parts)}")
        print(f"Working dir: {temp_workspace}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")


@then(parsers.parse('a test file "{filename}" should be created'))
def verify_test_file_exists(temp_workspace, test_files, filename):
    """Verify that a test file was created."""
    test_path = temp_workspace / filename
    assert test_path.exists(), f"Test file {filename} was not created. Files in directory: {list(temp_workspace.iterdir())}"
    test_files[filename] = test_path


@then(parsers.parse("the test file should contain exactly these test keys:"))
def verify_test_keys_present(test_files, temp_workspace):
    """Verify that specific test keys are present."""

    def _verify_keys(expected_keys):
        # Get the most recently created test file
        test_file = None
        for file_path in test_files.values():
            test_file = file_path
            break

        if not test_file:
            # Try to find any .tests.yaml file
            test_files_found = list(temp_workspace.glob("*.tests.yaml"))
            if test_files_found:
                test_file = test_files_found[0]
            else:
                pytest.fail("No test file found to verify keys")

        content = test_file.read_text(encoding="utf-8")
        yaml_content = yaml_loader.load(content)

        actual_keys = set()
        if yaml_content.get("tests"):
            actual_keys = set(yaml_content["tests"].keys())

        expected_keys_list = [key.strip('- "') for key in expected_keys if key.strip()]
        expected_keys_set = set(expected_keys_list)

        assert (
            actual_keys == expected_keys_set
        ), f"Expected keys {expected_keys_set}, but got {actual_keys}. File content:\n{content}"

    return _verify_keys


@then(parsers.parse("the test file should NOT contain:"))
def verify_test_keys_absent(test_files, temp_workspace):
    """Verify that specific test keys are NOT present."""

    def _verify_keys_absent(unwanted_keys):
        # Get the most recently created test file
        test_file = None
        for file_path in test_files.values():
            test_file = file_path
            break

        if not test_file:
            # Try to find any .tests.yaml file
            test_files_found = list(temp_workspace.glob("*.tests.yaml"))
            if test_files_found:
                test_file = test_files_found[0]
            else:
                pytest.fail("No test file found to verify absent keys")

        content = test_file.read_text(encoding="utf-8")
        yaml_content = yaml_loader.load(content)

        actual_keys = set()
        if yaml_content.get("tests"):
            actual_keys = set(yaml_content["tests"].keys())

        unwanted_keys_list = [key.strip('- "') for key in unwanted_keys if key.strip()]

        for unwanted_key in unwanted_keys_list:
            assert (
                unwanted_key not in actual_keys
            ), f"Unwanted key '{unwanted_key}' found in test file. Actual keys: {actual_keys}"

    return _verify_keys_absent


@then(parsers.parse("the command should fail with exit code {exit_code:d}"))
def verify_exit_code(cli_result, exit_code):
    """Verify that the command failed with the expected exit code."""
    assert (
        cli_result["returncode"] == exit_code
    ), f"Expected exit code {exit_code}, got {cli_result['returncode']}. Stderr: {cli_result['stderr']}"


@then(parsers.parse('the error output should contain "{expected_text}"'))
def verify_error_output(cli_result, expected_text):
    """Verify that the error output contains the expected text."""
    stderr = cli_result["stderr"] or ""
    assert (
        expected_text in stderr
    ), f"Expected '{expected_text}' in stderr, but got: {stderr}"
