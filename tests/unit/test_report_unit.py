from __future__ import annotations

from pathlib import Path

from teds_core.report import run_report_per_spec


def test_run_report_per_spec_markdown(tmp_path: Path):
    # Minimal valid spec with one empty tests group referencing a real schema
    schema = tmp_path / "schema.yaml"
    schema.write_text("{}\n", encoding="utf-8")
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        f"""
version: "1.0.0"
tests:
  {schema}#/:
    valid: {{}}
    invalid: {{}}
""",
        encoding="utf-8",
    )
    outputs, rc = run_report_per_spec([spec], "summary.md", output_level="warning")
    assert rc in (0, 1)
    assert outputs and outputs[0][0] == spec
    content = outputs[0][1]
    assert "TeDS Report" in content
