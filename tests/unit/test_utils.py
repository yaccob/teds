import subprocess
import sys
from pathlib import Path

import pytest
from jsonpath_ng import parse

from teds_core.utils import json_path_to_json_pointer


@pytest.mark.parametrize(
    "jsonpath_expr,expected_pointer",
    [
        # Root only
        ("$", ""),
        # Single field
        ("$.foo", "/foo"),
        # Nested fields
        ("$.foo.bar", "/foo/bar"),
        # Field with index
        ("$.foo[2]", "/foo/2"),
        # Nested index
        ("$[1].bar", "/1/bar"),
        # Escaping: field with ~ or /
        ('$["foo~bar"]', "/foo~0bar"),
        ('$["foo/bar"]', "/foo~1bar"),
    ],
)
def test_json_path_to_json_pointer(jsonpath_expr, expected_pointer):
    # Create test documents to match against different expressions
    if jsonpath_expr == "$.foo[2]":
        # foo needs to be an array with at least 3 elements for [2] to work
        test_doc = {"foo": ["item0", "item1", "item2"], "bar": "other"}
    elif jsonpath_expr == "$[1].bar":
        # Root needs to be an array with at least 2 elements where element 1 has bar
        test_doc = [{"name": "first"}, {"bar": "value", "name": "second"}]
    else:
        # Standard document for other cases
        test_doc = {
            "foo": {"bar": "value"},
            "items": ["item0", {"name": "item1"}],
            "foo~bar": "tilde_test",
            "foo/bar": "slash_test",
        }

    parser = parse(jsonpath_expr)
    matches = parser.find(test_doc)

    # Should find at least one match for our test cases
    assert len(matches) > 0, f"No matches found for {jsonpath_expr}"

    # Test the first match
    match = matches[0]
    pointer = json_path_to_json_pointer(match.full_path)
    assert pointer == expected_pointer


def test_json_path_to_json_pointer_unhandled_type():
    class Dummy:
        pass

    with pytest.raises(ValueError):
        json_path_to_json_pointer(None)


# CLI runner (used by CLI tests)
_SCRIPT = Path(__file__).resolve().parents[1] / "teds.py"


def run_cli(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr
