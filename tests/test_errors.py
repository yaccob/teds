from __future__ import annotations

from pathlib import Path
import textwrap

from tests.utils import load_yaml_text

from tests.test_cli import run_cli  # reuse local CLI runner


def test_verify_reports_yaml_parse_error(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    # invalid YAML (unbalanced indent)
    bad.write_text("tests:\n  - bad", encoding="utf-8")
    rc, out, err = run_cli(["verify", "bad.yaml"], cwd=tmp_path)
    assert rc == 2
    assert out == ""
    assert "Spec validation failed:" in err
    assert "bad.yaml" in err


def test_verify_reports_spec_validation_error(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    # wrong type for tests (should be a mapping)
    spec.write_text(textwrap.dedent(
        """
        tests: []
        """
    ), encoding="utf-8")
    rc, out, err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    assert rc == 2
    assert out == ""
    assert "Spec validation failed:" in err
    assert "at: tests/" in err or "at: tests" in err


def test_verify_reports_missing_schema_file(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(textwrap.dedent(
        """
        version: "1.0.0"
        tests:
          missing.yaml#/components/schemas: {}
        """
    ), encoding="utf-8")
    rc, out, err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    assert rc == 2
    assert "Failed to build validator for ref:" in err
    assert "missing.yaml" in err


def test_generate_reports_missing_schema_file(tmp_path: Path):
    rc, out, err = run_cli(["generate", "missing.yaml#/components/schemas=out.yaml"], cwd=tmp_path)
    assert rc == 2
    assert "Failed to resolve parent schema ref:" in err or "Failed to read or create testspec:" in err


def test_verify_reports_unsupported_ref_scheme(tmp_path: Path):
    # schema with a non-file $ref to trigger retrieve error during validation
    sch = tmp_path / "sch.yaml"
    sch.write_text(textwrap.dedent(
        """
        $ref: "http://example.com/does-not-exist.json"
        """
    ), encoding="utf-8")
    spec = tmp_path / "spec.yaml"
    spec.write_text(textwrap.dedent(
        """
        version: "1.0.0"
        tests:
          sch.yaml#/:
            valid:
              v1:
                payload: 1
        """
    ), encoding="utf-8")
    rc, out, err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    # Build may succeed, but case evaluation should report a failure
    assert rc == 2
    assert (
        "Validation failed while evaluating case for ref:" in err
        or "Validation failed while evaluating example case for ref:" in err
        or "unsupported URI scheme" in err
        or "network fetch disabled" in err
    )


def test_generate_reports_output_collision(tmp_path: Path):
    # minimal schema so planning runs; collision on same TARGET dir
    sch = tmp_path / "s.yaml"
    sch.write_text("{}\n", encoding="utf-8")
    rc, out, err = run_cli([
        "generate",
        "s.yaml#/=out/",
        "s.yaml#/=out/",
    ], cwd=tmp_path)
    assert rc == 2
    assert "Output collision:" in err
