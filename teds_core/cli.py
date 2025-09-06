from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

from .generate import generate_from
from .validate import validate_file
from .errors import TedsError
from .version import get_version, SUPPORTED_TESTSPEC_MAJOR


def _sanitize(s: str) -> str:
    if not s:
        return "root"
    segs = s.split("/")
    esc = [seg.replace("+", "++") for seg in segs]
    return "+".join(esc)


def _split_ref(mapping: str) -> tuple[str, str | None]:
    if "=" in mapping:
        left, right = mapping.split("=", 1)
        return left.strip(), right.strip()
    return mapping.strip(), None


def _parse_ref(ref: str) -> tuple[str, str]:
    file_part, sep, frag = ref.partition("#")
    if not sep:
        return file_part, "/"
    return file_part, frag or "/"


def _tokens_for_mapping(file_part: str, pointer: str, out_index: int) -> dict:
    from urllib.parse import quote

    p = Path(file_part)
    file_name = p.name or "schema.yaml"
    base = p.stem or "schema"
    ext = p.suffix.lstrip(".") if p.suffix else "yaml"
    dir_part = str(p.parent) if str(p.parent) not in (".", "") else ""

    pointer_raw = pointer.lstrip("/")
    pointer_token = _sanitize(pointer_raw) if pointer_raw else "root"
    pointer_strict = quote(pointer_raw, safe="") if pointer_raw else "root"

    return {
        "file": file_name,
        "base": base,
        "ext": ext,
        "dir": dir_part,
        "pointer": pointer_token,
        "pointer_raw": pointer_raw,
        "pointer_strict": pointer_strict,
        "index": out_index,
    }


def _default_filename(base: str, pointer: str) -> str:
    pointer_raw = pointer.lstrip("/")
    if not pointer_raw:
        return f"{base}.tests.yaml"
    return f"{base}.{_sanitize(pointer_raw)}.tests.yaml"


