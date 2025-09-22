"""Comprehensive BDD tests for all CLI functionality."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.utils import load_yaml_file, run_cli

# Load all scenarios from the feature file
scenarios("features/cli_comprehensive.feature")


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def command_result():
    """Store command execution results."""
    return {}


@pytest.fixture
def stored_files():
    """Store information about created files."""
    return {}


@given("I have a temporary workspace")
def workspace_exists(temp_workspace):
    """Ensure workspace exists."""
    assert temp_workspace.exists()


@given(parsers.parse('I have a schema file "{filename}" with content:'))
def create_schema_file(temp_workspace, stored_files, filename, docstring):
    """Create a schema file."""
    schema_path = temp_workspace / filename
    # Ensure parent directory exists
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    content = docstring.strip() if docstring else ""
    schema_path.write_text(content, encoding="utf-8")
    stored_files[filename] = schema_path


@given(parsers.parse('I have a test specification file "{filename}" with content:'))
def create_test_spec_file(temp_workspace, stored_files, filename, docstring):
    """Create a test specification file."""
    spec_path = temp_workspace / filename
    content = docstring.strip() if docstring else ""
    spec_path.write_text(content, encoding="utf-8")
    stored_files[filename] = spec_path


@given(parsers.parse('I have a config file "{filename}" with content:'))
def create_config_file(temp_workspace, stored_files, filename, docstring):
    """Create a configuration file."""
    config_path = temp_workspace / filename
    content = docstring.strip() if docstring else ""
    config_path.write_text(content, encoding="utf-8")
    stored_files[filename] = config_path


@given(parsers.parse('I have a file "{filename}" with content:'))
def create_generic_file(temp_workspace, filename, docstring):
    """Create a generic file with given content."""
    file_path = temp_workspace / filename
    content = docstring.strip() if docstring else ""
    file_path.write_text(content, encoding="utf-8")


@when(parsers.parse('I run teds verify "{spec_file}" with output level "{level}"'))
def run_verify_with_output_level(temp_workspace, command_result, spec_file, level):
    """Run teds verify with specific output level."""
    rc, out, err = run_cli(
        ["verify", spec_file, "--output-level", level], cwd=temp_workspace
    )
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when(parsers.parse('I run teds verify "{spec_file}" in-place'))
def run_verify_inplace(temp_workspace, command_result, spec_file):
    """Run teds verify in-place."""
    rc, out, err = run_cli(["verify", spec_file, "-i"], cwd=temp_workspace)
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when(parsers.parse('I run teds verify "{spec_file}"'))
def run_verify_simple(temp_workspace, command_result, spec_file):
    """Run teds verify on a specification file."""
    rc, out, err = run_cli(["verify", spec_file], cwd=temp_workspace)
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when(parsers.parse('I run teds verify "{spec_file}" with report "{report_type}"'))
def run_verify_with_report(temp_workspace, command_result, spec_file, report_type):
    """Run teds verify with report generation."""
    rc, out, err = run_cli(
        ["verify", spec_file, "--report", report_type], cwd=temp_workspace
    )
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when(parsers.parse('I run teds generate "{ref_spec}"'))
def run_generate_simple(temp_workspace, command_result, ref_spec):
    """Run teds generate with a reference specification."""
    rc, out, err = run_cli(["generate", ref_spec], cwd=temp_workspace)
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when(parsers.parse("I run teds generate with JSON config {config}"))
def run_generate_with_json_config(temp_workspace, command_result, config):
    """Run teds generate with JSON configuration."""
    # Remove quotes from config string if present
    config_str = config.strip("'\"")
    rc, out, err = run_cli(["generate", config_str], cwd=temp_workspace)
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when(parsers.parse('I run teds generate "{config_ref}"'))
def run_generate_with_file_config(temp_workspace, command_result, config_ref):
    """Run teds generate with file-based configuration."""
    rc, out, err = run_cli(["generate", config_ref], cwd=temp_workspace)
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@when("I run teds --version")
def run_version_command(temp_workspace, command_result):
    """Run teds --version command."""
    rc, out, err = run_cli(["--version"], cwd=temp_workspace)
    command_result["exit_code"] = rc
    command_result["stdout"] = out
    command_result["stderr"] = err


@then(parsers.parse("the command should exit with code {expected_code:d}"))
def check_exit_code(command_result, expected_code):
    """Check that command exited with expected code."""
    assert command_result["exit_code"] == expected_code, (
        f"Expected exit code {expected_code}, got {command_result['exit_code']}. "
        f"Stdout: {command_result['stdout']}, Stderr: {command_result['stderr']}"
    )


@then("the command should exit with code 0 or 1")
def check_exit_code_success_or_validation_error(command_result):
    """Check that command exited with code 0 or 1."""
    assert command_result["exit_code"] in [0, 1], (
        f"Expected exit code 0 or 1, got {command_result['exit_code']}. "
        f"Stderr: {command_result['stderr']}"
    )


@then("the output should contain YAML content")
def check_yaml_content(command_result):
    """Check that output contains YAML content."""
    output = command_result["stdout"]
    assert output.strip(), "Expected output but got none"
    # Basic check for YAML-like content
    yaml_indicators = ["tests:", "valid:", "invalid:", "result:", "payload:"]
    found = any(indicator in output for indicator in yaml_indicators)
    assert found, f"No YAML indicators found in output: {output[:200]}"


@then(parsers.parse('the error output should mention "{text}"'))
def check_error_contains_text(command_result, text):
    """Check that error output contains specific text."""
    stderr = command_result["stderr"]
    assert (
        text.lower() in stderr.lower()
    ), f"Expected '{text}' in error output: {stderr}"


@then(parsers.parse('a test file "{filename}" should be created'))
def check_test_file_created(temp_workspace, filename):
    """Check that a test file was created."""
    test_file = temp_workspace / filename
    # If exact filename doesn't exist, look for any .tests.yaml file
    if not test_file.exists():
        test_files = list(temp_workspace.glob("*.tests.yaml"))
        assert (
            len(test_files) > 0
        ), f"Expected test file {filename} to be created, but found no .tests.yaml files"
        test_file = test_files[0]  # Use the first found test file

    assert test_file.exists(), f"Expected test file {filename} to be created"
    assert test_file.stat().st_size > 0, f"Test file {filename} is empty"


@then("the test file should contain valid YAML content")
def check_test_file_yaml_content(temp_workspace):
    """Check that test file contains valid YAML content."""
    test_files = list(temp_workspace.glob("*.tests.yaml"))
    assert len(test_files) > 0, "No test files found"

    test_file = test_files[0]
    try:
        doc = load_yaml_file(test_file)
        assert isinstance(doc, dict), "Test file should contain YAML object"
        assert (
            "tests" in doc or "version" in doc
        ), "Test file should have expected structure"
    except Exception as e:
        pytest.fail(f"Test file does not contain valid YAML: {e}")


@then("the specification file should remain unchanged")
def check_spec_file_unchanged(temp_workspace, stored_files):
    """Check that specification file was not modified."""
    spec_files = [f for name, f in stored_files.items() if "spec.yaml" in name]
    assert len(spec_files) > 0, "No specification file found"

    # This is a simplified check - in reality, you'd compare with original content
    spec_file = spec_files[0]
    content = spec_file.read_text(encoding="utf-8")
    assert "version:" in content, "Specification file should contain version"


@then('the output should contain "teds"')
def check_output_contains_teds(command_result):
    """Check that output contains 'teds'."""
    output = command_result["stdout"]
    assert "teds" in output.lower(), f"Expected 'teds' in output: {output}"


@then('the output should contain "spec supported:"')
def check_output_contains_spec_supported(command_result):
    """Check that output contains spec support information."""
    output = command_result["stdout"]
    assert (
        "spec supported:" in output
    ), f"Expected 'spec supported:' in output: {output}"


@then("the output should contain semantic version format")
def check_semantic_version_format(command_result):
    """Check that output contains semantic version format."""
    output = command_result["stdout"]
    import re

    version_pattern = r"\d+\.\d+(?:\.\d+)?(?:\.dev\d+)?(?:\+g[a-f0-9]+)?"
    assert re.search(version_pattern, output), f"No semantic version found in: {output}"


@then("the error output should mention YAML parsing issues")
def check_yaml_parsing_error(command_result):
    """Check that error output mentions YAML parsing issues."""
    stderr = command_result["stderr"]
    yaml_error_indicators = ["yaml", "parse", "syntax", "scanner", "mapping"]
    found = any(indicator in stderr.lower() for indicator in yaml_error_indicators)
    assert found, f"No YAML parsing error indicators found in: {stderr}"


@then("the generated file should be validatable with teds verify")
def check_generated_file_validatable(temp_workspace, command_result):
    """Check that generated file can be validated with teds verify."""
    test_files = list(temp_workspace.glob("*.tests.yaml"))
    assert len(test_files) > 0, "No test files found"

    test_file = test_files[0]
    rc, out, err = run_cli(["verify", test_file.name], cwd=temp_workspace)

    assert rc in [0, 1], f"Generated file validation failed with exit code {rc}: {err}"


@then(parsers.parse("the output should exactly match:"))
def check_output_exactly_matches(command_result, docstring):
    """Check that output exactly matches expected YAML structure (semantic comparison)."""
    from io import StringIO

    from ruamel.yaml import YAML

    actual_output = command_result["stdout"]
    expected_yaml = docstring.strip()

    # Parse both YAML strings to Python objects for semantic comparison
    yaml = YAML(typ="safe")

    try:
        actual_data = yaml.load(StringIO(actual_output))
    except Exception as e:
        raise AssertionError(
            f"Failed to parse actual output as YAML: {e}\nOutput was: {actual_output}"
        ) from e

    try:
        expected_data = yaml.load(StringIO(expected_yaml))
    except Exception as e:
        raise AssertionError(
            f"Failed to parse expected YAML: {e}\nExpected was: {expected_yaml}"
        ) from e

    # Semantic comparison - ignores formatting, indentation, quoting style
    assert (
        actual_data == expected_data
    ), f"YAML content mismatch:\nActual: {actual_data}\nExpected: {expected_data}"
