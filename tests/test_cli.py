from __future__ import annotations

import sys
import subprocess
from pathlib import Path


CASES = Path(__file__).parent / "cases"


SCRIPT = Path(__file__).resolve().parents[1] / "teds.py"


def run_cli(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


from tests.utils import (
    load_yaml_text,
    load_yaml_file,
    copy_case,
    place_schema,
)


def test_verify_warning():
    case = CASES / "format_divergence"
    expected = case / "expected.yaml"

    rc, out, err = run_cli([
        "verify",
        "spec.yaml",
        "--output-level",
        "warning",
    ], cwd=case)
    assert rc == 1

    got_doc = load_yaml_text(out)
    exp_doc = load_yaml_file(expected)
    assert got_doc == exp_doc


def test_verify_error():
    case = CASES / "format_divergence"
    expected = case / "expected.error.yaml"

    rc, out, err = run_cli([
        "verify",
        "spec.yaml",
        "--output-level",
        "error",
    ], cwd=case)
    assert rc == 1

    got_doc = load_yaml_text(out)
    exp_doc = load_yaml_file(expected)
    assert got_doc == exp_doc


def test_verify_in_place(tmp_path: Path):
    # copy case dir to tmp and run -i
    src = CASES / "format_divergence"
    work = copy_case("format_divergence", tmp_path, "case")

    rc, out, err = run_cli(["verify", "spec.yaml", "-i"], cwd=work)
    assert rc == 1
    assert out == ""  # in-place writes to file, not stdout

    got_doc = load_yaml_file(work / "spec.yaml")
    exp_doc = load_yaml_file(src / "expected.in_place.yaml")
    assert got_doc == exp_doc


def test_generate_single_ref(tmp_path: Path, monkeypatch):
    # work on a tmp copy to keep paths literal
    work = copy_case("format_divergence", tmp_path, "case_single")

    rc, out, err = run_cli([
        "generate",
        "schema.yaml#/components/schemas=gen.yaml",
    ], cwd=work)
    assert rc == 0
    monkeypatch.chdir(work)
    assert Path("gen.yaml").exists()
    doc = load_yaml_file(Path("gen.yaml"))
    # contains Email schema group
    # key uses absolute file path; validate by suffix
    keys = list(doc.get("tests", {}).keys())
    assert any(k.endswith("/components/schemas/Email") for k in keys)
    key = next(k for k in keys if k.endswith("/components/schemas/Email"))
    valid = doc["tests"][key].get("valid", {})
    # has example-derived case
    assert any(v.get("from_examples") for v in valid.values())


def test_generate_multi_ref_outs(tmp_path: Path, monkeypatch):
    # create two mini schemas
    s1 = tmp_path / "s1.yaml"
    s1.write_text(
        """
components:
  schemas:
    A:
      type: string
      enum: [x]
      examples: [x]
""",
        encoding="utf-8",
    )
    s2 = tmp_path / "s2.yaml"
    s2.write_text(
        """
components:
  schemas:
    B:
      type: integer
      minimum: 1
      examples: [1]
""",
        encoding="utf-8",
    )

    out1 = tmp_path / "a.yaml"
    out2 = tmp_path / "b.yaml"

    # run in tmp so refs resolve relative to cwd
    rc, out, err = run_cli(
        [
            "generate",
            "s1.yaml#/components/schemas=a.yaml",
            "s2.yaml#/components/schemas=b.yaml",
        ],
        cwd=tmp_path,
    )
    assert rc == 0
    monkeypatch.chdir(tmp_path)
    assert Path("a.yaml").exists() and Path("b.yaml").exists()
    d1 = load_yaml_file(Path("a.yaml"))
    d2 = load_yaml_file(Path("b.yaml"))
    keys1 = list(d1.get("tests", {}).keys())
    keys2 = list(d2.get("tests", {}).keys())
    assert len(keys1) == 1 and keys1[0].endswith("/A")
    assert len(keys2) == 1 and keys2[0].endswith("/B")


def test_generate_directory_target_default_filename(tmp_path: Path, monkeypatch):
    # copy case to tmp and use literal args
    work = copy_case("format_divergence", tmp_path, "case_outdir")
    # place schema next to TARGET parent (out/)
    place_schema(work, "out")

    rc, out, err = run_cli([
        "generate",
        "schema.yaml#/components/schemas=out/",
    ], cwd=work)
    assert rc == 0
    # default filename: {base}.{pointer}.tests.yaml (pointer sanitized)
    monkeypatch.chdir(work)
    assert Path("out/schema.components+schemas.tests.yaml").exists()


def test_generate_template_tokens_pointer_and_raw(tmp_path: Path, monkeypatch):
    # copy case to tmp and use literal args
    work = copy_case("format_divergence", tmp_path, "case_tokens")

    # sanitized pointer token → parent is work/out2
    place_schema(work, "out2")

    # sanitized pointer token
    rc, out, err = run_cli([
        "generate",
        "schema.yaml#/components/schemas=out2/{base}.{pointer}.tests.yaml",
    ], cwd=work)
    assert rc == 0
    monkeypatch.chdir(work)
    assert Path("out2/schema.components+schemas.tests.yaml").exists()

    # pointer_raw creates nested directories → parent is work/out3/schema/components
    place_schema(work, "out3/schema/components")
    # pointer_raw creates nested directories
    rc2, out2, err2 = run_cli([
        "generate",
        "schema.yaml#/components/schemas=out3/{base}/{pointer_raw}.tests.yaml",
    ], cwd=work)
    assert rc2 == 0
    monkeypatch.chdir(work)
    assert Path("out3/schema/components/schemas.tests.yaml").exists()


def test_generate_omit_target_defaults_to_schema_dir(tmp_path: Path, monkeypatch):
    # Copy case to tmp; using relative ref, expect output next to schema.yaml
    work = copy_case("format_divergence", tmp_path, "case")
    rc, out, err = run_cli(["generate", "schema.yaml#/components/schemas"], cwd=work)
    assert rc == 0
    monkeypatch.chdir(work)
    assert Path("schema.components+schemas.tests.yaml").exists()


def test_generate_omit_pointer_and_target_defaults_root(tmp_path: Path, monkeypatch):
    work = copy_case("format_divergence", tmp_path, "case2")
    # no pointer → defaults to '#/'
    rc, out, err = run_cli(["generate", "schema.yaml"], cwd=work)
    assert rc == 0
    monkeypatch.chdir(work)
    assert Path("schema.tests.yaml").exists()


def test_generate_default_pointer_root(tmp_path: Path, monkeypatch):
    # copy case to tmp and use literal args
    work = copy_case("format_divergence", tmp_path, "case_defptr")
    # parent is work/defptr
    place_schema(work, "defptr")
    # omit '#...' → defaults to '#/'
    rc, out, err = run_cli([
        "generate",
        "schema.yaml=defptr/",
    ], cwd=work)
    assert rc == 0
    # default filename at root pointer: {base}.tests.yaml
    monkeypatch.chdir(work)
    assert Path("defptr/schema.tests.yaml").exists()
