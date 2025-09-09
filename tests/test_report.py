from __future__ import annotations

from pathlib import Path

from tests.test_cli import run_cli


def test_report_markdown(tmp_path: Path):
    # Use existing case directory
    case = Path(__file__).parent / "cases" / "format_divergence"
    rc, out, err = run_cli([
        "report",
        "--template",
        "summary.md",
        str(case / "spec.yaml"),
    ])
    assert rc == 0
    assert "TeDS Report" in out
    assert str(case / "spec.yaml") in out or "format_divergence" in out

