from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .yamlio import yaml_loader, yaml_dumper
from .validate import _validate_testspec_against_schema, validate_doc
from .version import (
    check_spec_compat,
    RECOMMENDED_TESTSPEC_VERSION,
    recommended_minor_str,
    supported_spec_range_str,
    get_version,
)


@dataclass
class ReportInput:
    path: Path
    doc: dict[str, Any]
    counts: dict[str, int]
    rc: int


def _compute_counts(doc: dict[str, Any]) -> dict[str, int]:
    tests = doc.get("tests") or {}
    success = warning = error = 0
    for _ref, grp in tests.items():
        for exp_key in ("valid", "invalid"):
            cases = grp.get(exp_key) or {}
            if isinstance(cases, dict):
                for _k, c in cases.items():
                    res = (c or {}).get("result", "SUCCESS")
                    if res == "ERROR":
                        error += 1
                    elif res == "WARNING":
                        warning += 1
                    else:
                        success += 1
    return {"success": success, "warning": warning, "error": error}


def _render_jinja(template_name_or_path: str, context: dict[str, Any]) -> str:
    from importlib.resources import files as res_files
    from jinja2 import Environment, FileSystemLoader, BaseLoader, select_autoescape

    # Resolve template path: explicit path or bundled name under teds_core/templates
    tpath = Path(template_name_or_path)
    template_source: str | None = None
    loader: BaseLoader
    template_name: str

    if tpath.exists():
        loader = FileSystemLoader(str(tpath.parent))
        template_name = tpath.name
    else:
        # allow names like "summary", "summary.md", "summary.html"
        base = template_name_or_path
        if not any(base.endswith(ext) for ext in (".j2", ".md", ".html", ".htm")):
            # default to markdown template
            candidates = [f"{base}.md.j2", f"{base}.html.j2"]
        elif base.endswith((".md", ".html", ".htm")):
            candidates = [f"{base}.j2"]
        else:
            candidates = [base]

        bundle_dir = res_files("teds_core").joinpath("templates")
        for cand in candidates:
            try:
                p = bundle_dir.joinpath(cand)
                # Using loader instead of read_text to allow template inheritance later
                loader = FileSystemLoader(str(bundle_dir))
                template_name = cand
                break
            except Exception:
                continue
        else:
            raise FileNotFoundError(f"Template not found: {template_name_or_path}")

    autoescape = select_autoescape(enabled_extensions=("html", "htm"))
    env = Environment(loader=loader, autoescape=autoescape)
    # Minimal, safe filters could be added here if needed
    tmpl = env.get_template(template_name)
    return tmpl.render(**context)


def build_context(inputs: Iterable[ReportInput]) -> dict[str, Any]:
    ins = list(inputs)
    totals = {"success": 0, "warning": 0, "error": 0, "specs": len(ins)}
    for ri in ins:
        for k in ("success", "warning", "error"):
            totals[k] += int(ri.counts.get(k, 0))
    return {
        "tool": {
            "version": get_version(),
            "spec_supported": supported_spec_range_str(),
            "spec_recommended": recommended_minor_str(),
        },
        "inputs": [{"path": str(ri.path), "doc": ri.doc, "counts": ri.counts, "rc": ri.rc} for ri in ins],
        "totals": totals,
    }


def run_report(spec_paths: list[Path], template: str, output_level: str) -> tuple[str, int]:
    """Render a report for the given spec files.

    Returns rendered text and an exit code (0 or 2 on hard failure).
    """
    repo_root = Path(__file__).resolve().parents[1]
    hard_rc = 0
    report_inputs: list[ReportInput] = []

    for sp in spec_paths:
        try:
            raw = yaml_loader.load(sp.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(
                f"Failed to read testspec: {sp}\n  error: {type(e).__name__}: {e}",
                flush=True,
            )
            hard_rc = 2
            continue
        # Schema validation
        try:
            _validate_testspec_against_schema(raw, repo_root)
        except Exception as e:
            print(
                f"Spec validation failed: {sp}\n  error: {type(e).__name__}: {e}",
            )
            hard_rc = 2
            continue
        # Version gate
        ver = str(raw.get("version", "")).strip()
        ok, reason = check_spec_compat(ver)
        if not ok:
            print(f"Unsupported testspec version in {sp}: {ver}")
            hard_rc = 2
            continue
        # Evaluate cases with filtering
        out_tests, rc = validate_doc(raw, sp.parent, output_level=output_level, in_place=False)
        doc = {"version": RECOMMENDED_TESTSPEC_VERSION, "tests": out_tests}
        counts = _compute_counts(doc)
        report_inputs.append(ReportInput(path=sp, doc=doc, counts=counts, rc=rc))

    context = build_context(report_inputs)
    rendered = _render_jinja(template, context)
    return rendered, (2 if hard_rc == 2 else 0)

