from __future__ import annotations


class TedsError(Exception):
    """Domain error for user-facing failures (I/O, YAML, schema/ref resolution)."""
    pass

