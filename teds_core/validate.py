from __future__ import annotations

import sys
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from .refs import build_validator_for_ref, collect_examples
from .version import (
    RECOMMENDED_TESTSPEC_VERSION,
    SUPPORTED_TESTSPEC_MAJOR,
    check_spec_compat,
    recommended_minor_str,
    supported_spec_range_str,
)
from .yamlio import yaml_dumper, yaml_loader


@dataclass
class ValidationResult:
    """Result of validating an instance against a schema."""

    is_valid: bool
    error_message: str | None = None
    message: str | None = None

    @property
    def has_errors(self) -> bool:
        return not self.is_valid


class ValidatorStrategy:
    """Strategy for validating instances with different policies."""

    def __init__(
        self,
        strict_validator: Draft202012Validator,
        base_validator: Draft202012Validator,
    ):
        self.strict_validator = strict_validator
        self.base_validator = base_validator

    def validate(self, instance: Any, expectation: str) -> ValidationResult:
        """Validate instance according to expectation (valid/invalid)."""
        strict_valid, strict_error = self._validate_with_validator(
            self.strict_validator, instance
        )

        if not strict_valid:
            base_valid, base_error = self._validate_with_validator(
                self.base_validator, instance
            )
            observed_valid = base_valid
            final_error = strict_error or base_error
        else:
            observed_valid = True
            final_error = None

        if expectation == "valid":
            return ValidationResult(
                is_valid=observed_valid,
                error_message=final_error if not observed_valid else None,
            )
        else:  # expectation == "invalid"
            is_rejected = not observed_valid
            if is_rejected:
                return ValidationResult(
                    is_valid=True,
                    message=final_error,  # Correctly rejected
                )
            else:
                # Provide detailed error for unexpectedly valid cases
                error_msg = self._format_unexpected_valid_error(
                    instance, strict_valid, strict_error
                )
                return ValidationResult(
                    is_valid=False,  # Should have been rejected but wasn't
                    error_message=error_msg,
                )

    def _validate_with_validator(
        self, validator: Draft202012Validator, instance: Any
    ) -> tuple[bool, str | None]:
        """Validate instance with a single validator."""
        try:
            validator.validate(instance)
            return True, None
        except JsonSchemaValidationError as e:
            return False, e.message

    def _format_unexpected_valid_error(
        self, instance: Any, strict_valid: bool, _strict_error: str | None
    ) -> str:
        """Format error message for unexpectedly valid instances."""
        if not strict_valid:
            # Get detailed format errors like the original implementation
            strict_errs = list(self.strict_validator.iter_errors(instance))
            fmts = sorted(
                {
                    e.schema.get("format")
                    for e in strict_errs
                    if getattr(e, "validator", None) == "format"
                }
            )
            fmts_str = f" (format: {', '.join(fmts)})" if fmts else ""
            err_lines = [
                "UNEXPECTEDLY VALID",
                f"A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired{fmts_str}.",
                _pattern_advice(),
            ]
            return "\n".join(err_lines)
        return "UNEXPECTEDLY VALID"


def _iter_cases(
    test_value: Any, key: str
) -> Generator[tuple[Any, str, bool, str, bool, list[str]], None, None]:
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
            yield (
                it.get("payload"),
                (it.get("description") or ""),
                bool(it.get("parse_payload", False)),
                k,
                bool(it.get("from_examples", False)),
                user_warns,
            )
        else:
            yield None, "", False, k, False, []


def _prepare_case(
    payload: Any, parse_flag: bool, case_key: str, desc: str
) -> tuple[Any, Any | None, Any | None, bool, str]:
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


# Legacy function - now uses ValidatorStrategy internally
def _validate_raw(
    validator: Draft202012Validator, instance: Any
) -> tuple[bool, str | None]:
    try:
        validator.validate(instance)
        return True, None
    except JsonSchemaValidationError as e:
        return False, e.message


def _assemble_output(
    desc: str,
    orig_payload: Any | None,
    payload_parsed: Any | None,
    emit_parse_flag: bool,
    result: str,
    error_msg: str | None,
    validation_msg: str | None,
) -> dict[str, Any]:
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
        out["message"] = validation_msg
    if payload_parsed is not None:
        out["payload_parsed"] = payload_parsed
    return out


def _pattern_advice() -> str:
    return "Consider enforcing the expected format by adding an explicit 'pattern' property to the schema."


