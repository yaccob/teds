from __future__ import annotations

from pathlib import Path


def to_relative_path(path: Path) -> str:
    """Convert an absolute path to relative path from current working directory.

    Args:
        path: The path to convert (can be absolute or relative)

    Returns:
        String representation of the path, relative to current working directory.
        Falls back to absolute path string if relative conversion fails.
    """
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        # Fallback to absolute if relative conversion fails
        return str(path)
