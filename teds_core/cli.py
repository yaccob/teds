from __future__ import annotations

import argparse
import logging
import logging.config
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from ruamel.yaml import YAML

from .errors import TedsError
from .generate import generate_from_source_config, parse_generate_config
from .validate import validate_file
from .version import get_version, recommended_minor_str, supported_spec_range_str


def setup_logging():
    """Setup logging from YAML config with environment variable override."""
    # Find the logging config file
    config_path = Path(__file__).parent.parent / "logging.yaml"
    
    if config_path.exists():
        yaml = YAML(typ='safe', pure=True)
        with open(config_path, 'r') as f:
            config = yaml.load(f)
        
        # Override log level from environment variable if set
        env_level = os.getenv('LOGLEVEL', '').upper()
        if env_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            # Set the teds_core logger level from environment
            if 'loggers' in config and 'teds_core' in config['loggers']:
                config['loggers']['teds_core']['level'] = env_level
        
        logging.config.dictConfig(config)
    else:
        # Fallback to basic config
        level = os.getenv('LOGLEVEL', 'INFO').upper()
        logging.basicConfig(
            level=getattr(logging, level, logging.INFO),
            format='%(name)s:%(levelname)s: %(message)s',
            stream=sys.stderr
        )


class Command(ABC):
    """Abstract base class for CLI commands."""

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the command and return exit code."""
        pass


class VersionCommand(Command):
    """Command to display version information."""

    def execute(self, _args: argparse.Namespace) -> int:
        print(
            f"teds {get_version()} (spec supported: {supported_spec_range_str()}; recommended: {recommended_minor_str()})"
        )
        return 0


class ListTemplatesCommand(Command):
    """Command to list available templates."""

    def execute(self, _args: argparse.Namespace) -> int:
        from .report import list_templates

        for it in list_templates():
            print(f"{it.get('id')}: {it.get('description','').strip()}")
        return 0


class VerifyCommand(Command):
    """Command to verify test specifications."""

    def execute(self, args: argparse.Namespace) -> int:
        self._configure_network(args)

        if args.report:
            return self._handle_report_mode(args)
        else:
            return self._handle_verify_mode(args)

    def _configure_network(self, args: argparse.Namespace) -> None:
        """Configure network policy from arguments."""
        try:
            from .refs import set_network_policy

            set_network_policy(
                args.allow_network,
                timeout=args.network_timeout,
                max_bytes=args.network_max_bytes,
            )
        except Exception:
            pass

    def _handle_report_mode(self, args: argparse.Namespace) -> int:
        """Handle verification with report generation."""
        try:
            # Parse TEMPLATE_ID or TEMPLATE_ID=OUTFILE
            report_arg = args.report
            tpl_id, out_override = (
                ([*report_arg.split("=", 1), None])[:2]
                if "=" in report_arg
                else (report_arg, None)
            )
        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 2

        from .report import resolve_template, run_report_per_spec

        try:
            resolve_template(tpl_id)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return 2

        try:
            pairs, rc = run_report_per_spec(
                [Path(s) for s in args.spec], tpl_id, args.output_level
            )
            multi = len(pairs) > 1

            for sp, content in pairs:
                if out_override:
                    if multi:
                        print(
                            "Explicit output path is only supported with a single SPEC",
                            file=sys.stderr,
                        )
                        return 2
                    out_path = Path(out_override)
                else:
                    base = sp.stem
                    # Extract extension from template name, default to .md
                    tpl_parts = tpl_id.split(".")
                    ext = f".{tpl_parts[-1]}" if len(tpl_parts) > 1 else ".md"
                    tbase = tpl_parts[0]
                    name = (
                        f"{base}.report{ext}"
                        if not multi
                        else f"{base}.{tbase}.report{ext}"
                    )
                    out_path = sp.parent / name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"Generating report {out_path}", file=sys.stderr)
                out_path.write_text(content, encoding="utf-8")
        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 2

        return rc

    def _handle_verify_mode(self, args: argparse.Namespace) -> int:
        """Handle standard verification mode."""
        rc_all = 0
        for spec in args.spec:
            spec_path = Path(spec)
            if args.in_place:
                print(f"Updating {spec_path}", file=sys.stderr)
            else:
                print(f"Verifying {spec_path}", file=sys.stderr)
            rc_all = max(
                rc_all, validate_file(spec_path, args.output_level, args.in_place)
            )
        return rc_all


class GenerateCommand(Command):
    """Command to generate test specifications."""

    def execute(self, args: argparse.Namespace) -> int:
        self._configure_network(args)

        try:
            # Process each mapping argument
            for mapping_str in args.mapping:
                config = parse_generate_config(mapping_str)

                # All inputs are now normalized to dict format by parse_generate_config
                if not isinstance(config, dict):
                    raise TedsError(f"Unexpected configuration format: {type(config)}")

                # Use unified processing pipeline
                base_dir = Path.cwd()
                # Status messages will be handled inside generate_from_source_config
                generate_from_source_config(config, base_dir)
        except TedsError as e:
            print(str(e), file=sys.stderr)
            return 2
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
            return 2

        return 0

    def _configure_network(self, args: argparse.Namespace) -> None:
        """Configure network policy from arguments."""
        try:
            from .refs import set_network_policy

            set_network_policy(
                args.allow_network,
                timeout=args.network_timeout,
                max_bytes=args.network_max_bytes,
            )
        except Exception:
            pass


class CommandRegistry:
    """Registry for CLI commands."""

    def __init__(self):
        self._commands: dict[str, Command] = {
            "version": VersionCommand(),
            "list-templates": ListTemplatesCommand(),
            "verify": VerifyCommand(),
            "generate": GenerateCommand(),
        }

    def get_command(self, name: str) -> Command | None:
        """Get command by name."""
        return self._commands.get(name)

    def has_command(self, name: str) -> bool:
        """Check if command exists."""
        return name in self._commands


def _sanitize(s: str) -> str:
    if not s:
        return "root"
    segs = s.split("/")
    esc = [seg.replace("+", "++") for seg in segs]
    return "+".join(esc)


def _expand_target_template(target: str, file_part: str, pointer: str) -> str:
    """Expand template variables in target path."""
    import urllib.parse

    file_path = Path(file_part)
    base = file_path.stem
    ext = file_path.suffix.lstrip(".")
    file_name = file_path.name
    dir_name = str(file_path.parent) if file_path.parent != Path(".") else ""

    pointer_raw = pointer.lstrip("/")
    pointer_sanitized = _sanitize(pointer_raw)
    pointer_strict = urllib.parse.quote(pointer_raw, safe="")

    # Template variables
    variables = {
        "base": base,
        "ext": ext,
        "file": file_name,
        "dir": dir_name,
        "pointer": pointer_sanitized,
        "pointer_raw": pointer_raw,
        "pointer_strict": pointer_strict,
        "index": "1",  # Single ref, so index is always 1
    }

    # Expand templates
    expanded = target
    for var, value in variables.items():
        expanded = expanded.replace(f"{{{var}}}", value)

    return expanded


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
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow HTTP/HTTPS $ref resolution (default: off). Applies global timeout and size caps.",
    )
    ap.add_argument(
        "--network-timeout",
        type=float,
        default=None,
        help="Timeout in seconds for HTTP/HTTPS $ref fetches (overrides env)",
    )
    ap.add_argument(
        "--network-max-bytes",
        type=int,
        default=None,
        help="Maximum bytes per HTTP/HTTPS resource (overrides env)",
    )
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
    p_verify.add_argument(
        "-l",
        "--output-level",
        choices=["all", "warning", "error"],
        default="warning",
        help="Filter cases to emit: all, warning (default), or error",
    )
    p_verify.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Write results back to the given spec file(s)",
    )
    p_verify.add_argument(
        "--report",
        help="Render report using TEMPLATE_ID or TEMPLATE_ID=OUTFILE (reports always write files)",
    )
    # verify remains focused on validation; reporting moved to a dedicated subcommand

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
            "  {pointer}      JSON Pointer (no leading '/'), RFC 6901 escaped for filenames\n"
            "  {pointer_raw}  JSON Pointer without leading '/' (slashes preserved)\n"
            "  {pointer_strict} JSON Pointer without leading '/', percent-encoded (safe, reversible)\n\n"
            "Default filename (when TARGET is omitted or a directory):\n"
            "  - Pointer '#/': {base}.tests.yaml\n"
            "  - Any other pointer: {base}.{pointer}.tests.yaml (pointer without leading '/', RFC 6901 escaped)\n\n"
            "Examples:\n"
            "  teds generate demo/schema.yaml#/components/schemas\n"
            "    → writes demo/schema.components~1schemas.tests.yaml\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_gen.add_argument("mapping", nargs="+", help="REF[=TARGET] mappings")

    # No explicit report/templates subcommands; reporting is handled via verify --report and templates listing via top-level --list-templates.

    return ap


def main() -> None:
    """Main CLI entry point using Command pattern."""
    setup_logging()  # Initialize logging first
    argv = sys.argv[1:]
    registry = CommandRegistry()

    # Handle special cases first
    exit_code = _handle_special_cases(argv, registry)
    if exit_code is not None:
        sys.exit(exit_code)

    # Parse arguments for regular commands
    ap = _build_parser()

    if not argv or argv[0] not in {"verify", "generate"}:
        ap.print_help(sys.stderr)
        sys.exit(2)

    try:
        args = ap.parse_args(argv)
        command = registry.get_command(args.cmd)

        if command:
            exit_code = command.execute(args)
            sys.exit(exit_code)
        else:
            ap.print_help(sys.stderr)
            sys.exit(2)

    except Exception as e:
        print(f"Error parsing arguments: {e}", file=sys.stderr)
        sys.exit(2)


def _handle_special_cases(argv: list[str], registry: CommandRegistry) -> int | None:
    """Handle special command-line cases that don't require full parsing."""
    if not argv or argv[0] in {"-h", "--help"}:
        ap = _build_parser()
        ap.print_help(sys.stderr if argv else sys.stdout)
        return 0

    if argv[0] in {"--version", "-V"}:
        command = registry.get_command("version")
        return command.execute(argparse.Namespace()) if command else 2

    if "--list-templates" in argv:
        command = registry.get_command("list-templates")
        return command.execute(argparse.Namespace()) if command else 2

    return None  # Continue with normal processing


__all__ = ["main"]
