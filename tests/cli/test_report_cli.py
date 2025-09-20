from __future__ import annotations

from pathlib import Path

from tests.utils import run_cli


def test_report_markdown(tmp_path: Path):
    # Use existing case directory
    case = Path(__file__).resolve().parents[1] / "cases" / "format_divergence"
    spec = case / "spec.yaml"
    rc, _out, _err = run_cli(
        [
            "verify",
            "--report",
            "summary.md",
            str(spec),
        ]
    )
    # verify semantics: rc=1 for cases with ERROR
    assert rc == 1
    # output file exists next to spec
    out_file = spec.parent / f"{spec.stem}.report.md"
    assert out_file.exists()
    txt = out_file.read_text(encoding="utf-8")
    assert "TeDS Report" in txt
