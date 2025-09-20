from __future__ import annotations

from teds_core.report import _compute_counts, _render_jinja_str


def test_compute_counts_edge_cases():
    # Test _compute_counts with edge cases

    # Empty doc
    result = _compute_counts({})
    assert result == {"success": 0, "warning": 0, "error": 0}

    # Doc with no tests
    result = _compute_counts({"version": "1.0.0"})
    assert result == {"success": 0, "warning": 0, "error": 0}

    # Tests with no groups
    result = _compute_counts({"tests": {}})
    assert result == {"success": 0, "warning": 0, "error": 0}

    # Tests with empty groups
    result = _compute_counts({"tests": {"ref1": {}}})
    assert result == {"success": 0, "warning": 0, "error": 0}

    # Tests with non-dict cases
    result = _compute_counts(
        {"tests": {"ref1": {"valid": "not a dict", "invalid": []}}}
    )
    assert result == {"success": 0, "warning": 0, "error": 0}

    # Tests with None cases
    result = _compute_counts({"tests": {"ref1": {"valid": {"case1": None}}}})
    assert result == {
        "success": 1,
        "warning": 0,
        "error": 0,
    }  # None defaults to SUCCESS

    # Tests with mixed results
    result = _compute_counts(
        {
            "tests": {
                "ref1": {
                    "valid": {
                        "case1": {"result": "SUCCESS"},
                        "case2": {"result": "WARNING"},
                        "case3": {"result": "ERROR"},
                    },
                    "invalid": {
                        "case4": {},  # Missing result defaults to SUCCESS
                        "case5": {"result": "ERROR"},
                    },
                }
            }
        }
    )
    assert result == {"success": 2, "warning": 1, "error": 2}


def test_render_jinja_str_basic():
    # Test basic jinja rendering
    template = "Hello {{name}}!"
    context = {"name": "World"}
    result = _render_jinja_str("test.txt", template, context)
    assert result == "Hello World!"


def test_render_jinja_str_html_autoescape():
    # Test HTML autoescaping
    template = "Hello {{name}}!"
    context = {"name": "<script>alert('xss')</script>"}
    result = _render_jinja_str("test.html", template, context)
    assert "&lt;script&gt;" in result  # Should be escaped
    assert "<script>" not in result


def test_render_jinja_str_no_autoescape():
    # Test no autoescaping for non-HTML files
    template = "Hello {{name}}!"
    context = {"name": "<b>bold</b>"}
    result = _render_jinja_str("test.md", template, context)
    assert result == "Hello <b>bold</b>!"  # Should not be escaped
