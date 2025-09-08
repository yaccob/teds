from __future__ import annotations

from pathlib import Path

from tests.test_cli import run_cli
from tests.utils import load_yaml_text


def test_demo_boundary_conditions():
    demo_spec = Path("demo/public_specs.yaml")
    rc, out, err = run_cli(["verify", str(demo_spec), "--output-level", "all"])
    # overall still has ERROR due to explicit invalids in other groups
    assert rc == 1
    doc = load_yaml_text(out)
    tests = (doc or {}).get("tests", {})

    ref_amt = "public_schemas.yaml#/components/schemas/CurrencyAmount"
    assert ref_amt in tests
    amt_group = tests[ref_amt]
    valid_amt = (amt_group or {}).get("valid", {})
    # zero and one boundaries should be SUCCESS
    assert any(k.endswith("zero boundary ok") and v.get("result") == "SUCCESS" for k, v in valid_amt.items())
    assert any(k.endswith("one boundary ok") and v.get("result") == "SUCCESS" for k, v in valid_amt.items())

    ref_arr = "public_schemas.yaml#/components/schemas/ArrayMinItems"
    assert ref_arr in tests
    arr_group = tests[ref_arr]
    valid_arr = (arr_group or {}).get("valid", {})
    invalid_arr = (arr_group or {}).get("invalid", {})
    # valid edges
    assert any(v.get("result") == "SUCCESS" for v in valid_arr.values())
    # invalid edges (empty, 4 items) should both be SUCCESS (schema rejects them as intended)
    assert sum(1 for v in invalid_arr.values() if v.get("result") == "SUCCESS") >= 2
