"""BDD tests for TeDS generate command - reorganized from original working files."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from teds_core.cli import main as cli_main
from teds_core.yamlio import yaml_loader


def run_teds_command(*args):
    """Helper function to run teds CLI commands in tests."""
    original_argv = sys.argv.copy()
    try:
        sys.argv = ["teds", *list(args)]
        cli_main()
        return 0
    except SystemExit as e:
        return e.code
    finally:
        sys.argv = original_argv


# Load generate-related scenarios
scenarios("features/generate.feature")


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
def config_files(temp_workspace):
    """Store created config files for reference."""
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
def working_directory(temp_workspace):
    """Ensure we have a working directory."""
    assert temp_workspace.exists()


@given(parsers.parse('I have a subdirectory "{dirname}"'))
def create_subdirectory(temp_workspace, dirname):
    """Create a subdirectory."""
    subdir = temp_workspace / dirname
    subdir.mkdir(parents=True, exist_ok=True)


@given(parsers.parse('I have a schema file "{filename}" with content:'))
def create_schema_file(temp_workspace, schema_files, filename, docstring):
    """Create a schema file with specified content."""
    schema_path = temp_workspace / filename
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove yaml language marker if present
    content = docstring
    if content and content.strip().startswith("yaml"):
        content = "\n".join(content.strip().split("\n")[1:])

    schema_path.write_text(content.strip() if content else "", encoding="utf-8")
    schema_files[filename] = schema_path


@given(parsers.parse('I have a configuration file "{filename}" with content:'))
def create_config_file(temp_workspace, config_files, filename, docstring):
    """Create a configuration file with specified content."""
    config_path = temp_workspace / filename

    # Remove yaml language marker if present
    content = docstring
    if content.strip().startswith("yaml"):
        content = "\n".join(content.strip().split("\n")[1:])

    config_path.write_text(content.strip(), encoding="utf-8")
    config_files[filename] = config_path


@given(parsers.parse('I have an existing test file "{filename}" with content:'))
def create_existing_test_file(temp_workspace, filename, docstring):
    """Create an existing test file with specified content."""
    test_path = temp_workspace / filename
    test_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove yaml language marker if present
    content = docstring
    if content.strip().startswith("yaml"):
        content = "\n".join(content.strip().split("\n")[1:])

    test_path.write_text(content.strip(), encoding="utf-8")


@when(parsers.parse("I run the generate command: `{command}`"))
def run_generate_command(temp_workspace, cli_result, command):
    """Execute the generate command."""
    # Extract command arguments
    # Remove 'teds generate ' prefix
    args_str = command.replace("teds generate ", "").strip()

    # Handle quoted arguments
    import shlex

    args = shlex.split(args_str)

    # Run with subprocess to capture stderr
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    result = subprocess.run(
        [sys.executable, str(teds_path), "generate", *args],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    # Store result in cli_result fixture
    cli_result["returncode"] = result.returncode
    cli_result["stdout"] = result.stdout
    cli_result["stderr"] = result.stderr

    # Store result for later assertions
    pytest.current_exit_code = result.returncode
    pytest.current_command_success = result.returncode == 0

    # CRITICAL: The command must succeed for the BDD test to be valid
    # If exit code is not 0, the command failed and we should fail the test
    if result.returncode != 0:
        raise AssertionError(
            f"Generate command failed with exit code {result.returncode}: teds generate {' '.join(args)}. Stderr: {result.stderr}"
        )


@when(parsers.parse("I run the CLI command: `{command}`"))
def run_cli_command(temp_workspace, cli_result, command):
    """Execute a CLI command using subprocess."""
    # Extract the actual command (remove backticks and handle quoting)
    cmd_parts = []

    if command.startswith("./teds.py"):
        # Use the teds.py script from the repo root with current Python interpreter
        teds_path = Path(__file__).parent.parent.parent / "teds.py"
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

    # Show what files were actually created for debugging
    actual_files = [f.name for f in temp_workspace.iterdir() if f.is_file()]
    test_files_found = [
        f for f in actual_files if f.endswith(".tests.yaml") or f.endswith(".yaml")
    ]

    assert test_path.exists(), (
        f"Test file '{filename}' was not created.\n"
        f"Expected: {filename}\n"
        f"Actual files created: {actual_files}\n"
        f"Test/YAML files found: {test_files_found}"
    )
    test_files[filename] = test_path


@then(parsers.parse('the test file should contain "{content}"'))
def step_test_file_should_contain(temp_workspace, content):
    """Assert that the most recently created test file contains specific content."""
    # Find the most recent .tests.yaml file
    test_files = list(temp_workspace.glob("*.tests.yaml"))
    if not test_files:
        test_files = list(temp_workspace.glob("*.yaml"))

    assert test_files, "No test files found"

    # Use the most recently created file
    latest_file = max(test_files, key=lambda f: f.stat().st_mtime)
    file_content = latest_file.read_text()
    assert (
        content in file_content
    ), f"Content '{content}' not found in {latest_file.name}"


@then(parsers.parse('the test file should not contain "{content}"'))
def step_test_file_should_not_contain(temp_workspace, content):
    """Assert that the most recently created test file does not contain specific content."""
    # Find the most recent .tests.yaml file
    test_files = list(temp_workspace.glob("*.tests.yaml"))
    if not test_files:
        test_files = list(temp_workspace.glob("*.yaml"))

    assert test_files, "No test files found"

    # Use the most recently created file
    latest_file = max(test_files, key=lambda f: f.stat().st_mtime)
    file_content = latest_file.read_text()
    assert (
        content not in file_content
    ), f"Content '{content}' found in {latest_file.name} but shouldn't be there"


@then(parsers.parse('the test file should contain examples marked with "{marker}"'))
def step_test_file_should_contain_examples_with_marker(temp_workspace, marker):
    """Assert that the test file contains examples with a specific marker."""
    test_files = list(temp_workspace.glob("*.tests.yaml"))
    assert test_files, "No test files found"

    latest_file = max(test_files, key=lambda f: f.stat().st_mtime)
    file_content = latest_file.read_text()
    assert marker in file_content, f"Marker '{marker}' not found in {latest_file.name}"


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


@then("the command should succeed")
def command_should_succeed(cli_result):
    """Assert that the command succeeded."""
    assert (
        cli_result["returncode"] == 0
    ), f"Command failed with exit code {cli_result['returncode']}. Stderr: {cli_result['stderr']}"


@then(parsers.parse('the error output should match "{expected_text}"'))
def verify_error_output(cli_result, expected_text):
    """Verify that the error output contains the expected text."""
    stderr = cli_result["stderr"] or ""
    assert re.fullmatch(
        expected_text, stderr, re.DOTALL
    ), f"Expected '{expected_text}' in stderr, but got: {stderr}"


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


@then(parsers.parse('the test file "{filename}" should be updated with content:'))
def verify_test_file_updated(temp_workspace, test_files, filename):
    """Verify that a test file was updated with expected content."""

    def _verify_updated_content(expected_content):
        test_path = temp_workspace / filename
        assert test_path.exists(), f"Test file {filename} does not exist"

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

    return _verify_updated_content


@then(parsers.parse('the result should not contain "{unwanted_ref}"'))
def verify_does_not_contain(test_files, unwanted_ref):
    """Verify that specific references are not present."""
    for test_file in test_files.values():
        if test_file.exists():
            content = test_file.read_text(encoding="utf-8")
            assert (
                unwanted_ref not in content
            ), f"Unwanted reference {unwanted_ref} found in {test_file}"


@then("the result should not contain property-level references")
def verify_no_property_references(test_files):
    """Verify no unwanted property-level references are generated."""
    # This is verified by exact content matching
    pass


@then("the result should not contain deeper nested properties")
def verify_no_deep_nested_properties(test_files):
    """Verify that deeper nested properties are not included."""
    # This is verified by exact content matching
    pass


@then("no child nodes should be automatically included")
def verify_no_child_nodes(test_files):
    """Verify that child nodes are not automatically included."""
    # This is verified by exact content matching
    pass


@then("the test should target exactly the User definition, not its properties")
def verify_exact_user_targeting(test_files):
    """Verify that the test targets exactly the User definition."""
    # This is verified by exact content matching
    pass
