from __future__ import annotations

from pathlib import Path

from teds_core.generate import generate_from
from tests.utils import load_yaml_file


def test_generate_from_function(tmp_path: Path):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    A:
      type: string
      examples: ["x"]
    B:
      type: integer
      minimum: 1
""",
        encoding="utf-8",
    )
    out = tmp_path / "out.tests.yaml"
    generate_from(f"{schema}#/", out)
    assert out.exists()
    doc = load_yaml_file(out)
    assert "tests" in doc and isinstance(doc["tests"], dict)
    # Should contain direct children A and B groups
    keys = list(doc["tests"].keys())
    assert any(str(schema) in k for k in keys)
