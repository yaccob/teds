from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from teds_core.errors import NetworkError
from teds_core.refs import NetworkConfiguration, _retrieve_with_config


class TestHttpRetrieve:
    """Test HTTP retrieval functionality with mocked network calls."""

    def test_http_timeout_error(self):
        """Test handling of HTTP timeout errors."""
        config = NetworkConfiguration(allow_network=True, timeout=1.0)

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timed out")

            with pytest.raises(NetworkError) as exc_info:
                _retrieve_with_config("http://example.com/schema.yaml", config)

            assert "failed to fetch http://example.com/schema.yaml" in str(
                exc_info.value
            )

    def test_http_url_error(self):
        """Test handling of HTTP URL errors."""
        config = NetworkConfiguration(allow_network=True, timeout=1.0)

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("Network unreachable")

            with pytest.raises(NetworkError) as exc_info:
                _retrieve_with_config("http://example.com/schema.yaml", config)

            assert "failed to fetch http://example.com/schema.yaml" in str(
                exc_info.value
            )

    def test_http_large_response_dos_protection(self):
        """Test DoS protection for large HTTP responses."""
        config = NetworkConfiguration(allow_network=True, max_bytes=100)

        # Mock response that returns chunks exceeding max_bytes
        mock_resp = MagicMock()
        mock_resp.read.side_effect = [
            b"x" * 50,  # First chunk: 50 bytes
            b"x" * 60,  # Second chunk: 60 bytes (total: 110 > 100)
        ]

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            with pytest.raises(NetworkError) as exc_info:
                _retrieve_with_config("http://example.com/schema.yaml", config)

            assert "resource too large (>100 bytes)" in str(exc_info.value)

    def test_http_successful_small_response(self):
        """Test successful HTTP response within size limits."""
        config = NetworkConfiguration(allow_network=True, max_bytes=1000)
        yaml_content = "type: object\nproperties: {}"

        mock_resp = MagicMock()
        mock_resp.read.side_effect = [
            yaml_content.encode("utf-8"),
            b"",
        ]  # End with empty chunk

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            resource = _retrieve_with_config("http://example.com/schema.yaml", config)

            # Should return a Resource with the YAML content parsed
            assert resource is not None
            mock_urlopen.assert_called_once_with(
                "http://example.com/schema.yaml", timeout=config.timeout
            )

    def test_http_chunked_response_within_limits(self):
        """Test HTTP response that arrives in multiple chunks within limits."""
        config = NetworkConfiguration(allow_network=True, max_bytes=1000)

        mock_resp = MagicMock()
        mock_resp.read.side_effect = [
            b"type: object\n",
            b"properties:\n",
            b"  name: {type: string}",
            b"",  # End marker
        ]

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            resource = _retrieve_with_config("http://example.com/schema.yaml", config)

            assert resource is not None

    def test_http_invalid_utf8_response(self):
        """Test handling of invalid UTF-8 in HTTP response."""
        config = NetworkConfiguration(allow_network=True, max_bytes=1000)

        mock_resp = MagicMock()
        # Invalid UTF-8 bytes
        mock_resp.read.side_effect = [b"\xff\xfe\x00\x00invalid", b""]

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            with pytest.raises(NetworkError) as exc_info:
                _retrieve_with_config("http://example.com/schema.yaml", config)

            assert "failed to fetch http://example.com/schema.yaml" in str(
                exc_info.value
            )

    def test_http_network_error_preserves_original_network_error(self):
        """Test that NetworkError exceptions are preserved, not wrapped."""
        config = NetworkConfiguration(allow_network=True, max_bytes=100)

        with patch("teds_core.refs.urlopen") as mock_urlopen:
            # Simulate the DoS protection raising NetworkError internally
            original_error = NetworkError("resource too large (>100 bytes): test")
            mock_urlopen.side_effect = original_error

            with pytest.raises(NetworkError) as exc_info:
                _retrieve_with_config("http://example.com/schema.yaml", config)

            # Should be the same exception, not wrapped
            assert exc_info.value is original_error
