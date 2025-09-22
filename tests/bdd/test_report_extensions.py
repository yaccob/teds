"""BDD tests for report file extensions using pytest-bdd."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Load all scenarios from the feature file
scenarios("features/report_extensions.feature")


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
def command_result():
    """Store command execution results."""
    return {}


@given("I have a working directory")
def working_directory(temp_workspace):
    """Ensure we have a clean working directory."""
    assert temp_workspace.exists()


@given(parsers.parse('I have a schema file "{filename}" with content:'))
def create_schema_file(temp_workspace, filename, docstring):
    """Create a schema file with specified content."""
    file_path = temp_workspace / filename
    # Remove the yaml prefix from docstring format
    clean_content = docstring.replace("yaml\n", "").strip()
    file_path.write_text(clean_content, encoding="utf-8")


@given(parsers.parse('I have a testspec file "{filename}" with content:'))
def create_testspec_file(temp_workspace, filename, docstring):
    """Create a testspec file with specified content."""
    file_path = temp_workspace / filename
    # Remove the yaml prefix from docstring format
    clean_content = docstring.replace("yaml\n", "").strip()
    file_path.write_text(clean_content, encoding="utf-8")


@when(parsers.parse('I run the command "{command}"'))
def run_command(temp_workspace, command_result, command):
    """Execute a CLI command and store the result."""
    # Get the path to teds.py from the project root
    project_root = Path(__file__).resolve().parents[2]
    teds_script = project_root / "teds.py"

    # Split command and prepare arguments
    args = command.split()
    cmd = ["python", str(teds_script), *args]

    result = subprocess.run(
        cmd, cwd=str(temp_workspace), capture_output=True, text=True
    )

    command_result["returncode"] = result.returncode
    command_result["stdout"] = result.stdout
    command_result["stderr"] = result.stderr


@then("the command should succeed")
def command_should_succeed(command_result):
    """Verify that the command executed successfully."""
    assert (
        command_result["returncode"] == 0
    ), f"Command failed with: {command_result['stderr']}"


@then(parsers.parse('a file "{filename}" should be created'))
def file_should_be_created(temp_workspace, filename):
    """Verify that a specific file was created."""
    file_path = temp_workspace / filename
    assert file_path.exists(), f"Expected file {filename} to be created"


@then(parsers.parse('the file "{filename}" should contain AsciiDoc content'))
def file_should_contain_asciidoc(temp_workspace, filename):
    """Verify that the file contains AsciiDoc content."""
    file_path = temp_workspace / filename
    content = file_path.read_text(encoding="utf-8")
    # AsciiDoc typically uses = for headers
    assert "=" in content, f"Expected AsciiDoc headers with = signs in {filename}"


@then(parsers.parse('the file "{filename}" should contain HTML content'))
def file_should_contain_html(temp_workspace, filename):
    """Verify that the file contains HTML content."""
    file_path = temp_workspace / filename
    content = file_path.read_text(encoding="utf-8")
    # HTML should contain basic HTML tags
    assert any(
        tag in content.lower() for tag in ["<html>", "<body>", "<div>", "<p>"]
    ), f"Expected HTML tags in {filename}"


@then(parsers.parse('the file "{filename}" should contain Markdown content'))
def file_should_contain_markdown(temp_workspace, filename):
    """Verify that the file contains Markdown content."""
    file_path = temp_workspace / filename
    content = file_path.read_text(encoding="utf-8")
    # Markdown typically uses # for headers or other markdown syntax
    assert any(
        marker in content for marker in ["#", "*", "-", "`"]
    ), f"Expected Markdown syntax in {filename}"
