from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .errors import NetworkError
from .yamlio import yaml_loader

# Constants
DEFAULT_NETWORK_TIMEOUT = 5.0  # seconds
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB per resource
SCHEMA_CACHE_SIZE = 128  # LRU cache size for schema resolution


def build_validator_for_ref(
    base_dir: Path, ref_expr: str
) -> tuple[Draft202012Validator, Draft202012Validator]:
    """Build validators for a schema reference."""
    file_part, _, frag = ref_expr.partition("#")
    schema_path = (base_dir / file_part).resolve()
    base_uri = schema_path.as_uri()
    target_ref = base_uri if not frag else f"{base_uri}#/{frag.lstrip('/')}"

    root_doc = yaml_loader.load(schema_path.read_text(encoding="utf-8")) or {}

    registry = Registry(retrieve=_retrieve).with_resource(
        base_uri,
        Resource.from_contents(root_doc, default_specification=DRAFT202012),
    )

    wrapper = {"$ref": target_ref}
    base = Draft202012Validator(wrapper, registry=registry)
    strict = Draft202012Validator(
        wrapper, registry=registry, format_checker=FormatChecker()
    )
    return strict, base


def build_validator_for_ref_with_config(
    base_dir: Path, ref_expr: str, network_config: NetworkConfiguration
) -> tuple[Draft202012Validator, Draft202012Validator]:
    """Build validators with specific network configuration."""
    file_part, _, frag = ref_expr.partition("#")
    schema_path = (base_dir / file_part).resolve()
    base_uri = schema_path.as_uri()
    target_ref = base_uri if not frag else f"{base_uri}#/{frag.lstrip('/')}"

    root_doc = yaml_loader.load(schema_path.read_text(encoding="utf-8")) or {}

    # Use specific retrieve function with config
    def retrieve_func(uri: str) -> Resource:
        return _retrieve_with_config(uri, network_config)

    registry = Registry(retrieve=retrieve_func).with_resource(
        base_uri,
        Resource.from_contents(root_doc, default_specification=DRAFT202012),
    )

    wrapper = {"$ref": target_ref}
    base = Draft202012Validator(wrapper, registry=registry)
    strict = Draft202012Validator(
        wrapper, registry=registry, format_checker=FormatChecker()
    )
    return strict, base


def split_json_pointer(fragment: str) -> list[str]:
    frag = fragment.lstrip("/")
    if not frag:
        return []
    parts = frag.split("/")
    return [p.replace("~1", "/").replace("~0", "~") for p in parts]


def jq_segment(seg: str) -> str:
    return f".{seg}" if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", seg) else f'.["{seg}"]'


def jq_examples_prefix(fragment: str) -> str:
    segs = split_json_pointer(fragment)
    if not segs:
        return ""
    return "".join(jq_segment(s) for s in segs)


def resolve_schema_node(base_dir: Path, ref_expr: str) -> tuple[Any, str]:
    file_part, _, frag = ref_expr.partition("#")
    schema_path = (base_dir / file_part).resolve()
    doc = yaml_loader.load(schema_path.read_text(encoding="utf-8")) or {}
    node: Any = doc
    fragment = frag.lstrip("/")
    for k in split_json_pointer(frag):
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            node = None
            break
    return node, fragment


def collect_examples(base_dir: Path, ref_expr: str) -> list[tuple[str, Any]]:
    node, fragment = resolve_schema_node(base_dir, ref_expr)
    if not isinstance(node, dict):
        return []
    ex = node.get("examples")
    if not isinstance(ex, list):
        return []
    prefix = jq_examples_prefix(fragment)
    base = f"{prefix}.examples" if prefix else ".examples"
    out: list[tuple[str, Any]] = []
    for i, item in enumerate(ex):
        out.append((f"{base}[{i}]", item))
    return out


def join_fragment(parent_fragment: str, child: str) -> str:
    parent_fragment = parent_fragment.strip("/")
    return child if not parent_fragment else f"{parent_fragment}/{child}"


@dataclass
class NetworkConfiguration:
    """Configuration for network operations."""

    allow_network: bool = False
    timeout: float = DEFAULT_NETWORK_TIMEOUT
    max_bytes: int = DEFAULT_MAX_BYTES

    @classmethod
    def from_env(cls, allow_network: bool = False) -> NetworkConfiguration:
        """Create configuration from environment variables."""
        return cls(
            allow_network=allow_network,
            timeout=_env_float("TEDS_NETWORK_TIMEOUT", DEFAULT_NETWORK_TIMEOUT),
            max_bytes=_env_int("TEDS_NETWORK_MAX_BYTES", DEFAULT_MAX_BYTES),
        )

    def update(
        self,
        allow: bool | None = None,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> NetworkConfiguration:
        """Create updated configuration with new values."""
        return NetworkConfiguration(
            allow_network=allow if allow is not None else self.allow_network,
            timeout=timeout if timeout is not None else self.timeout,
            max_bytes=max_bytes if max_bytes is not None else self.max_bytes,
        )


def _env_float(name: str, default: float) -> float:
    """Get float value from environment variable with fallback."""
    try:
        v = os.getenv(name)
        return float(v) if v is not None else default
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    """Get int value from environment variable with fallback."""
    try:
        v = os.getenv(name)
        return int(v) if v is not None else default
    except Exception:
        return default


# Global default configuration - can be overridden via dependency injection
_default_network_config = NetworkConfiguration.from_env()


def set_network_policy(
    allow: bool, timeout: float | None = None, max_bytes: int | None = None
) -> None:
    """Update global network policy (legacy compatibility)."""
    global _default_network_config
    _default_network_config = _default_network_config.update(allow, timeout, max_bytes)


def _retrieve_with_config(uri: str, config: NetworkConfiguration) -> Resource:
    """Retrieve resource with specific network configuration."""
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        p = Path(unquote(parsed.path))
        return Resource.from_contents(
            yaml_loader.load(p.read_text(encoding="utf-8")) or {},
            default_specification=DRAFT202012,
        )
    if parsed.scheme in ("http", "https"):
        if not config.allow_network:
            raise NetworkError("network fetch disabled; re-run with --allow-network")
        try:
            with urlopen(uri, timeout=config.timeout) as resp:
                # Fix DoS vulnerability: use proper streaming
                data = bytearray()
                while len(data) <= config.max_bytes:
                    chunk = resp.read(min(8192, config.max_bytes - len(data) + 1))
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > config.max_bytes:
                        raise NetworkError(
                            f"resource too large (>{config.max_bytes} bytes): {uri}"
                        )

            text = bytes(data).decode("utf-8", errors="strict")
        except Exception as e:
            if isinstance(e, NetworkError):
                raise
            raise NetworkError(f"failed to fetch {uri}: {e}") from e
        return Resource.from_contents(
            yaml_loader.load(text) or {},
            default_specification=DRAFT202012,
        )
    raise LookupError(f"unsupported URI scheme: {parsed.scheme}")


def _retrieve(uri: str) -> Resource:
    """Retrieve resource using global configuration (legacy compatibility)."""
    return _retrieve_with_config(uri, _default_network_config)
