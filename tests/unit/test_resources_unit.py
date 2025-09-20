from __future__ import annotations

from unittest.mock import patch

import pytest

from teds_core.resources import read_text_resource


def test_read_text_resource_existing():
    txt = read_text_resource("template_map.yaml")
    assert isinstance(txt, str) and "templates:" in txt


def test_read_text_resource_missing():
    with pytest.raises(FileNotFoundError):
        read_text_resource("does_not_exist_12345.yaml")


def test_read_text_resource_fallback_paths():
    # Test fallback to different paths when package resources fail
    with patch("teds_core.resources._res_files") as mock_res_files:
        # Mock package resources to fail
        mock_res_files.side_effect = FileNotFoundError("Package resource not found")

        with patch("pathlib.Path.exists") as mock_exists:
            # First path (site_root) doesn't exist, second path (repo_root) exists
            mock_exists.side_effect = [False, True]

            with patch("pathlib.Path.read_text") as mock_read_text:
                mock_read_text.return_value = "test content"

                result = read_text_resource("test.yaml")
                assert result == "test content"

                # Verify read_text was called on the second path
                assert mock_read_text.call_count == 1
