from __future__ import annotations

import pytest

from teds_core.resources import read_text_resource


def test_read_text_resource_existing():
    txt = read_text_resource("template_map.yaml")
    assert isinstance(txt, str) and "templates:" in txt


def test_read_text_resource_missing():
    with pytest.raises(FileNotFoundError):
        read_text_resource("does_not_exist_12345.yaml")

