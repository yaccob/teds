from __future__ import annotations

from pathlib import Path

from teds_core.refs import split_json_pointer, jq_examples_prefix, jq_segment, _retrieve


def test_split_json_pointer_and_jq():
    assert split_json_pointer("/a/b") == ["a", "b"]
    assert split_json_pointer("/a~1b/~0c") == ["a/b", "~c"]
    assert jq_segment("ok") == ".ok"
    assert jq_segment("not-ok") == '.["not-ok"]'
    assert jq_examples_prefix("/components/schemas/A") == ".components.schemas.A"
    assert jq_examples_prefix("/") == ""


def test_retrieve_file_uri(tmp_path: Path):
    p = tmp_path / "x.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    res = _retrieve(p.as_uri())
    assert res.contents.get("a") == 1

