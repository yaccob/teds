from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import jsonpath_ng
from ruamel.yaml.comments import CommentedMap

from .errors import TedsError
from .refs import collect_examples, join_fragment, resolve_schema_node
from .utils import expand_target_template, json_path_to_json_pointer
from .version import RECOMMENDED_TESTSPEC_VERSION
from .yamlio import yaml_dumper, yaml_loader


def _ensure_group(group: Any) -> dict[str, Any]:
    group = {} if not isinstance(group, dict) else dict(group)
    group.setdefault("valid", None)
    group.setdefault("invalid", None)
    return group


def _create_empty_test_file(testspec_path: Path) -> None:
    """Create an empty test file with basic structure for visibility in batch mode."""
    doc = {"version": RECOMMENDED_TESTSPEC_VERSION, "tests": {}}

    # Write the empty test file
    try:
        with testspec_path.open("w", encoding="utf-8") as f:
            yaml_loader.dump(doc, f)
    except Exception as e:
        raise TedsError(
            f"Failed to create empty testspec: {testspec_path}\n  error: {type(e).__name__}: {e}"
        ) from e


def generate_exact_node(node_ref: str, testspec_path: Path) -> None:
    """Generate a test for the exact referenced node without expanding children."""
    if testspec_path.exists():
        try:
            doc = yaml_loader.load(testspec_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            raise TedsError(
                f"Failed to read or create testspec: {testspec_path}\n  error: {type(e).__name__}: {e}"
            ) from e
    else:
        doc = {}

    # Ensure version field is present for new documents
    if "version" not in doc:
        doc["version"] = RECOMMENDED_TESTSPEC_VERSION

    tests = doc.get("tests")
    if not isinstance(tests, dict):
        tests = {}
        doc["tests"] = tests

    base_dir = testspec_path.parent

    # Create test only for the exact referenced node (no children expansion)
    group = _ensure_group(tests.get(node_ref))
    tests[node_ref] = group

    # Add examples if available
    ex_list = collect_examples(base_dir, node_ref)
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

    # Ensure version field is present for new documents
    if "version" not in doc:
        doc["version"] = RECOMMENDED_TESTSPEC_VERSION

    tests = doc.get("tests")
    if not isinstance(tests, dict):
        tests = {}
        doc["tests"] = tests

    base_dir = testspec_path.parent

    # Try to resolve the schema reference
    try:
        parent_node, parent_frag = resolve_schema_node(base_dir, parent_ref)
    except Exception as first_error:
        # If the reference is relative and fails, try to find the schema file
        file_part = parent_ref.split("#")[0]
        if not Path(file_part).is_absolute():
            # Search for the schema file in the directory tree
            schema_path = _find_schema_file(base_dir, file_part)
            if schema_path:
                # Update base_dir to the schema's directory and try again
                base_dir = schema_path.parent
                try:
                    parent_node, parent_frag = resolve_schema_node(base_dir, parent_ref)
                except Exception as second_error:
                    raise TedsError(
                        f"Failed to resolve parent schema ref: {parent_ref}\n  base_dir: {base_dir}\n  error: {type(second_error).__name__}: {second_error}"
                    ) from second_error
            else:
                raise TedsError(
                    f"Failed to resolve parent schema ref: {parent_ref}\n  base_dir: {base_dir}\n  error: {type(first_error).__name__}: {first_error}"
                ) from first_error
        else:
            raise TedsError(
                f"Failed to resolve parent schema ref: {parent_ref}\n  base_dir: {base_dir}\n  error: {type(first_error).__name__}: {first_error}"
            ) from first_error
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

    # Create tests for children of the referenced node (standard behavior)
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
        # Check for REF[=TARGET] syntax first
        if "=" in parsed:
            ref_part, target_part = parsed.split("=", 1)
        else:
            ref_part = parsed
            target_part = None

        # JSON Pointer string - convert to normalized JSON-Path configuration
        if "#" in ref_part:
            file_part, fragment = ref_part.split("#", 1)
            if not file_part:
                raise TedsError(f"Missing schema file path: {ref_part}")

            # Convert JSON Pointer to JSON-Path with mandatory wildcard for children
            fragment = fragment.lstrip("/")
            if fragment:
                # Convert /path/to/property to $["path"]["to"]["property"].*
                parts = fragment.split("/")
                quoted_parts = [f'["{part}"]' for part in parts]
                jsonpath = "$" + "".join(quoted_parts) + ".*"
            else:
                # Root reference becomes $.*
                jsonpath = "$.*"

            # Expand template variables in target if present
            expanded_target = None
            if target_part:
                expanded_target = expand_target_template(
                    target_part, file_part, fragment
                )

            # Return normalized configuration with expanded target
            return {file_part: {"paths": [jsonpath], "target": expanded_target}}
        else:
            # String without fragment - RFC 3986 compliant: references whole document
            # Both "schema.yaml" and "schema.yaml#" reference the entire document
            jsonpath = "$.*"

            # Expand template variables in target if present
            expanded_target = None
            if target_part:
                expanded_target = expand_target_template(target_part, ref_part, "")

            return {ref_part: {"paths": [jsonpath], "target": expanded_target}}
    else:
        raise TedsError(
            f"Configuration must be object or string, got {type(parsed).__name__}"
        )


# validate_jsonpath_expression() function removed - redundant to jsonpath-ng validation


def _find_schema_file(base_dir: Path, filename: str) -> Path | None:
    """Find a schema file by searching in subdirectories.

    Searches for the file starting from base_dir and walking through subdirectories.
    Returns the first match found, or None if not found.
    """
    # First check current directory
    candidate = base_dir / filename
    if candidate.exists():
        return candidate

    # Search in subdirectories
    for root, _dirs, files in os.walk(base_dir):
        if filename in files:
            return Path(root) / filename

    return None


def expand_jsonpath_expressions(source_file: Path, expressions: list[str]) -> list[str]:
    """Expand JsonPath expressions to concrete JSON Pointer references.

    This function processes only JSON-Path expressions. JSON-Pointer conversion
    should happen at the CLI boundary via parse_generate_config().
    """
    expanded = []

    # Load schema document once
    try:
        schema_doc = yaml_loader.load(source_file.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise TedsError(f"Failed to load schema {source_file}: {e}") from e

    for jsonpath_expr in expressions:
        try:
            # Parse and find matches - jsonpath-ng handles all validation
            jsonpath_parser = jsonpath_ng.parse(jsonpath_expr)
            matches = jsonpath_parser.find(schema_doc)

            for match in matches:
                # Use the clean utils function for JSONPath -> JSON Pointer conversion
                json_pointer = json_path_to_json_pointer(match.full_path)
                expanded.append(f"{source_file.name}#{json_pointer}")

        except Exception as e:
            raise TedsError(
                f"Failed to expand JsonPath expression '{jsonpath_expr}': {e}"
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
            # Explicit target: relative to cwd (only {base} template supported for YAML configs)
            target_name = source_config["target"].replace("{base}", source_file.stem)
            target_path = base_dir / target_name
        else:
            # Default: {base}.tests.yaml next to schema file
            target_name = f"{source_file.stem}.tests.yaml"
            target_path = source_file.parent / target_name

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

        # Generate tests for each unique reference (exact nodes only, no children expansion)
        try:
            display_path = str(target_path.relative_to(Path.cwd()))
        except ValueError:
            # Fall back to absolute path if relative conversion fails (e.g., symlinks)
            display_path = str(target_path)
        print(f"Generating {display_path}", file=sys.stderr)

        if unique_refs:
            # Generate for each found reference
            for ref in unique_refs:
                try:
                    generate_exact_node(ref, target_path)
                except Exception as e:
                    print(
                        f"Warning: Failed to generate from '{ref}': {e}",
                        file=sys.stderr,
                    )
        else:
            # No references found - create empty test file for visibility and batch-mode feedback
            _create_empty_test_file(target_path)
