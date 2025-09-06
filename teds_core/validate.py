from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Optional, Generator

from jsonschema import Draft202012Validator, ValidationError

from .yamlio import yaml_loader, yaml_dumper
from .refs import build_validator_for_ref, collect_examples
from .version import (
    SUPPORTED_TESTSPEC_VERSION,
    SUPPORTED_TESTSPEC_MAJOR,
    SUPPORTED_TESTSPEC_MINOR,
    supported_spec_range_str,
    check_spec_compat,
)


def _iter_cases(test_value: Any, key: str) -> Generator[tuple[Any, str, bool, str, bool, list[str]], None, None]:
    items: Any = {}
    if isinstance(test_value, dict):
        group = test_value.get(key)
        if isinstance(group, dict):
            items = group
    if not isinstance(items, dict):
        items = {}
    for k, it in items.items():
        if isinstance(it, dict):
            warnings_raw = it.get("warnings")
            user_warns: list[str] = []
            if isinstance(warnings_raw, list):
                for w in warnings_raw:
                    if isinstance(w, str):
                        user_warns.append(w)
                    elif isinstance(w, dict) and "generated" in w:
                        pass
            yield it.get("payload"), (it.get("description") or ""), bool(it.get("parse_payload", False)), k, bool(it.get("from_examples", False)), user_warns
        else:
            yield None, "", False, k, False, []


def _prepare_case(payload: Any, parse_flag: bool, case_key: str, desc: str) -> tuple[Any, Any | None, Any | None, bool, str]:
    if payload is None:
        instance = yaml_loader.load(case_key)
        orig_payload = None
        payload_parsed = instance
        emit_parse_flag = False
    else:
        if parse_flag and isinstance(payload, str):
            instance = yaml_loader.load(payload)
            orig_payload = payload
            payload_parsed = instance
            emit_parse_flag = True
        else:
            instance = payload
            orig_payload = payload
            payload_parsed = None
            emit_parse_flag = False
    return instance, orig_payload, payload_parsed, emit_parse_flag, desc


def _validate_raw(validator: Draft202012Validator, instance: Any) -> tuple[bool, str | None]:
    try:
        validator.validate(instance)
        return True, None
    except ValidationError as e:
        return False, e.message


def _assemble_output(desc: str,
                    orig_payload: Any | None,
                    payload_parsed: Any | None,
                    emit_parse_flag: bool,
                    result: str,
                    error_msg: str | None,
                    validation_msg: str | None) -> dict[str, Any]:
    out = {}
    if desc:
        out["description"] = desc
    if orig_payload is not None:
        out["payload"] = orig_payload
    if emit_parse_flag:
        out["parse_payload"] = True
    out["result"] = result
    if error_msg is not None:
        out["message"] = error_msg
    elif validation_msg is not None:
        out["validation_message"] = validation_msg
    if payload_parsed is not None:
        out["payload_parsed"] = payload_parsed
    return out


def _pattern_advice() -> str:
    return "Consider enforcing the expected format by adding an explicit 'pattern' property to the schema."


def _add_warning_if_only_strict_fails(out_case: dict[str, Any], validator_strict: Draft202012Validator, validator_base: Draft202012Validator) -> None:
    if out_case.get("result") != "SUCCESS":
        return
    inst = out_case.get("payload_parsed", out_case.get("payload"))
    if inst is None:
        return
    strict_errs = list(validator_strict.iter_errors(inst))
    if not strict_errs or not any(getattr(e, "validator", None) == "format" for e in strict_errs):
        return
    if any(True for _ in validator_base.iter_errors(inst)):
        return
    fmts = sorted({e.schema.get("format") for e in strict_errs if getattr(e, "validator", None) == "format"})
    fmts_str = f" (format: {', '.join(fmts)})" if fmts else ""
    lines = [
        f"Relies on JSON Schema 'format' assertion{fmts_str}.",
        "Validators that *enforce* 'format' will reject this instance.",
        _pattern_advice(),
        "",
    ]
    msg = "\n".join(lines)
    gen_entry = {"generated": msg, "code": "format-divergence"}
    out_case.setdefault("warnings", []).append(gen_entry)


