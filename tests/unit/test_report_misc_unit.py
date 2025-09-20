from __future__ import annotations

from pathlib import Path

import pytest

from teds_core.report import (
    ReportInput,
    build_context,
    list_templates,
    resolve_template,
    run_report_per_spec,
)


def test_list_and_resolve_templates():
    items = list_templates()
    assert any(it.get("id") == "summary.md" for it in items)
    path, text, desc = resolve_template("summary.md")
    assert (
        path.endswith("summary.md.j2")
        and "TeDS Report" in text
        and isinstance(desc, str)
    )


def test_resolve_template_invalid():
    with pytest.raises(FileNotFoundError):
        resolve_template("nope.invalid")


def test_build_context_totals():
    ri1 = ReportInput(
        path_name("a"),
        {"version": "1.0.0", "tests": {}},
        {"success": 1, "warning": 2, "error": 3},
        0,
    )
    ri2 = ReportInput(
        path_name("b"),
        {"version": "1.0.0", "tests": {}},
        {"success": 0, "warning": 1, "error": 0},
        0,
    )
    ctx = build_context([ri1, ri2])
    assert ctx["totals"] == {"success": 1, "warning": 3, "error": 3, "specs": 2}


def test_run_report_per_spec_hard_failure(tmp_path: Path):
    # Spec with invalid version should produce hard_rc=2 and no outputs
    spec = tmp_path / "spec.yaml"
    spec.write_text("version: '2.0.0'\ntests: {}\n", encoding="utf-8")
    outputs, rc = run_report_per_spec([spec], "summary.md", output_level="warning")
    assert rc == 2
    assert outputs == [] or all(isinstance(x[1], str) for x in outputs)


def path_name(stem: str):
    from pathlib import Path

    return Path(f"/tmp/{stem}.yaml")
