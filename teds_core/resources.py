from __future__ import annotations

from importlib.resources import files as _res_files
from pathlib import Path

_PKG_NAME = "teds_core"


def read_text_resource(filename: str) -> str:
    """Read a bundled text resource robustly.

    Tries, in order:
      1) Package resources under teds_core (if bundled there)
      2) The parent directory of the package (wheel root in site-packages)
      3) The project root when running from a source checkout
    Raises FileNotFoundError if not found.
    """
    # 1) Package resources (if packaged inside teds_core)
    try:
        return _res_files(_PKG_NAME).joinpath(filename).read_text(encoding="utf-8")
    except Exception:
        pass

    # 2) Wheel/site-packages root next to the package directory
    site_root = Path(__file__).resolve().parents[1]
    p_site = site_root / filename
    if p_site.exists():
        return p_site.read_text(encoding="utf-8")

    # 3) Repository root (source checkout)
    repo_root = Path(__file__).resolve().parents[1]
    p_repo = repo_root / filename
    if p_repo.exists():
        return p_repo.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Resource not found: {filename}")
