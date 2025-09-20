from __future__ import annotations

from pathlib import Path

from tests.utils import run_cli


def test_demo_public_specs_verify_warning_level():
    demo_spec = Path("demo/public_specs.yaml")
    rc, _out, _err = run_cli(["verify", str(demo_spec), "--output-level", "warning"])
    assert rc == 1
