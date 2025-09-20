from __future__ import annotations

from pathlib import Path

import pytest

from teds_core.errors import TedsError
from teds_core.generate import generate_from
from tests.utils import load_yaml_file


def test_generate_non_dict_parent_writes_doc(tmp_path: Path):
    # Schema root is a list (non-dict) so generate_from should just write doc and return
    schema = tmp_path / "s.yaml"
    schema.write_text("- 1\n- 2\n", encoding="utf-8")
    out = tmp_path / "out.yaml"
    generate_from(f"{schema}#/", out)
    assert out.exists()
    doc = load_yaml_file(out)
    assert isinstance(doc.get("tests"), dict)


def test_generate_merges_existing_and_inserts_examples(tmp_path: Path):
    schema = tmp_path / "s.yaml"
    schema.write_text(
        """
components:
  schemas:
    C:
      type: string
      examples: ["a", "b"]
""",
        encoding="utf-8",
    )
    out = tmp_path / "out.yaml"
    # Pre-populate doc with an existing valid entry
    out.write_text(
        f"""
tests:
  {schema}#/components/schemas/C:
    valid:
      existing:
        payload: "x"
""",
        encoding="utf-8",
    )
    generate_from(f"{schema}#/components/schemas", out)
    doc = load_yaml_file(out)
    grp = doc["tests"][f"{schema}#/components/schemas/C"]
    valid = list(grp["valid"].keys())
    # Example-derived keys should be present alongside 'existing'
    assert any(".examples[0]" in k for k in valid) and any(
        ".examples[1]" in k for k in valid
    )


def test_generate_from_file_read_error(tmp_path: Path):
    # Test exception handling when reading existing testspec fails
    schema = tmp_path / "s.yaml"
    schema.write_text("type: string\n", encoding="utf-8")
    testspec = tmp_path / "out.yaml"
    testspec.write_text("invalid: yaml: content", encoding="utf-8")

    with pytest.raises(TedsError, match="Failed to read or create testspec"):
        generate_from(f"{schema}#/", testspec)


def test_generate_from_schema_resolution_error(tmp_path: Path):
    # Test exception handling when schema resolution fails
    testspec = tmp_path / "out.yaml"

    with pytest.raises(TedsError, match="Failed to resolve parent schema ref"):
        generate_from("nonexistent.yaml#/", testspec)


def test_generate_from_write_error_non_dict_parent(tmp_path: Path):
    # Test write error handling for non-dict parent case
    # Use a read-only file to trigger the write error path
    schema = tmp_path / "s.yaml"
    schema.write_text("- not a dict\n", encoding="utf-8")
    testspec = tmp_path / "readonly.yaml"
    testspec.write_text("{}\n", encoding="utf-8")
    testspec.chmod(0o444)  # Make file read-only

    with pytest.raises(TedsError, match="Failed to write testspec"):
        generate_from(f"{schema}#/", testspec)


def test_generate_from_write_error_final(tmp_path: Path):
    # Test write error handling for final write
    schema = tmp_path / "s.yaml"
    schema.write_text("components: {schemas: {A: {type: string}}}\n", encoding="utf-8")
    testspec = tmp_path / "readonly.yaml"
    testspec.write_text("{}\n", encoding="utf-8")
    testspec.chmod(0o444)  # Make file read-only

    with pytest.raises(TedsError, match="Failed to write testspec"):
        generate_from(f"{schema}#/components/schemas", testspec)
