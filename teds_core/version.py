from __future__ import annotations

from importlib import metadata
from subprocess import run, PIPE
from enum import Enum
import semver  # type: ignore

SUPPORTED_TESTSPEC_VERSION = "1.0.0"
_SUPPORTED_VI = semver.VersionInfo.parse(SUPPORTED_TESTSPEC_VERSION)
SUPPORTED_TESTSPEC_MAJOR = _SUPPORTED_VI.major
SUPPORTED_TESTSPEC_MINOR = _SUPPORTED_VI.minor
SUPPORTED_TESTSPEC_PATCH = _SUPPORTED_VI.patch


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
    return f"{SUPPORTED_TESTSPEC_MAJOR}.{SUPPORTED_TESTSPEC_MINOR}.x"


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
    if vi.minor > SUPPORTED_TESTSPEC_MINOR:
        return False, SpecVersionIssue.MINOR_TOO_NEW
    return True, None