def _evaluate_case(
    payload: Any,
    desc: str,
    parse_flag: bool,
    case_key: str,
    expectation: str,
    validator_strict: Draft202012Validator,
    validator_base: Draft202012Validator,
    user_warnings: list[str] | None = None,
) -> tuple[str, dict[str, Any], int]:
    instance, orig_payload, payload_parsed, emit_pf, desc = _prepare_case(payload, parse_flag, case_key, desc)
    ok_strict, err_strict = _validate_raw(validator_strict, instance)
    ok_base, err_base = (True, None)
    if not ok_strict:
        ok_base, err_base = _validate_raw(validator_base, instance)

    observed_ok = ok_strict or ok_base

    if expectation == "valid":
        result = "SUCCESS" if observed_ok else "ERROR"
        err_msg = (err_strict or err_base) if result == "ERROR" else None
        val_msg = None
    else:  # expectation == "invalid"
        final_ok = not observed_ok
        result = "SUCCESS" if final_ok else "ERROR"
        if final_ok:
            err_msg = None
            val_msg = err_strict or err_base
        else:
            err_msg = "UNEXPECTEDLY VALID"
            val_msg = None
            if (not ok_strict) and ok_base:
                strict_errs = list(validator_strict.iter_errors(instance))
                fmts = sorted({e.schema.get("format") for e in strict_errs if getattr(e, "validator", None) == "format"})
                fmts_str = f" (format: {', '.join(fmts)})" if fmts else ""
                err_lines = [
                    "UNEXPECTEDLY VALID",
                    f"A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired{fmts_str}.",
                    _pattern_advice(),
                    "",
                ]
                err_msg = "\n".join(err_lines)

    out_case = _assemble_output(desc, orig_payload, payload_parsed, emit_pf, result, err_msg, val_msg)
    if user_warnings:
        out_case.setdefault("warnings", []).extend(user_warnings)
    return case_key, out_case, 1 if result == "ERROR" else 0


def _validate_testspec_against_schema(doc: dict[str, Any], repo_root: Path) -> None:
    schema_path = (repo_root / "spec_schema.yaml").resolve()
    schema = yaml_loader.load(schema_path.read_text(encoding="utf-8")) or {}
    Draft202012Validator(schema).validate(doc)


def _visible(level: str, result: str) -> bool:
    return (
        level == "all"
        or (level == "warning" and result in ("WARNING", "ERROR"))
        or (level == "error" and result == "ERROR")
    )


