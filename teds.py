#!/usr/bin/env python3
"""TeDS CLI shim.

Allows running `python teds.py` in the repo. Installed entry-point is `teds`.
"""

from teds_core import (
    __version__,
    generate_from,
    validate_doc,
    validate_file,
    yaml_dumper,
    yaml_loader,
)
from teds_core.cli import main

__all__ = [
    "__version__",
    "generate_from",
    "main",
    "validate_doc",
    "validate_file",
    "yaml_dumper",
    "yaml_loader",
]

if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