def _add_warning_if_only_strict_fails(
    out_case: dict[str, Any],
    validator_strict: Draft202012Validator,
    validator_base: Draft202012Validator,
) -> None:
    if out_case.get("result") != "SUCCESS":
        return
    inst = out_case.get("payload_parsed", out_case.get("payload"))
    if inst is None:
        return
    strict_errs = list(validator_strict.iter_errors(inst))
    if not strict_errs or not any(
        getattr(e, "validator", None) == "format" for e in strict_errs
    ):
        return
    if any(True for _ in validator_base.iter_errors(inst)):
        return
    fmts = sorted(
        {
            e.schema.get("format")
            for e in strict_errs
            if getattr(e, "validator", None) == "format"
        }
    )
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
    """Evaluate a test case using validator strategy."""
    instance, orig_payload, payload_parsed, emit_pf, desc = _prepare_case(
        payload, parse_flag, case_key, desc
    )

    # Use new validator strategy
    validator_strategy = ValidatorStrategy(validator_strict, validator_base)
    validation_result = validator_strategy.validate(instance, expectation)

    if validation_result.is_valid:
        result = "SUCCESS"
        err_msg = None
        val_msg = validation_result.message
    else:
        result = "ERROR"
        err_msg = validation_result.error_message
        val_msg = validation_result.message

    out_case = _assemble_output(
        desc, orig_payload, payload_parsed, emit_pf, result, err_msg, val_msg
    )
    if user_warnings:
        out_case.setdefault("warnings", []).extend(user_warnings)
    return case_key, out_case, 1 if result == "ERROR" else 0


def _validate_testspec_against_schema(doc: dict[str, Any], _repo_root: Path) -> None:
    # Load schema via package resources for installed wheels, with repo-root fallback for dev.
    from .resources import read_text_resource

    schema_text = read_text_resource("spec_schema.yaml")
    schema = yaml_loader.load(schema_text) or {}
    Draft202012Validator(schema).validate(doc)


def _visible(level: str, result: str) -> bool:
    return (
        level == "all"
        or (level == "warning" and result in ("WARNING", "ERROR"))
        or (level == "error" and result == "ERROR")
    )


