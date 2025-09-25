from __future__ import annotations

import urllib.parse
from pathlib import Path

from jsonpath_ng.jsonpath import Fields, Index, Root


def json_path_to_json_pointer(full_path) -> str:
    """
    Convert a jsonpath-ng match.full_path to a JSON Pointer string.

    Args:
        full_path: The full_path attribute from a jsonpath-ng match object.
                  This should be a concrete path without Root() at the beginning.
                  Use: match.full_path (from parser.find() results)
                  Not: parser object directly

    Returns:
        JSON Pointer string (RFC 6901 format)

    Examples:
        Fields('name') -> "/name"
        Child(Fields('foo'), Fields('bar')) -> "/foo/bar"
        Child(Fields('items'), Index(0)) -> "/items/0"
    """
    segments: list[str] = []

    def walk(node) -> None:
        # Child nodes have .left and .right; recurse to keep order
        if hasattr(node, "left") and hasattr(node, "right"):
            walk(node.left)
            walk(node.right)
            return

        if isinstance(node, Root):
            # Root match ($ expression) -> empty pointer
            return

        if isinstance(node, Fields):
            # In a realized match path this should be exactly one field
            name = node.fields[0]  # no loop, take the single field
            segments.append(
                name.replace("~", "~0").replace("/", "~1")
            )  # Escape per RFC 6901
            return

        if isinstance(node, Index):
            segments.append(str(node.index))
            return

        raise ValueError(
            f"Unhandled node type in jsonpath-ng path: {type(node)} ({full_path!s})"
        )

    walk(full_path)
    return (
        "/" + "/".join(segments) if segments else ""
    )  # Empty string = root document per RFC 6901


def sanitize_pointer(s: str) -> str:
    """Sanitize a JSON Pointer fragment for use in filenames using RFC 6901 escaping."""
    if not s:
        return "root"
    # Apply RFC 6901 escaping: ~ becomes ~0, / becomes ~1
    return s.replace("~", "~0").replace("/", "~1")


def expand_target_template(target: str, file_part: str, pointer: str) -> str:
    """Expand template variables in target path.

    Args:
        target: Target path template with variables like {base}, {file}, {pointer}
        file_part: Schema file path
        pointer: JSON Pointer fragment

    Returns:
        Expanded target path with all template variables substituted

    Template variables:
        {base}  - schema filename without extension
        {ext}   - schema extension without dot
        {file}  - schema filename with extension
        {dir}   - schema file directory
        {pointer} - JSON Pointer (no leading '/'), sanitized for filenames
        {pointer_raw} - JSON Pointer without leading '/' (slashes preserved)
        {pointer_strict} - JSON Pointer without leading '/', percent-encoded
        {index} - 1-based index (always "1" for single refs)
    """
    file_path = Path(file_part)
    base = file_path.stem
    ext = file_path.suffix.lstrip(".")
    file_name = file_path.name
    dir_name = str(file_path.parent) if file_path.parent != Path(".") else ""

    pointer_raw = pointer.lstrip("/")
    pointer_sanitized = sanitize_pointer(pointer_raw)
    pointer_strict = urllib.parse.quote(pointer_raw, safe="")

    # Template variables
    variables = {
        "base": base,
        "ext": ext,
        "file": file_name,
        "dir": dir_name,
        "pointer": pointer_sanitized,
        "pointer_raw": pointer_raw,
        "pointer_strict": pointer_strict,
    }

    # Expand templates
    expanded = target
    for var, value in variables.items():
        expanded = expanded.replace(f"{{{var}}}", value)

    return expanded
