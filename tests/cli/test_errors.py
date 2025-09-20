from __future__ import annotations

from pathlib import Path

from tests.utils import run_cli  # reuse local CLI runner


def test_verify_reports_yaml_parse_error(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("invalid: [1,\n", encoding="utf-8")
    rc, _out, err = run_cli(["verify", "bad.yaml"], cwd=tmp_path)
    assert rc == 2
    assert "Failed to read testspec" in err


def test_verify_reports_spec_validation_error(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text("{}\n", encoding="utf-8")
    rc, _out, err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    assert rc == 2
    assert "Spec validation failed" in err


def test_verify_reports_missing_schema_file(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
version: "1.0.0"
tests:
  sch.yaml#/:
    valid:
      v1:
        payload: 1
""",
        encoding="utf-8",
    )
    rc, _out, _err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    # Build may succeed, but case evaluation should report a failure
    assert rc == 2


def test_generate_reports_missing_schema_file(tmp_path: Path):
    rc, _out, err = run_cli(
        ["generate", "missing.yaml#/components/schemas=out.yaml"], cwd=tmp_path
    )
    assert rc == 2
    assert "Failed to resolve parent schema ref" in err


def test_verify_reports_unsupported_ref_scheme(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
version: "1.0.0"
tests:
  http://example.com/schema.yaml#/:
    valid:
      v1:
        payload: 1
""",
        encoding="utf-8",
    )
    rc, _out, _err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    assert rc == 2
