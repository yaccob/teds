from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap

from .errors import TedsError
from .refs import collect_examples, join_fragment, resolve_schema_node
from .yamlio import yaml_dumper, yaml_loader


def _ensure_group(group: Any) -> dict[str, Any]:
    group = {} if not isinstance(group, dict) else dict(group)
    group.setdefault("valid", None)
    group.setdefault("invalid", None)
    return group


def generate_from(parent_ref: str, testspec_path: Path) -> None:
    if testspec_path.exists():
        try:
            doc = yaml_loader.load(testspec_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            raise TedsError(
                f"Failed to read or create testspec: {testspec_path}\n  error: {type(e).__name__}: {e}"
            ) from e
    else:
        doc = {}
    tests = doc.get("tests")
    if not isinstance(tests, dict):
        tests = {}
        doc["tests"] = tests

    base_dir = testspec_path.parent
    try:
        parent_node, parent_frag = resolve_schema_node(base_dir, parent_ref)
    except Exception as e:
        raise TedsError(
            f"Failed to resolve parent schema ref: {parent_ref}\n  base_dir: {base_dir}\n  error: {type(e).__name__}: {e}"
        ) from e
    file_part, _, _ = parent_ref.partition("#")
    if not isinstance(parent_node, dict):
        try:
            with testspec_path.open("w", encoding="utf-8") as fh:
                yaml_dumper.dump(doc, fh)
        except Exception as e:
            raise TedsError(
                f"Failed to write testspec: {testspec_path}\n  error: {type(e).__name__}: {e}"
            ) from e
        return

    for child_key in parent_node:
        child_fragment = join_fragment(parent_frag, child_key)
        child_ref = f"{file_part}#/{child_fragment}"
        group = _ensure_group(tests.get(child_ref))
        tests[child_ref] = group

        ex_list = collect_examples(base_dir, child_ref)
        if ex_list:
            vm = group.get("valid")
            if not isinstance(vm, dict):
                vm = CommentedMap()
            elif not isinstance(vm, CommentedMap):
                vm = CommentedMap(vm)

            missing = [(ek, ep) for ek, ep in ex_list if ek not in vm]
            for ek, ep in reversed(missing):
                vm.insert(0, ek, {"payload": ep, "from_examples": True})

            group["valid"] = vm

    try:
        with testspec_path.open("w", encoding="utf-8") as fh:
            yaml_dumper.dump(doc, fh)
    except Exception as e:
        raise TedsError(
            f"Failed to write testspec: {testspec_path}\n  error: {type(e).__name__}: {e}"
        ) from e
