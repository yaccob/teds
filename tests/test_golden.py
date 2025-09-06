from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Iterable
import shutil

from tests.utils import load_yaml_file
import teds


CASES_DIR = Path(__file__).parent / "cases"


def _compute_rc(tests_obj: Dict[str, Any]) -> int:
    # Return 1 if any case has result == ERROR, else 0
    for _ref, group in (tests_obj or {}).items():
        for sect in ("valid", "invalid"):
            cases = (group or {}).get(sect)
            if isinstance(cases, dict):
                for _name, case in cases.items():
                    if case.get("result") == "ERROR":
                        return 1
    return 0


def _iter_cases() -> Iterable[Path]:
    if not CASES_DIR.exists():
        return []
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir())


def test_golden_warning_level(tmp_path: Path):
    for case_dir in _iter_cases():
        spec = case_dir / "spec.yaml"
        expected = case_dir / "expected.yaml"
        assert spec.exists() and expected.exists(), f"Missing files in {case_dir}"

        doc = load_yaml_file(spec)
        out_tests, rc = teds.validate_doc(doc, case_dir, output_level="warning", in_place=False)
        result_doc = {"tests": out_tests}

        expected_doc = load_yaml_file(expected)
        assert result_doc == expected_doc, f"Mismatch in {case_dir} (warning)"
        assert rc == _compute_rc(expected_doc.get("tests")), f"RC mismatch in {case_dir} (warning)"


def test_golden_error_level(tmp_path: Path):
    for case_dir in _iter_cases():
        spec = case_dir / "spec.yaml"
        expected_err = case_dir / "expected.error.yaml"
        if not expected_err.exists():
            continue

        doc = load_yaml_file(spec)
        out_tests, rc = teds.validate_doc(doc, case_dir, output_level="error", in_place=False)
        result_doc = {"tests": out_tests}

        expected_doc = load_yaml_file(expected_err)
        assert result_doc == expected_doc, f"Mismatch in {case_dir} (error)"
        assert rc == _compute_rc(expected_doc.get("tests")), f"RC mismatch in {case_dir} (error)"


def test_golden_in_place(tmp_path: Path):
    for case_dir in _iter_cases():
        spec_src = case_dir / "spec.yaml"
        expected_ip = case_dir / "expected.in_place.yaml"
        if not expected_ip.exists():
            continue

        workdir = tmp_path / case_dir.name
        shutil.copytree(case_dir, workdir)
        spec = workdir / "spec.yaml"

        rc = teds.validate_file(spec, output_level="warning", in_place=True)
        result_doc = load_yaml_file(spec)

        expected_doc = load_yaml_file(expected_ip)
        assert result_doc == expected_doc, f"Mismatch in {case_dir} (in_place)"
        assert rc == _compute_rc(expected_doc.get("tests")), f"RC mismatch in {case_dir} (in_place)"
