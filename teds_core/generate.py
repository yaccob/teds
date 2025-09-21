from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import jsonpath_ng
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


def parse_generate_config(config_str: str) -> dict[str, dict[str, Any]] | str:
    """Parse generate configuration from YAML string or file reference.

    Returns:
        - dict: Source-centric configuration {source_file: config}
        - str: JSON Pointer string for backward compatibility
    """
    # Handle @filename syntax
    if config_str.startswith("@"):
        config_file = Path(config_str[1:])
        if not config_file.exists():
            raise TedsError(f"Configuration file not found: {config_file}")
        try:
            config_str = config_file.read_text(encoding="utf-8")
        except Exception as e:
            raise TedsError(
                f"Failed to read configuration file {config_file}: {e}"
            ) from e

    # Parse YAML
    try:
        parsed = yaml_loader.load(config_str)
    except Exception as e:
        raise TedsError(f"Invalid YAML configuration: {e}") from e

    # Check result type
    if isinstance(parsed, dict):
        # Source-centric YAML object format
        normalized_config = {}

        for source_file, config in parsed.items():
            if isinstance(config, list):
                # Simple format: {"source.yaml": ["path1", "path2"]}
                normalized_config[source_file] = {
                    "paths": config,
                    "target": None,  # Will use default
                }
            elif isinstance(config, dict):
                # Explicit format: {"source.yaml": {"paths": [...], "target": "..."}}
                if "paths" not in config:
                    raise TedsError(f"Source '{source_file}': missing 'paths' field")
                if not isinstance(config["paths"], list):
                    raise TedsError(f"Source '{source_file}': 'paths' must be a list")

                normalized_config[source_file] = {
                    "paths": config["paths"],
                    "target": config.get("target"),
                }
            else:
                raise TedsError(
                    f"Source '{source_file}': config must be list or object, got {type(config).__name__}"
                )

            # Validate all paths are strings
            for path in normalized_config[source_file]["paths"]:
                if not isinstance(path, str):
                    raise TedsError(
                        f"Source '{source_file}': path must be string, got {type(path).__name__}"
                    )

        return normalized_config
    elif isinstance(parsed, str):
        # Backward compatibility: JSON Pointer string
        return parsed
    else:
        raise TedsError(
            f"Configuration must be object or string, got {type(parsed).__name__}"
        )


def validate_jsonpath_expression(expr: str) -> None:
    """Validate a JsonPath expression for basic syntax."""
    # Handle backward compatibility: JSON Pointer format (with #)
    if "#" in expr:
        file_part, fragment = expr.split("#", 1)
        if not file_part:
            raise TedsError(f"Missing schema file path: {expr}")

        # Convert to JsonPath for validation
        if fragment.startswith("/"):
            fragment = fragment[1:]  # Remove leading slash
        if not fragment:
            return  # Root reference is valid

        # Check for basic syntax errors in JSON Pointer format
        invalid_patterns = [
            r"\.\./",  # Parent navigation (not supported)
        ]
        for pattern in invalid_patterns:
            if re.search(pattern, fragment):
                raise TedsError(f"Invalid JSON Pointer expression: {expr}")
        return

    # Pure JsonPath expression validation
    if not expr:
        raise TedsError("Empty JsonPath expression")

    # Basic JsonPath validation - must start with $ for root
    if not expr.startswith("$"):
        raise TedsError(f"JsonPath expression must start with '$': {expr}")

    # Check for basic syntax errors
    invalid_patterns = [
        r"\[([^]]+$)",  # Unclosed bracket
        r"\.\./",  # Parent navigation (not supported)
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, expr):
            raise TedsError(f"Invalid JsonPath expression: {expr}")


