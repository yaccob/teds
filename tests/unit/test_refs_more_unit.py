from __future__ import annotations

from pathlib import Path

import pytest

from teds_core.errors import NetworkError
from teds_core.refs import (
    NetworkConfiguration,
    _retrieve,
    _retrieve_with_config,
    build_validator_for_ref_with_config,
    jq_examples_prefix,
    jq_segment,
    set_network_policy,
    split_json_pointer,
)


def test_split_json_pointer_and_jq():
    assert split_json_pointer("/a/b") == ["a", "b"]
    assert split_json_pointer("/a~1b/~0c") == ["a/b", "~c"]
    assert jq_segment("ok") == ".ok"
    assert jq_segment("not-ok") == '.["not-ok"]'
    assert jq_examples_prefix("/components/schemas/A") == ".components.schemas.A"
    assert jq_examples_prefix("/") == ""


def test_retrieve_file_uri(tmp_path: Path):
    p = tmp_path / "x.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    res = _retrieve(p.as_uri())
    assert res.contents.get("a") == 1


def test_retrieve_unsupported_scheme():
    with pytest.raises(LookupError):
        _retrieve("ftp://example.com/x.yaml")


def test_retrieve_https_network_disabled():
    set_network_policy(False)
    with pytest.raises(NetworkError):
        _retrieve("https://example.com/schema.yaml")


def test_build_validator_for_ref_with_config(tmp_path: Path):
    # Test the build_validator_for_ref_with_config function
    schema = tmp_path / "test.yaml"
    schema.write_text("type: string\n", encoding="utf-8")

    config = NetworkConfiguration(allow_network=False)
    strict, base = build_validator_for_ref_with_config(tmp_path, "test.yaml", config)

    # Both validators should be created successfully
    assert strict is not None
    assert base is not None
    assert hasattr(strict, "format_checker")
    assert not hasattr(base, "format_checker") or base.format_checker is None


def test_network_configuration_creation():
    # Test NetworkConfiguration creation and methods
    config = NetworkConfiguration()
    assert not config.allow_network
    assert config.timeout == 5.0
    assert config.max_bytes == 5242880

    # Test from_env class method
    config_env = NetworkConfiguration.from_env(allow_network=True)
    assert config_env.allow_network

    # Test update method
    updated = config.update(allow=True, timeout=10.0)
    assert updated.allow_network
    assert updated.timeout == 10.0
    assert updated.max_bytes == 5242880  # unchanged


def test_retrieve_with_config_network_disabled(tmp_path: Path):
    # Test _retrieve_with_config with network disabled
    config = NetworkConfiguration(allow_network=False)

    # File URI should work
    schema = tmp_path / "test.yaml"
    schema.write_text("key: value\n", encoding="utf-8")
    resource = _retrieve_with_config(schema.as_uri(), config)
    assert resource.contents.get("key") == "value"

    # HTTPS URI should fail
    with pytest.raises(NetworkError, match="network fetch disabled"):
        _retrieve_with_config("https://example.com/test.yaml", config)


def test_retrieve_with_config_unsupported_scheme():
    # Test unsupported scheme
    config = NetworkConfiguration(allow_network=True)
    with pytest.raises(LookupError, match="unsupported URI scheme"):
        _retrieve_with_config("ftp://example.com/test.yaml", config)