def _process_example_cases(
    examples: list[tuple[str, Any]],
    schema_ref: str,
    validator_strict: Draft202012Validator,
    validator_base: Draft202012Validator,
    output_level: str,
    in_place: bool,
) -> tuple[dict[str, Any], int]:
    """Process example cases for a schema reference."""
    cases_valid: dict[str, Any] = {}
    rc = 0

    for ex_key, ex_payload in examples:
        try:
            ck, oc, _ = _evaluate_case(
                ex_payload, "", False, ex_key, "valid", validator_strict, validator_base
            )
        except Exception as e:  # pragma: no cover start
            # Internal validation errors - difficult to trigger in controlled tests
            print(
                f"Validation failed while evaluating example case for ref: {schema_ref}\n  case: {ex_key}\n  error: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            rc = max(rc, 2)
            continue  # pragma: no cover stop
        oc["from_examples"] = True
        _add_warning_if_only_strict_fails(oc, validator_strict, validator_base)
        if oc.get("result") == "SUCCESS" and oc.get("warnings"):
            oc["result"] = "WARNING"
        if in_place or _visible(output_level, oc.get("result", "SUCCESS")):
            cases_valid[ck] = oc
        rc = max(rc, 1 if oc.get("result") == "ERROR" else 0)

    return cases_valid, rc


def _process_manual_cases(
    value: dict[str, Any],
    schema_ref: str,
    validator_strict: Draft202012Validator,
    validator_base: Draft202012Validator,
    output_level: str,
    in_place: bool,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Process manual test cases for a schema reference."""
    cases_valid: dict[str, Any] = {}
    cases_invalid: dict[str, Any] = {}
    rc = 0

    for expectation in ("valid", "invalid"):
        if isinstance(value, dict) and expectation in value:
            for (
                pl,
                desc,
                parse_flag,
                case_key,
                is_from_examples,
                user_warnings,
            ) in _iter_cases(value, expectation):
                if is_from_examples:
                    continue
                try:
                    ck, oc, _ = _evaluate_case(
                        pl,
                        desc,
                        parse_flag,
                        case_key,
                        expectation,
                        validator_strict,
                        validator_base,
                        user_warnings,
                    )
                except Exception as e:  # pragma: no cover start
                    # Internal validation errors - difficult to trigger in controlled tests
                    print(
                        f"Validation failed while evaluating case for ref: {schema_ref}\n  case: {case_key}\n  error: {type(e).__name__}: {e}",
                        file=sys.stderr,
                    )
                    rc = max(rc, 2)
                    continue  # pragma: no cover stop
                _add_warning_if_only_strict_fails(oc, validator_strict, validator_base)
                if oc.get("result") == "SUCCESS" and oc.get("warnings"):
                    oc["result"] = "WARNING"
                if in_place or _visible(output_level, oc.get("result", "SUCCESS")):
                    if expectation == "valid":
                        cases_valid[ck] = oc
                    else:
                        cases_invalid[ck] = oc
                rc = max(rc, 1 if oc.get("result") == "ERROR" else 0)

    return cases_valid, cases_invalid, rc


def _process_schema_ref(
    schema_ref: str,
    value: dict[str, Any],
    testspec_dir: Path,
    output_level: str,
    in_place: bool,
) -> tuple[dict[str, Any], int]:
    """Process a single schema reference and its test cases."""
    try:
        validator_strict, validator_base = build_validator_for_ref(
            testspec_dir, schema_ref
        )
    except Exception as e:
        print(
            f"Failed to build validator for ref: {schema_ref}\n  in: {testspec_dir}\n  error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return {}, 2

    try:
        examples = collect_examples(testspec_dir, schema_ref)
    except Exception as e:
        print(
            f"Failed to collect examples for ref: {schema_ref}\n  in: {testspec_dir}\n  error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return {}, 2

    # Process example cases
    cases_valid_from_examples, rc_examples = _process_example_cases(
        examples, schema_ref, validator_strict, validator_base, output_level, in_place
    )

    # Process manual cases
    cases_valid_manual, cases_invalid, rc_manual = _process_manual_cases(
        value, schema_ref, validator_strict, validator_base, output_level, in_place
    )

    # Merge valid cases
    cases_valid = {**cases_valid_from_examples, **cases_valid_manual}

    # Build output group
    out_group: dict = {}
    if cases_valid:
        out_group["valid"] = cases_valid
    if cases_invalid:
        out_group["invalid"] = cases_invalid

    return out_group, max(rc_examples, rc_manual)


def validate_doc(
    doc: dict[str, Any], testspec_dir: Path, output_level: str, in_place: bool = False
) -> tuple[dict[str, Any], int]:
    """Validate a testspec document against schemas."""
    tests = doc.get("tests") or {}
    rc = 0
    out_tests: dict = {}

    for schema_ref, value in tests.items():
        out_group, ref_rc = _process_schema_ref(
            schema_ref, value, testspec_dir, output_level, in_place
        )
        rc = max(rc, ref_rc)

        if out_group:
            out_tests[schema_ref] = out_group

    return out_tests, rc


def validate_file(testspec_path: Path, output_level: str, in_place: bool) -> int:
    try:
        doc = yaml_loader.load(testspec_path.read_text(encoding="utf-8")) or {}
    except Exception as e:  # pragma: no cover start
        # I/O errors - difficult to reproduce reliably in tests
        print(
            f"Failed to read testspec: {testspec_path}\n  error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 2  # pragma: no cover stop
    repo_root = Path(__file__).resolve().parents[1]
    try:
        _validate_testspec_against_schema(doc, repo_root)
    except JsonSchemaValidationError as e:
        path = "/" + "/".join(str(x) for x in e.path) if e.path else "/"
        print(
            f"Spec validation failed: {testspec_path}\n  at: tests{path}\n  error: {e.message}",
            file=sys.stderr,
        )
        return 2
    except Exception as e:  # pragma: no cover start
        # Schema validation errors - internal errors, hard to trigger
        print(
            f"Spec validation failed: {testspec_path}\n  error: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 2  # pragma: no cover stop
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
                    f"  supported: {supported_spec_range_str()} (recommended: {recommended_minor_str()})"
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

    result_doc = {"version": RECOMMENDED_TESTSPEC_VERSION, "tests": out_tests}
    if in_place:
        preserved = dict(doc) if isinstance(doc, dict) else {}
        preserved.setdefault("version", RECOMMENDED_TESTSPEC_VERSION)
        preserved["tests"] = out_tests
        with testspec_path.open("w", encoding="utf-8") as fh:
            yaml_dumper.dump(preserved, fh)
    else:
        yaml_dumper.dump(result_doc, sys.stdout)
    return rc
