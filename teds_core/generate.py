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


def parse_generate_config(config_str: str) -> dict[str, list[str]] | str:
    """Parse generate configuration from YAML string or file reference.

    Returns:
        - dict: YAML object configuration for multiple outputs
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
        # New YAML object format
        for output_file, sources in parsed.items():
            if not isinstance(sources, list):
                raise TedsError(
                    f"Sources for '{output_file}' must be a list, got {type(sources).__name__}"
                )
            for source in sources:
                if not isinstance(source, str):
                    raise TedsError(
                        f"Source reference must be string, got {type(source).__name__}"
                    )
        return parsed
    elif isinstance(parsed, str):
        # Backward compatibility: JSON Pointer string
        return parsed
    else:
        raise TedsError(
            f"Configuration must be object or string, got {type(parsed).__name__}"
        )


def validate_jsonpath_expression(expr: str) -> None:
    """Validate a JsonPath expression for basic syntax."""
    # Split schema file and fragment
    if "#" not in expr:
        raise TedsError(f"Invalid reference format, missing '#': {expr}")

    file_part, fragment = expr.split("#", 1)
    if not file_part:
        raise TedsError(f"Missing schema file path: {expr}")

    # Basic JsonPath validation - check for obviously invalid syntax
    if fragment.startswith("/"):
        fragment = fragment[1:]  # Remove leading slash for JsonPath

    if not fragment:
        return  # Root reference is valid

    # Check for basic syntax errors
    invalid_patterns = [
        r"\[([^]]+$)",  # Unclosed bracket
        r"\.\./",  # Parent navigation (not supported)
        r"^[^$]",  # Must start with $ for root
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, fragment):
            raise TedsError(f"Invalid JsonPath expression: {expr}")


def expand_jsonpath_expressions(base_dir: Path, expressions: list[str]) -> list[str]:
    """Expand JsonPath expressions with wildcards to concrete JSON Pointer references."""
    expanded = []

    for expr in expressions:
        validate_jsonpath_expression(expr)

        file_part, fragment = expr.split("#", 1)
        if "*" not in fragment:
            # No wildcards, use as-is
            expanded.append(expr)
            continue

        # Load schema and expand wildcards
        schema_path = (base_dir / file_part).resolve()
        try:
            schema_doc = yaml_loader.load(schema_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            raise TedsError(f"Failed to load schema {schema_path}: {e}") from e

        # Convert JSON Pointer to JsonPath format
        jsonpath_expr = fragment.lstrip("/")
        if jsonpath_expr:
            # Convert /path/to/property to $["path"]["to"]["property"]
            # This handles special characters like $ in property names
            parts = jsonpath_expr.split("/")
            quoted_parts = [f'["{part}"]' for part in parts]
            jsonpath_expr = "$" + "".join(quoted_parts)
        else:
            jsonpath_expr = "$"

        try:
            # Parse and find matches
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
                    # Handle bracket notation like ["$defs"]["User"]["properties"]["name"]
                    import re

                    bracket_pattern = r'\["([^"]+)"\]'
                    matches_parts = re.findall(bracket_pattern, path_str)
                    if matches_parts:
                        path_parts.extend(matches_parts)
                    else:
                        # Handle dot notation like 'key'.User.properties.name or key.value.prop
                        if path_str.startswith("."):
                            path_str = path_str[1:]  # Remove leading .
                        for part in path_str.split("."):
                            # Handle quoted parts like '$defs' -> $defs
                            if part.startswith("'") and part.endswith("'"):
                                part = part[1:-1]
                            # Handle bracket array notation like [0]
                            elif part.startswith("[") and part.endswith("]"):
                                part = part[1:-1]
                                if part.startswith("'") and part.endswith("'"):
                                    part = part[1:-1]
                            path_parts.append(part)

                if path_parts:
                    json_pointer = "/" + "/".join(path_parts)
                    expanded.append(f"{file_part}#{json_pointer}")
                else:
                    expanded.append(f"{file_part}#/")

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


def resolve_template_variables(config: dict[str, list[str]]) -> dict[str, list[str]]:
    """Resolve template variables like {base} in output filenames."""
    resolved = {}

    for output_template, sources in config.items():
        if "{base}" in output_template:
            base_name = extract_base_name(sources)
            output_file = output_template.replace("{base}", base_name)
        else:
            output_file = output_template

        resolved[output_file] = sources

    return resolved


def generate_from_config(config: dict[str, list[str]], base_dir: Path) -> None:
    """Generate test specifications from YAML configuration."""
    # Resolve template variables
    resolved_config = resolve_template_variables(config)

    for output_file, sources in resolved_config.items():
        # Expand JsonPath expressions
        expanded_refs = expand_jsonpath_expressions(base_dir, sources)

        # Detect and warn about conflicts
        conflicts = detect_conflicts(expanded_refs)
        for ref, indices in conflicts:
            source_positions = ", ".join(f"#{i+1}" for i in indices)
            print(
                f"Warning: Conflict detected for '{ref}' (sources {source_positions}). Using first occurrence.",
                file=sys.stderr,
            )

        # Remove duplicates while preserving order (first wins)
        seen = set()
        unique_refs = []
        for ref in expanded_refs:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        # Determine output path
        output_path = base_dir / output_file

        # Generate tests for each unique reference
        for ref in unique_refs:
            try:
                generate_from(ref, output_path)
            except Exception as e:
                print(f"Warning: Failed to generate from '{ref}': {e}", file=sys.stderr)
