from __future__ import annotations

from teds_core.version import (
    check_spec_compat,
    recommended_minor_str,
    supported_spec_range_str,
)


def test_check_spec_compat_invalid():
    ok, reason = check_spec_compat("not-a-semver")
    assert ok is False and reason is not None


def test_supported_and_recommended_strings():
    s = supported_spec_range_str()
    r = recommended_minor_str()
    assert "." in s and "." in r
