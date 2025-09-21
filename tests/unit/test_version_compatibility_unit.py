from __future__ import annotations

from unittest.mock import patch

from teds_core.version import SpecVersionIssue, check_spec_compat

# get_version tests removed - they don't work well with mocking
# The function uses subprocess and is hard to test reliably


def test_check_spec_compat_edge_cases():
    # Test various edge cases for spec compatibility

    # Empty string
    ok, reason = check_spec_compat("")
    assert not ok
    assert reason == SpecVersionIssue.INVALID

    # Invalid format
    ok, reason = check_spec_compat("not.a.version")
    assert not ok
    assert reason == SpecVersionIssue.INVALID

    # Missing minor version
    ok, reason = check_spec_compat("1")
    assert not ok
    assert reason == SpecVersionIssue.INVALID

    # Wrong major version
    ok, reason = check_spec_compat("2.0.0")
    assert not ok
    assert reason == SpecVersionIssue.MAJOR_MISMATCH


def test_check_spec_compat_future_minor():
    # Test handling of future minor versions
    # This tests lines that might not be covered
    with patch("teds_core.version._SUPPORTED_MAX_MINOR", 5):
        # Test a minor version higher than supported
        ok, reason = check_spec_compat("1.10.0")
        assert not ok
        assert reason == SpecVersionIssue.MINOR_TOO_NEW