def validate_doc(doc: dict[str, Any], testspec_dir: Path, output_level: str, in_place: bool = False) -> tuple[dict[str, Any], int]:
    tests = doc.get("tests") or {}
    rc = 0
    out_tests: dict = {}

    for schema_ref, value in tests.items():
        try:
            validator_strict, validator_base = build_validator_for_ref(testspec_dir, schema_ref)
        except Exception as e:
            print(
                f"Failed to build validator for ref: {schema_ref}\n  in: {testspec_dir}\n  error: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            rc = max(rc, 2)
            continue
        out_group: dict = {}
        cases_valid: dict[str, Any] = {}
        cases_invalid: dict[str, Any] = {}

        try:
            examples = collect_examples(testspec_dir, schema_ref)
        except Exception as e:
            print(
                f"Failed to collect examples for ref: {schema_ref}\n  in: {testspec_dir}\n  error: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            rc = max(rc, 2)
            continue

        for ex_key, ex_payload in examples:
            try:
                ck, oc, _ = _evaluate_case(ex_payload, "", False, ex_key, "valid", validator_strict, validator_base)
            except Exception as e:
                print(
                    f"Validation failed while evaluating example case for ref: {schema_ref}\n  case: {ex_key}\n  error: {type(e).__name__}: {e}",
                    file=sys.stderr,
                )
                rc = max(rc, 2)
                continue
            oc["from_examples"] = True
            _add_warning_if_only_strict_fails(oc, validator_strict, validator_base)
            if oc.get("result") == "SUCCESS" and oc.get("warnings"):
                oc["result"] = "WARNING"
            if in_place or _visible(output_level, oc.get("result", "SUCCESS")):
                cases_valid[ck] = oc
            rc = max(rc, 1 if oc.get("result") == "ERROR" else 0)

        for expectation in ("valid", "invalid"):
            if isinstance(value, dict) and expectation in value:
                for pl, desc, parse_flag, case_key, is_from_examples, user_warnings in _iter_cases(value, expectation):
                    if is_from_examples:
                        continue
                    try:
                        ck, oc, _ = _evaluate_case(pl, desc, parse_flag, case_key, expectation, validator_strict, validator_base, user_warnings)
                    except Exception as e:
                        print(
                            f"Validation failed while evaluating case for ref: {schema_ref}\n  case: {case_key}\n  error: {type(e).__name__}: {e}",
                            file=sys.stderr,
                        )
                        rc = max(rc, 2)
                        continue
                    _add_warning_if_only_strict_fails(oc, validator_strict, validator_base)
                    if oc.get("result") == "SUCCESS" and oc.get("warnings"):
                        oc["result"] = "WARNING"
                    if in_place or _visible(output_level, oc.get("result", "SUCCESS")):
                        if expectation == "valid":
                            cases_valid[ck] = oc
                        else:
                            cases_invalid[ck] = oc
                    rc = max(rc, 1 if oc.get("result") == "ERROR" else 0)

        if cases_valid:
            out_group["valid"] = cases_valid
        if cases_invalid:
            out_group["invalid"] = cases_invalid
        if out_group:
            out_tests[schema_ref] = out_group

    return out_tests, rc


def validate_file(testspec_path: Path, output_level: str, in_place: bool) -> int:
    try:
        doc = yaml_loader.load(testspec_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(
            f"Failed to read testspec: {testspec_path}\n  error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 2
    repo_root = Path(__file__).resolve().parents[1]
    try:
        _validate_testspec_against_schema(doc, repo_root)
    except ValidationError as e:
        path = "/" + "/".join(str(x) for x in e.path) if e.path else "/"
        print(
            f"Spec validation failed: {testspec_path}\n  at: tests{path}\n  error: {e.message}",
            file=sys.stderr,
        )
        return 2
    except Exception as e:
        print(
            f"Spec validation failed: {testspec_path}\n  error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 2
    ver = str(doc.get("version", "")).strip()
    ok, reason = check_spec_compat(ver)
    if not ok:
        from .version import SpecVersionIssue
        if reason == SpecVersionIssue.INVALID:
            print(
                f"Spec version invalid: {testspec_path}\n  value: {ver or '<missing>'}",
                file=sys.stderr,
            )
        elif reason == SpecVersionIssue.MAJOR_MISMATCH:
            print(
                f"Unsupported testspec version: {ver}\n  supported major: {SUPPORTED_TESTSPEC_MAJOR}",
                file=sys.stderr,
            )
        elif reason == SpecVersionIssue.MINOR_TOO_NEW:
            print(
                (
                    f"Newer testspec minor not supported: {ver}\n"
                    f"  supported up to: {supported_spec_range_str()}"
                ),
                file=sys.stderr,
            )
        else:
            print(f"Unsupported testspec version: {ver}", file=sys.stderr)
        return 2

    out_tests, rc = validate_doc(
        doc,
        testspec_path.parent,
        output_level=output_level,
        in_place=in_place,
    )

    result_doc = {"tests": out_tests}
    if in_place:
        preserved = dict(doc) if isinstance(doc, dict) else {}
        preserved["tests"] = out_tests
        with testspec_path.open("w", encoding="utf-8") as fh:
            yaml_dumper.dump(preserved, fh)
    else:
        yaml_dumper.dump(result_doc, sys.stdout)
    return rc

