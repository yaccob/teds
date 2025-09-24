"""Python tests for TeDS verify functionality - copied from test_tutorial_examples_simple.py"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)


def test_basic_email_validation_from_tutorial(temp_workspace):
    """Test basic email validation from tutorial Chapter 1."""
    # Create email schema
    schema_content = """
type: string
format: email
"""
    schema_file = temp_workspace / "user_email.yaml"
    schema_file.write_text(schema_content.strip())

    # Create test specification
    test_content = """
version: "1.0.0"
tests:
  user_email.yaml#:
    valid:
      simple_email:
        description: "Basic valid email"
        payload: "alice@example.com"
      email_with_subdomain:
        description: "Email with subdomain"
        payload: "bob@mail.company.com"
    invalid:
      missing_at:
        description: "Email without @ symbol"
        payload: "alice.example.com"
      missing_domain:
        description: "Email without domain"
        payload: "alice@"
"""
    test_file = temp_workspace / "user_email.tests.yaml"
    test_file.write_text(test_content.strip())

    # Run verify command
    teds_path = Path(__file__).parent.parent.parent / "teds.py"
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(teds_path),
            "verify",
            "user_email.tests.yaml",
            "--output-level",
            "all",
        ],
        capture_output=True,
        text=True,
        cwd=str(temp_workspace),
    )

    assert (
        result.returncode == 1
    ), f"Verify command should report validation errors: {result.stderr}"

    # Check that output contains expected results
    output = result.stdout
    assert "simple_email" in output
    assert "email_with_subdomain" in output
    assert "missing_domain" in output
