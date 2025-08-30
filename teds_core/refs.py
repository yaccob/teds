from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
import re
from urllib.parse import urlparse, unquote
from urllib.request import urlopen
import os

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .yamlio import yaml_loader


def build_validator_for_ref(base_dir: Path, ref_expr: str) -> tuple[Draft202012Validator, Draft202012Validator]:
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
    strict = Draft202012Validator(wrapper, registry=registry, format_checker=FormatChecker())
    return strict, base


def split_json_pointer(fragment: str) -> list[str]:
    frag = fragment.lstrip("/")
    if not frag:
        return []
    parts = frag.split("/")
    return [p.replace("~1", "/").replace("~0", "~") for p in parts]


def jq_segment(seg: str) -> str:
    return f".{seg}" if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", seg) else f".[\"{seg}\"]"


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


# Network policy (pauschal): default deny; overrides via CLI and env vars.
_ALLOW_NETWORK = False


def _env_float(name: str, default: float) -> float:
    try:
        v = os.getenv(name)
        return float(v) if v is not None else default
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        return int(v) if v is not None else default
    except Exception:
        return default


_NETWORK_TIMEOUT = _env_float("TEDS_NETWORK_TIMEOUT", 5.0)  # seconds
_MAX_BYTES = _env_int("TEDS_NETWORK_MAX_BYTES", 5 * 1024 * 1024)  # 5 MiB/resource


def set_network_policy(allow: bool, timeout: float | None = None, max_bytes: int | None = None) -> None:
    global _ALLOW_NETWORK, _NETWORK_TIMEOUT, _MAX_BYTES
    _ALLOW_NETWORK = bool(allow)
    if timeout is not None:
        _NETWORK_TIMEOUT = float(timeout)
    if max_bytes is not None:
        _MAX_BYTES = int(max_bytes)


def _retrieve(uri: str) -> Resource:
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        p = Path(unquote(parsed.path))
        return Resource.from_contents(
            yaml_loader.load(p.read_text(encoding="utf-8")) or {},
            default_specification=DRAFT202012,
        )
    if parsed.scheme in ("http", "https"):
        if not _ALLOW_NETWORK:
            raise LookupError("network fetch disabled; re-run with --allow-network")
        with urlopen(uri, timeout=_NETWORK_TIMEOUT) as resp:
            data = resp.read(_MAX_BYTES + 1)
        if len(data) > _MAX_BYTES:
            raise LookupError(f"resource too large (>{_MAX_BYTES} bytes): {uri}")
        text = data.decode("utf-8", errors="strict")
        return Resource.from_contents(
            yaml_loader.load(text) or {},
            default_specification=DRAFT202012,
        )
    raise LookupError(f"unsupported URI scheme: {parsed.scheme}")

