from __future__ import annotations

from pathlib import Path

from tests.test_cli import run_cli
from tests.utils import load_yaml_text


def test_demo_public_specs_verify_warning_level():
    demo_spec = Path("demo/public_specs.yaml")
    assert demo_spec.exists(), "demo/public_specs.yaml missing"

    rc, out, err = run_cli(["verify", str(demo_spec), "--output-level", "warning"])
    # Expect ERROR cases present due to explicit invalids
    assert rc == 1
    doc = load_yaml_text(out)
    tests = (doc or {}).get("tests", {})
    # Check EmailContact ref exists
    ref_email = "public_schemas.yaml#/components/schemas/EmailContact"
    assert ref_email in tests
    email_group = tests[ref_email]
    # Expect the warning case (valid group)
    valid_cases = (email_group or {}).get("valid", {})
    assert any(v.get("result") == "WARNING" for v in valid_cases.values())

    # EmailContact should have at least one explicit invalid case reported as ERROR
    invalid_email = (email_group or {}).get("invalid", {})
    assert any(c.get("result") == "ERROR" for c in invalid_email.values())
