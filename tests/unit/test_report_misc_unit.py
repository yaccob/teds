from __future__ import annotations

import pytest

from teds_core.report import list_templates, resolve_template, build_context, ReportInput


def test_list_and_resolve_templates():
    items = list_templates()
    assert any(it.get("id") == "summary.md" for it in items)
    path, text, desc = resolve_template("summary.md")
    assert path.endswith("summary.md.j2") and "TeDS Report" in text and isinstance(desc, str)


def test_resolve_template_invalid():
    with pytest.raises(FileNotFoundError):
        resolve_template("nope.invalid")


def test_build_context_totals():
    ri1 = ReportInput(path_name("a"), {"version": "1.0.0", "tests": {}}, {"success": 1, "warning": 2, "error": 3}, 0)
    ri2 = ReportInput(path_name("b"), {"version": "1.0.0", "tests": {}}, {"success": 0, "warning": 1, "error": 0}, 0)
    ctx = build_context([ri1, ri2])
    assert ctx["totals"] == {"success": 1, "warning": 3, "error": 3, "specs": 2}


def path_name(stem: str):
    from pathlib import Path
    return Path(f"/tmp/{stem}.yaml")

