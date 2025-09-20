from __future__ import annotations

from pathlib import Path

from tests.utils import run_cli


def test_demo_boundary_conditions():
    demo_spec = Path("demo/public_specs.yaml")
    rc, _out, _err = run_cli(["verify", str(demo_spec), "--output-level", "all"])
    assert rc == 1
