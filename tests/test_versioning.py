from __future__ import annotations

from pathlib import Path
import re

from tests.test_cli import run_cli


def test_cli_version_prints_semver_and_spec_range():
    rc, out, err = run_cli(["--version"])
    assert rc == 0
    assert err == ""
    # teds <semver> (spec supported: 1.0–1.N; recommended: 1.N)
    assert out.startswith("teds ")
    assert "(spec supported: " in out and "; recommended: " in out, out


def test_in_place_rejects_mismatched_major(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
version: "2.0.0"
tests:
  dummy.yaml#/: {}
        """,
        encoding="utf-8",
    )
    before = spec.read_text(encoding="utf-8")
    rc, out, err = run_cli(["verify", "spec.yaml", "-i"], cwd=tmp_path)
    assert rc == 2
    assert out == ""
    assert "Unsupported testspec version:" in err
    # file unchanged
    after = spec.read_text(encoding="utf-8")
    assert after == before


def test_rejects_newer_minor(tmp_path: Path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
version: "1.99.0"
tests:
  dummy.yaml#/: {}
        """,
        encoding="utf-8",
    )
    rc, out, err = run_cli(["verify", "spec.yaml"], cwd=tmp_path)
    assert rc == 2
    assert out == ""
    assert "Newer testspec minor not supported" in err
