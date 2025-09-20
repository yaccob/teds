from __future__ import annotations

from pathlib import Path
from typing import Any

from teds_core.validate import _iter_cases, _visible, validate_doc, validate_file
from teds_core.yamlio import yaml_loader


def write_yaml(p: Path, data: dict[str, Any]) -> None:
    p.write_text(
        "\n".join(list((yaml_loader.dump(data) or "").splitlines())),
        encoding="utf-8",
    )


def test_validate_doc_format_divergence_warning(tmp_path: Path):
    # Schema with format 'uuid' and an example that is not a UUID
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    A:
      type: string
      format: uuid
      examples: ["not-a-uuid"]
""",
        encoding="utf-8",
    )
    doc = {
        "version": "1.0.0",
        "tests": {
            f"{schema}#/components/schemas/A": {
                # no manual cases; examples produce a WARNING due to format divergence
            }
        },
    }
    out, rc = validate_doc(doc, tmp_path, output_level="warning", in_place=False)
    assert rc == 0
    key = next(iter(out.keys()))
    case = next(iter(out[key]["valid"].values()))
    assert case["result"] == "WARNING"
    assert any(
        isinstance(w, dict) and w.get("code") == "format-divergence"
        for w in case.get("warnings", [])
    )


def test_validate_file_version_gates(tmp_path: Path):
    # Major mismatch
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
version: "2.0.0"
tests:
  dummy.yaml#/: {}
""",
        encoding="utf-8",
    )
    rc = validate_file(spec, output_level="warning", in_place=False)
    assert rc == 2

    # Newer minor
    spec.write_text(
        """
version: "1.99.0"
tests:
  dummy.yaml#/: {}
""",
        encoding="utf-8",
    )
    rc = validate_file(spec, output_level="warning", in_place=False)
    assert rc == 2


def test_validate_doc_error_case_and_filtering(tmp_path: Path):
    # Schema accepts only 'a'; create an invalid expectation that will be unexpectedly valid
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
components:
  schemas:
    OnlyA:
      type: string
      pattern: "^a$"
""",
        encoding="utf-8",
    )
    ref = f"{schema}#/components/schemas/OnlyA"
    doc = {
        "version": "1.0.0",
        "tests": {
            ref: {"invalid": {"a": {"payload": "a"}}, "valid": {"a": {"payload": "a"}}}
        },
    }
    # output-level=error should include only the ERROR case
    out, rc = validate_doc(doc, tmp_path, output_level="error", in_place=False)
    assert rc == 1
    grp = out[ref]
    assert "valid" not in grp or grp["valid"] == {}
    assert "invalid" in grp and len(grp["invalid"]) == 1
    only_case = next(iter(grp["invalid"].values()))
    assert only_case["result"] == "ERROR"


def test_validate_doc_invalid_success_and_valid_error(tmp_path: Path):
    # Schema integer; craft invalid expectation that actually fails (SUCCESS for invalid),
    # and a valid expectation that fails (ERROR for valid)
    schema = tmp_path / "schema.yaml"
    schema.write_text("components: {schemas: {I: {type: integer}}}\n", encoding="utf-8")
    ref = f"{schema}#/components/schemas/I"
    doc = {
        "version": "1.0.0",
        "tests": {
            ref: {
                "invalid": {
                    "str": {"payload": "x"}
                },  # invalid expectation succeeds (both validators fail)
                "valid": {"str": {"payload": "x"}},  # valid expectation errors
            }
        },
    }
    out, _rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
    grp = out[ref]
    assert grp["invalid"]["str"]["result"] == "SUCCESS"
    assert grp["invalid"]["str"].get("message")  # carries validator message
    assert grp["valid"]["str"]["result"] == "ERROR"


def test_validate_doc_add_warning_strict_errs_non_format_and_base_fails(tmp_path: Path):
    # Schema with type integer (non-format validator). Provide SUCCESS result so _add_warning... early-returns
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        "components: {schemas: {I: {type: integer, examples: [1]}}}\n", encoding="utf-8"
    )
    ref = f"{schema}#/components/schemas/I"
    doc = {"version": "1.0.0", "tests": {ref: {}}}
    out, _rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
    case = next(iter(out[ref]["valid"].values()))
    # remains SUCCESS (no warning), since no format-related divergence
    assert case.get("result") == "SUCCESS"


def test_validate_doc_iter_cases_scalar_key_parsed(tmp_path: Path):
    # Provide a scalar key under 'valid' so _iter_cases yields (payload None) and _prepare_case parses key
    schema = tmp_path / "schema.yaml"
    schema.write_text("components: {schemas: {I: {type: integer}}}\n", encoding="utf-8")
    ref = f"{schema}#/components/schemas/I"
    doc = {
        "version": "1.0.0",
        "tests": {ref: {"valid": {"1": None}}},
    }
    out, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
    assert rc == 0
    case = next(iter(out[ref]["valid"].values()))
    assert case.get("payload_parsed") == 1


def test_validate_file_in_place_writes(tmp_path: Path):
    # Simple schema and spec; -i should write back and preserve top-level version
    schema = tmp_path / "schema.yaml"
    schema.write_text("components: {schemas: {S: {type: integer}}}\n", encoding="utf-8")
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        f"""
version: "1.0.0"
tests:
  {schema}#/components/schemas/S:
    valid:
      case1:
        payload: 1
