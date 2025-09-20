from __future__ import annotations

from pathlib import Path

from teds_core.refs import collect_examples, join_fragment, resolve_schema_node


def test_refs_resolve_and_examples(tmp_path: Path):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    A:
      type: string
      examples: ["x", "y"]
    B:
      type: integer
      minimum: 1
""",
        encoding="utf-8",
    )
    node, frag = resolve_schema_node(tmp_path, f"{schema}#/components/schemas")
    assert isinstance(node, dict)
    assert frag == "components/schemas"
    # collect examples for A
    ex = list(collect_examples(tmp_path, f"{schema}#/components/schemas/A"))
    assert ex and ex[0][0]
    assert join_fragment("components/schemas", "A") == "components/schemas/A"