def expand_jsonpath_expressions(source_file: Path, expressions: list[str]) -> list[str]:
    """Expand JsonPath expressions with wildcards to concrete JSON Pointer references."""
    expanded = []

    # Load schema document once
    try:
        schema_doc = yaml_loader.load(source_file.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise TedsError(f"Failed to load schema {source_file}: {e}") from e

    for expr in expressions:
        validate_jsonpath_expression(expr)

        # Handle backward compatibility: JSON Pointer format
        if "#" in expr:
            file_part, fragment = expr.split("#", 1)
            if "*" not in fragment:
                # No wildcards, use as-is
                expanded.append(expr)
                continue

            # Convert JSON Pointer to JsonPath format for expansion
            jsonpath_expr = fragment.lstrip("/")
            if jsonpath_expr:
                # Convert /path/to/property to $["path"]["to"]["property"]
                parts = jsonpath_expr.split("/")
                quoted_parts = [f'["{part}"]' for part in parts]
                jsonpath_expr = "$" + "".join(quoted_parts)
            else:
                jsonpath_expr = "$"
        else:
            # Pure JsonPath expression
            jsonpath_expr = expr
            if "*" not in expr:
                # No wildcards, convert to JSON Pointer format
                try:
                    # Test if expression is valid by parsing it
                    test_parser = jsonpath_ng.parse(jsonpath_expr)
                    test_matches = test_parser.find(schema_doc)
                    if test_matches:
                        # Convert to JSON Pointer format for consistency
                        match = test_matches[0]  # Take first match for path structure
                        path_str = str(match.full_path)
                        if path_str.startswith("$"):
                            path_str = path_str[1:]  # Remove $

                        path_parts = []
                        if path_str:
                            # Handle dot notation parsing
                            if path_str.startswith("."):
                                path_str = path_str[1:]  # Remove leading .
                            for part in path_str.split("."):
                                if part.startswith("'") and part.endswith("'"):
                                    part = part[1:-1]
                                path_parts.append(part)

                        if path_parts:
                            json_pointer = "/" + "/".join(path_parts)
                            expanded.append(f"{source_file.name}#{json_pointer}")
                        else:
                            expanded.append(f"{source_file.name}#/")
                        continue
                    else:
                        # No matches, but expression is valid - include as-is
                        expanded.append(f"{source_file.name}#{jsonpath_expr}")
                        continue
                except Exception:
                    # Invalid expression, let it fail below
                    pass

        try:
            # Parse and find matches for wildcard expressions
            jsonpath_parser = jsonpath_ng.parse(jsonpath_expr)
            matches = jsonpath_parser.find(schema_doc)

            for match in matches:
                # Convert path back to JSON Pointer
                path_parts = []

                # Parse the full path from jsonpath-ng
                path_str = str(match.full_path)
                if path_str.startswith("$"):
                    path_str = path_str[1:]  # Remove $

                if path_str:
                    # Handle dot notation like 'key'.User.properties.name or key.value.prop
                    # jsonpath-ng returns paths in formats like:
                    # - '$defs'.User -> ['$defs', 'User']
                    # - items.[0] -> ['items', '[0]']
                    # - key.nested.prop -> ['key', 'nested', 'prop']
                    for part in path_str.split("."):
                        # Handle quoted parts like '$defs' -> $defs
                        if part.startswith("'") and part.endswith("'"):
                            part = part[1:-1]
                        # Keep bracket array notation as-is (like [0])
                        path_parts.append(part)

                if path_parts:
                    json_pointer = "/" + "/".join(path_parts)
                    expanded.append(f"{source_file.name}#{json_pointer}")
                else:
                    expanded.append(f"{source_file.name}#/")

        except Exception as e:
            raise TedsError(
                f"Failed to expand JsonPath expression '{expr}': {e}"
            ) from e

    return expanded


def detect_conflicts(expanded_refs: list[str]) -> list[tuple[str, list[int]]]:
    """Detect conflicts between multiple source references.

    Returns list of (ref, [indices]) where indices are positions in expanded_refs.
    """
    ref_indices: dict[str, list[int]] = {}

    for i, ref in enumerate(expanded_refs):
        if ref not in ref_indices:
            ref_indices[ref] = []
        ref_indices[ref].append(i)

    conflicts = [
        (ref, indices) for ref, indices in ref_indices.items() if len(indices) > 1
    ]
    return conflicts


def extract_base_name(sources: list[str]) -> str:
    """Extract base name for template resolution from list of source references."""
    if not sources:
        return "generated"

    # Use the first source file for base name
    first_source = sources[0]
    file_part = first_source.split("#")[0]
    return Path(file_part).stem


def generate_from_source_config(
    config: dict[str, dict[str, Any]], base_dir: Path
) -> None:
    """Generate test specifications from source-centric YAML configuration."""

    for source_file_str, source_config in config.items():
        source_file = base_dir / source_file_str

        # Determine target file
        if source_config["target"]:
            # Explicit target with possible {base} template resolution
            target_name = source_config["target"].replace("{base}", source_file.stem)
        else:
            # Default: {base}.tests.yaml
            target_name = f"{source_file.stem}.tests.yaml"

        target_path = base_dir / target_name

        # Expand JsonPath expressions for this source
        expanded_refs = expand_jsonpath_expressions(source_file, source_config["paths"])

        # Detect and warn about conflicts within this source
        conflicts = detect_conflicts(expanded_refs)
        for ref, indices in conflicts:
            source_positions = ", ".join(f"#{i+1}" for i in indices)
            print(
                f"Warning: Conflict detected for '{ref}' (paths {source_positions}). Using first occurrence.",
                file=sys.stderr,
            )

        # Remove duplicates while preserving order (first wins)
        seen = set()
        unique_refs = []
        for ref in expanded_refs:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        # Generate tests for each unique reference
        for ref in unique_refs:
            try:
                generate_from(ref, target_path)
            except Exception as e:
                print(f"Warning: Failed to generate from '{ref}': {e}", file=sys.stderr)