""",
        encoding="utf-8",
    )
    rc = validate_file(spec, output_level="all", in_place=True)
    assert rc == 0
    text = spec.read_text(encoding="utf-8")
    assert "version: 1.0.0" in text and "tests:" in text


def test_validate_doc_parse_payload_and_user_warning(tmp_path: Path):
    # Schema integer; provide a valid case with parse_payload True from a string
    schema = tmp_path / "schema.yaml"
    schema.write_text("components: {schemas: {I: {type: integer}}}\n", encoding="utf-8")
    ref = f"{schema}#/components/schemas/I"
    doc = {
        "version": "1.0.0",
        "tests": {
            ref: {
                "valid": {
                    "one": {"payload": "1", "parse_payload": True, "warnings": ["note"]}
                }
            }
        },
    }
    out, rc = validate_doc(doc, tmp_path, output_level="all", in_place=False)
    assert rc == 0
    case = next(iter(out[ref]["valid"].values()))
    assert case.get("parse_payload") is True
    assert case.get("payload_parsed") == 1
    # user warnings elevate SUCCESS to WARNING
    assert case.get("result") == "WARNING"


def test_validate_doc_collect_examples_failure(monkeypatch, tmp_path: Path):
    # Monkeypatch collect_examples to raise and ensure rc becomes 2
    from teds_core import validate as v

    def boom(*args, **kwargs):
        raise RuntimeError("collect failed")

    monkeypatch.setattr(v, "collect_examples", boom)
    schema = tmp_path / "s.yaml"
    schema.write_text("components: {schemas: {S: {type: integer}}}\n", encoding="utf-8")
    ref = f"{schema}#/components/schemas/S"
    doc = {"version": "1.0.0", "tests": {ref: {}}}
    _out, rc = v.validate_doc(doc, tmp_path, output_level="warning", in_place=False)
    assert rc == 2


def test_validate_doc_build_validator_failure(monkeypatch, tmp_path: Path):
    # Monkeypatch build_validator_for_ref to raise and ensure rc becomes 2
    from teds_core import validate as v

    def boom(*args, **kwargs):
        raise RuntimeError("validator failed")

    monkeypatch.setattr(v, "build_validator_for_ref", boom)
    schema = tmp_path / "s.yaml"
    schema.write_text("{}\n", encoding="utf-8")
    ref = f"{schema}#/"
    doc = {"version": "1.0.0", "tests": {ref: {}}}
    _out, rc = v.validate_doc(doc, tmp_path, output_level="warning", in_place=False)
    assert rc == 2


def test_validate_doc_unsupported_scheme_failure(tmp_path: Path):
    # Unsupported scheme should surface as rc=2 and continue
    doc = {
        "version": "1.0.0",
        "tests": {"http://example.com/schema.yaml#/:": {}},
    }
    _out, rc = validate_doc(doc, tmp_path, output_level="warning", in_place=False)
    assert rc == 2


def test_visible_function():
    # Test _visible helper function
    assert _visible("all", "SUCCESS")
    assert _visible("all", "WARNING")
    assert _visible("all", "ERROR")

    assert not _visible("warning", "SUCCESS")
    assert _visible("warning", "WARNING")
    assert _visible("warning", "ERROR")

    assert not _visible("error", "SUCCESS")
    assert not _visible("error", "WARNING")
    assert _visible("error", "ERROR")


def test_iter_cases_empty_and_edge_cases():
    # Test _iter_cases with various edge cases

    # Non-dict test_value
    cases = list(_iter_cases("not a dict", "valid"))
    assert len(cases) == 0

    # Empty dict
    cases = list(_iter_cases({}, "valid"))
    assert len(cases) == 0

    # Dict without the requested key
    cases = list(_iter_cases({"invalid": {}}, "valid"))
    assert len(cases) == 0

    # Non-dict group
    cases = list(_iter_cases({"valid": "not a dict"}, "valid"))
    assert len(cases) == 0

    # Dict with non-dict item
    test_data = {"valid": {"case1": "not a dict"}}
    cases = list(_iter_cases(test_data, "valid"))
    assert len(cases) == 1
    payload, desc, parse_flag, case_key, from_examples, warnings = cases[0]
    assert payload is None
    assert desc == ""
    assert not parse_flag
    assert case_key == "case1"
    assert not from_examples
    assert warnings == []


def test_iter_cases_with_warnings():
    # Test _iter_cases with various warning types
    test_data = {
        "valid": {
            "case1": {
                "payload": "test",
                "warnings": [
                    "string warning",
                    {"generated": "generated warning", "code": "test"},
                ],
            }
        }
    }

    cases = list(_iter_cases(test_data, "valid"))
    assert len(cases) == 1
    payload, _desc, _parse_flag, _case_key, _from_examples, warnings = cases[0]
    assert payload == "test"
    assert len(warnings) == 1  # Only string warnings are kept
    assert warnings[0] == "string warning"