def _plan_pairs(mappings: list[str]) -> list[tuple[str, Path]]:
    pairs: List[Tuple[str, Path]] = []
    for i, m in enumerate(mappings, start=1):
        ref_str, target = _split_ref(m)
        file_part, pointer = _parse_ref(ref_str)
        toks = _tokens_for_mapping(file_part, pointer, i)

        schema_dir = Path(file_part).resolve().parent

        if target is None:
            out_path = schema_dir / _default_filename(toks["base"], pointer)
        else:
            target_fmt = target.format(**toks) if "{" in target else target
            base_target = Path(target_fmt)
            path = base_target if base_target.is_absolute() else (schema_dir / base_target)
            if target_fmt.endswith(os.sep) or path.is_dir():
                out_path = path / _default_filename(toks["base"], pointer)
            else:
                out_path = path

        pairs.append((f"{file_part}#/{pointer.lstrip('/')}" if not file_part.endswith(f"#{pointer}") else f"{file_part}#{pointer}", out_path))
    outs_abs = [p.resolve() for _, p in pairs]
    seen = {}
    for idx, p in enumerate(outs_abs):
        if p in seen:
            other = seen[p]
            raise TedsError(f"Output collision: mappings #{other+1} and #{idx+1} both target {p}")
        seen[p] = idx
    return [(ref, p) for (ref, _), p in zip(pairs, outs_abs)]


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="teds",
        description=(
            "Verify YAML testspecs against JSON Schemas, and generate specs from schema refs."
        ),
        epilog=(
            "Exit codes:\n"
            "  0  success\n"
            "  1  validation produced ERROR cases\n"
            "  2  hard failures (I/O, YAML parse, invalid testspec schema, schema/ref resolution, unexpected error)\n\n"
            "Network access:\n"
            "  By default, external $ref resolution is disabled (local-only).\n"
            "  Use --allow-network to enable HTTP/HTTPS with a global timeout and size cap.\n"
            "  Env overrides: TEDS_NETWORK_TIMEOUT (seconds), TEDS_NETWORK_MAX_BYTES (bytes).\n\n"
            "Error handling:\n"
            "  emits concise, user-facing messages with context; no stack traces for expected failures."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow HTTP/HTTPS $ref resolution (default: off). Applies global timeout and size caps.",
    )
    ap.add_argument("--network-timeout", type=float, default=None, help="Timeout in seconds for HTTP/HTTPS $ref fetches (overrides env)")
    ap.add_argument("--network-max-bytes", type=int, default=None, help="Maximum bytes per HTTP/HTTPS resource (overrides env)")
    sub = ap.add_subparsers(dest="cmd")

    p_verify = sub.add_parser(
        "verify",
        help="Verify one or more testspec files.",
        epilog=(
            "Exit codes:\n"
            "  0  success\n"
            "  1  validation produced ERROR cases\n"
            "  2  hard failures (I/O, YAML parse, invalid testspec schema, schema/ref resolution, unexpected error)\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_verify.add_argument("spec", nargs="+", help="YAML testspec file(s)")
    p_verify.add_argument("--output-level", choices=["all", "warning", "error"], default="warning",
                         help="Filter cases to emit: all, warning (default), or error")
    p_verify.add_argument("-i", "--in-place", action="store_true", help="Write results back to the given spec file(s)")

    p_gen = sub.add_parser(
        "generate",
        help="Generate testspec(s) from schema ref(s)",
        description=(
            "Generate testspec(s) for child schemas under a JSON Pointer.\n"
            "- Usage: teds generate REF[=TARGET] [REF[=TARGET] ...]\n"
            "- REF: path/to/schema.yaml#/<json-pointer> (default pointer if omitted: #/)\n"
            "- TARGET: literal path or template with tokens; if a directory, the default filename is appended.\n"
            "- Resolution: omitted or relative TARGET paths are resolved against the schema file's directory.\n"
            "- Behavior: merges existing files; adds example-derived valid cases; leaves invalid empty."
        ),
        epilog=(
            "Tokens (in TARGET):\n"
            "  {file}  schema filename with extension\n"
            "  {base}  schema filename without extension\n"
            "  {ext}   schema extension without dot\n"
            "  {dir}   schema file directory (as given)\n"
            "  {pointer}      JSON Pointer (no leading '/'), sanitized for filenames\n"
            "  {pointer_raw}  JSON Pointer without leading '/' (slashes preserved)\n"
            "  {pointer_strict} JSON Pointer without leading '/', percent-encoded (safe, reversible)\n"
            "  {index}        1-based index of this mapping\n\n"
            "Default filename (when TARGET is omitted or a directory):\n"
            "  - Pointer '#/': {base}.tests.yaml\n"
            "  - Any other pointer: {base}.{pointer}.tests.yaml (pointer without leading '/', sanitized)\n\n"
            "Examples:\n"
            "  teds generate demo/schema.yaml#/components/schemas\n"
            "    → writes demo/schema.components+schemas.tests.yaml\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_gen.add_argument("mapping", nargs="+", help="REF[=TARGET] mappings")

    return ap


def main() -> None:
    argv = sys.argv[1:]
    ap = _build_parser()
    if not argv or argv[0] in {"-h", "--help"}:
        ap.print_help(sys.stderr if argv else sys.stdout)
        sys.exit(0)

    if argv[0] in {"--version", "-V"}:
        print(f"teds {get_version()} (testspec major: {SUPPORTED_TESTSPEC_MAJOR})")
        sys.exit(0)

    if argv[0] in {"verify", "generate"}:
        args = ap.parse_args(argv)
        try:
            from .refs import set_network_policy
            set_network_policy(args.allow_network, timeout=args.network_timeout, max_bytes=args.network_max_bytes)
        except Exception:
            pass
        if args.cmd == "verify":
            rc_all = 0
            for spec in args.spec:
                rc_all = max(rc_all, validate_file(Path(spec), args.output_level, args.in_place))
            sys.exit(rc_all)
        elif args.cmd == "generate":
            try:
                pairs = _plan_pairs(args.mapping)
                for ref, outp in pairs:
                    outp.parent.mkdir(parents=True, exist_ok=True)
                    generate_from(ref, outp)
            except TedsError as e:
                print(str(e), file=sys.stderr)
                sys.exit(2)
            except Exception as e:
                print(f"Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
                sys.exit(2)
            sys.exit(0)
        else:
            ap.print_help(sys.stderr)
            sys.exit(2)

    ap.print_help(sys.stderr)
    sys.exit(2)


__all__ = ["main"]
