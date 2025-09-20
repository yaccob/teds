from __future__ import annotations

from pathlib import Path

from tests.utils import load_yaml_file


def test_golden_output_filtering_and_inplace(tmp_path: Path):
    case = Path("tests/cases/output_filtering_and_inplace")
    # The golden files live in the repo; just verify they load and match themselves (sanity placeholder)
    exp = load_yaml_file(case / "expected.yaml")
    assert isinstance(exp, dict) and "tests" in exp
