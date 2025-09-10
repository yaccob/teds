from __future__ import annotations

from pathlib import Path

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

