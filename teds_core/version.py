from __future__ import annotations

from importlib import metadata
from subprocess import run, PIPE
from enum import Enum
from pathlib import Path
import semver  # type: ignore

from .yamlio import yaml_loader
from .resources import read_text_resource

# Load compatibility manifest from repository root (bundled with the wheel)
_REPO_ROOT = Path(__file__).resolve().parents[1]

def _load_compat() -> tuple[int, int, int]:
    # Load manifest via shared resource helper
    try:
        text = read_text_resource("teds_compat.yaml")
    except Exception:
        return 1, 0, 0
    try:
        compat = yaml_loader.load(text) or {}
        spec = compat.get("spec") or {}
        major = int(spec.get("major"))
        max_minor = int(spec.get("max_minor"))
        rec_minor = int(spec.get("recommended_minor", max_minor))
        return major, max_minor, rec_minor
    except Exception:
        return 1, 0, 0

SUPPORTED_TESTSPEC_MAJOR, _SUPPORTED_MAX_MINOR, _RECOMMENDED_MINOR = _load_compat()
RECOMMENDED_TESTSPEC_VERSION = f"{SUPPORTED_TESTSPEC_MAJOR}.{_RECOMMENDED_MINOR}.0"


def _from_pkg() -> str | None:
    try:
        return metadata.version("teds")
    except Exception:
        return None


def _from_git() -> str | None:
    try:
        p = run(["git", "describe", "--tags", "--abbrev=0"], stdout=PIPE, stderr=PIPE, text=True, check=False)
        if p.returncode == 0:
            return p.stdout.strip().lstrip("v")
        return None
    except Exception:
        return None


def get_version() -> str:
    return _from_pkg() or _from_git() or "0.0.0+dev"


def supported_spec_range_str() -> str:
    # Display as 1.0–1.N
    return f"{SUPPORTED_TESTSPEC_MAJOR}.0–{SUPPORTED_TESTSPEC_MAJOR}.{_SUPPORTED_MAX_MINOR}"

def recommended_minor_str() -> str:
    return f"{SUPPORTED_TESTSPEC_MAJOR}.{_RECOMMENDED_MINOR}"


class SpecVersionIssue(Enum):
    INVALID = "invalid"
    MAJOR_MISMATCH = "major_mismatch"
    MINOR_TOO_NEW = "minor_too_new"


def check_spec_compat(ver: str) -> tuple[bool, SpecVersionIssue | None]:
    try:
        vi = semver.VersionInfo.parse(ver)
    except Exception:
        return False, SpecVersionIssue.INVALID
    if vi.major != SUPPORTED_TESTSPEC_MAJOR:
        return False, SpecVersionIssue.MAJOR_MISMATCH
    if vi.minor > _SUPPORTED_MAX_MINOR:
        return False, SpecVersionIssue.MINOR_TOO_NEW
    return True, None
