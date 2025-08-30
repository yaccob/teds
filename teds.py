#!/usr/bin/env python3
"""TeDS CLI shim.

Allows running `python teds.py` in the repo. Installed entry-point is `teds`.
"""

from teds_core import yaml_loader, yaml_dumper, validate_doc, validate_file, generate_from, __version__
from teds_core.cli import main

__all__ = [
    "yaml_loader",
    "yaml_dumper",
    "validate_doc",
    "validate_file",
    "generate_from",
    "__version__",
    "main",
]

if __name__ == "__main__":
    main()

