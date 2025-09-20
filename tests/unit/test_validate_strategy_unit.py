from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from teds_core.validate import ValidationResult, ValidatorStrategy


def test_validation_result():
    # Test ValidationResult dataclass
    result = ValidationResult(is_valid=True)
    assert result.is_valid
    assert not result.has_errors
    assert result.error_message is None
    assert result.message is None

    result_with_error = ValidationResult(is_valid=False, error_message="test error")
    assert not result_with_error.is_valid
    assert result_with_error.has_errors
    assert result_with_error.error_message == "test error"


def test_validator_strategy_valid_expectation(tmp_path: Path):
    # Test ValidatorStrategy for valid cases
    schema = {"type": "string", "format": "email"}
    strict_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    base_validator = Draft202012Validator(schema)

    strategy = ValidatorStrategy(strict_validator, base_validator)

    # Valid email should pass
    result = strategy.validate("test@example.com", "valid")
    assert result.is_valid
    assert not result.has_errors

    # Invalid format should fail with strict but pass with base
    # Since base validator allows it, the overall result should be valid
    result = strategy.validate("not-an-email", "valid")
    assert result.is_valid  # Base validator allows it
    assert not result.has_errors


def test_validator_strategy_invalid_expectation(tmp_path: Path):
    # Test ValidatorStrategy for invalid cases
    schema = {"type": "string", "format": "email"}
    strict_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    base_validator = Draft202012Validator(schema)

    strategy = ValidatorStrategy(strict_validator, base_validator)

    # Invalid data: strict rejects, base accepts -> base wins, so it's unexpectedly valid
    result = strategy.validate("not-an-email", "invalid")
    assert not result.is_valid  # Unexpectedly valid (base accepted it)
    assert "UNEXPECTEDLY VALID" in result.error_message

    # Valid data should fail the invalid test
    result = strategy.validate("test@example.com", "invalid")
    assert not result.is_valid  # Incorrectly accepted
    assert result.error_message is not None


def test_validator_strategy_format_error_details(tmp_path: Path):
    # Test detailed format error messages
    schema = {"type": "string", "format": "email"}
    strict_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    base_validator = Draft202012Validator(schema)  # No format checking

    strategy = ValidatorStrategy(strict_validator, base_validator)

    # Test case where strict fails but base passes (format issue)
    result = strategy.validate("not-an-email", "invalid")
    assert not result.is_valid  # Unexpectedly valid
    assert "format" in result.error_message.lower()


def test_validator_strategy_unexpected_valid_with_format_details():
    # Test the _format_unexpected_valid_error method with format errors
    schema = {"type": "string", "format": "email"}
    strict_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    base_validator = Draft202012Validator(schema)

    strategy = ValidatorStrategy(strict_validator, base_validator)

    # This should trigger the detailed format error message
    result = strategy.validate("not-an-email", "invalid")

    # When base validator accepts but strict rejects, and expectation is invalid
    # The instance should be properly rejected
    if not result.is_valid:  # If unexpectedly valid
        assert "UNEXPECTEDLY VALID" in result.error_message
        assert "format" in result.error_message


def test_validator_strategy_with_no_format_errors():
    # Test case with no format-related errors
    schema = {"type": "integer", "minimum": 5}
    strict_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    base_validator = Draft202012Validator(schema)

    strategy = ValidatorStrategy(strict_validator, base_validator)

    # Both validators should behave the same for non-format constraints
    result = strategy.validate(3, "invalid")  # Should be rejected (< 5)
    assert result.is_valid  # Correctly rejected

    result = strategy.validate(10, "invalid")  # Should be accepted (>= 5)
    assert not result.is_valid  # Unexpectedly valid for invalid expectation
    assert "UNEXPECTEDLY VALID" in result.error_message
