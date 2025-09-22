from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .resources import read_text_resource
from .validate import _validate_testspec_against_schema, validate_doc
from .version import (
    RECOMMENDED_TESTSPEC_VERSION,
    check_spec_compat,
    get_version,
    recommended_minor_str,
    supported_spec_range_str,
)
from .yamlio import yaml_loader


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


def _render_jinja_str(
    template_key: str, template_text: str, context: dict[str, Any]
) -> str:
    import io

    from jinja2 import DictLoader, Environment, select_autoescape

    from .yamlio import yaml_dumper

    def strip_document_end_marker(s):
        """Remove YAML document end markers for cleaner template output."""
        if s.endswith("...\n"):
            return s[:-4]
        elif s.endswith("..."):
            return s[:-3]
        return s

    def to_yaml(data):
        """Convert data to YAML format with nice formatting."""
        if data is None:
            return "undefined"
        # Check for Jinja2 Undefined objects
        if hasattr(data, "_undefined_name"):
            return "undefined"

        # Use the project's configured YAML dumper with transform to remove document end markers
        output = io.StringIO()
        yaml_dumper.dump(data, output, transform=strip_document_end_marker)
        return output.getvalue().rstrip()

    autoescape = select_autoescape(enabled_extensions=("html", "htm"))
    env = Environment(
        loader=DictLoader({template_key: template_text}), autoescape=autoescape
    )

    # Add custom YAML filter
    env.filters["to_yaml"] = to_yaml

    tmpl = env.get_template(template_key)
    return tmpl.render(**context)


def _load_template_map() -> list[dict[str, str]]:
    txt = read_text_resource("template_map.yaml")
    data = yaml_loader.load(txt) or {}
    items = data.get("templates") or []
    return [i for i in items if isinstance(i, dict) and i.get("id") and i.get("path")]


def list_templates() -> list[dict[str, str]]:
    return _load_template_map()


def resolve_template(template_id: str) -> tuple[str, str, str]:
    for it in _load_template_map():
        if it.get("id") == template_id:
            path = str(it.get("path"))
            desc = str(it.get("description", ""))
            text = read_text_resource(path)
            return path, text, desc
    raise FileNotFoundError(f"Unknown template id: {template_id}")


def build_context(inputs: Iterable[ReportInput]) -> dict[str, Any]:
    from datetime import datetime

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
        "inputs": [
            {"path": str(ri.path), "doc": ri.doc, "counts": ri.counts, "rc": ri.rc}
            for ri in ins
        ],
        "totals": totals,
        "timestamp": datetime.now().astimezone().isoformat(),
    }


def run_report_per_spec(
    spec_paths: list[Path], template_id: str, output_level: str
) -> tuple[list[tuple[Path, str]], int]:
    """Render a report per spec file using the given template id.

    Returns list of (spec_path, rendered_text) and an exit code (0 or 2 on hard failure).
    """
    repo_root = Path(__file__).resolve().parents[1]
    hard_rc = 0
    report_inputs: list[ReportInput] = []

    for sp in spec_paths:
        try:
            raw = yaml_loader.load(sp.read_text(encoding="utf-8")) or {}
        except Exception as e:  # pragma: no cover start
            # I/O failures - hard to reproduce reliably in tests
            print(
                f"Failed to read testspec: {sp}\n  error: {type(e).__name__}: {e}",
                flush=True,
            )
            hard_rc = 2
            continue  # pragma: no cover stop
        # Schema validation
        try:
            _validate_testspec_against_schema(raw, repo_root)
        except Exception as e:  # pragma: no cover start
            # Schema validation failures - internal errors, hard to trigger
            print(
                f"Spec validation failed: {sp}\n  error: {type(e).__name__}: {e}",
            )
            hard_rc = 2
            continue  # pragma: no cover stop
        # Version gate
        ver = str(raw.get("version", "")).strip()
        ok, _reason = check_spec_compat(ver)
        if not ok:
            print(f"Unsupported testspec version in {sp}: {ver}")
            hard_rc = 2
            continue
        # Evaluate cases with filtering
        out_tests, rc = validate_doc(
            raw, sp.parent, output_level=output_level, in_place=False
        )
        doc = {"version": RECOMMENDED_TESTSPEC_VERSION, "tests": out_tests}
        counts = _compute_counts(doc)
        report_inputs.append(ReportInput(path=sp, doc=doc, counts=counts, rc=rc))

    # load template text
    tpl_path, tpl_text, _ = resolve_template(template_id)

    outputs: list[tuple[Path, str]] = []
    rc_cases = 0
    for ri in report_inputs:
        ctx = build_context([ri])
        rendered = _render_jinja_str(tpl_path, tpl_text, ctx)
        outputs.append((ri.path, rendered))
        rc_cases = max(rc_cases, ri.rc)
    return outputs, (2 if hard_rc == 2 else rc_cases)
