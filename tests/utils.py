from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import teds


def load_yaml_text(text: str) -> Dict[str, Any]:
    return teds.yaml_loader.load(text) or {}


def load_yaml_file(path: Path) -> Dict[str, Any]:
    return teds.yaml_loader.load(path.read_text(encoding="utf-8")) or {}


def copy_case(case_name: str, base_tmp: Path, dest_name: str) -> Path:
    src = Path(__file__).parent / "cases" / case_name
    dest = base_tmp / dest_name
    shutil.copytree(src, dest)
    return dest


def place_schema(work: Path, parent_rel: str) -> None:
    dest = work / parent_rel
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work / "schema.yaml", dest / "schema.yaml")


# CLI runner (used by CLI tests)
_SCRIPT = Path(__file__).resolve().parents[1] / "teds.py"


def run_cli(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr
