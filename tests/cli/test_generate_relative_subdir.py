from __future__ import annotations

from pathlib import Path

from tests.utils import load_yaml_file, run_cli


def test_generate_with_relative_schema_in_subdir(tmp_path: Path, monkeypatch):
    # Create nested subdir with a minimal schema
    sub = tmp_path / "sub"
    sub.mkdir()
    schema = sub / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    A:
      type: string
      examples: [x]
""",
        encoding="utf-8",
    )

    # Run from tmp root, pass a relative path into a subdirectory
    rc, _out, err = run_cli(["generate", "sub/schema.yaml#/"], cwd=tmp_path)
    assert rc == 0, err

    # Expect default filename next to the schema
    out_file = sub / "schema.tests.yaml"
    assert out_file.exists()
    doc = load_yaml_file(out_file)
    # Contains group for '#/' and example-derived case
    keys = list((doc.get("tests") or {}).keys())
    assert any("schema.yaml#/" in k for k in keys) or any(
        "schema.yaml#/A" in k for k in keys
    )
