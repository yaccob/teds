from __future__ import annotations

import argparse
import logging
import logging.config
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from ruamel.yaml import YAML

from .cache import TedsSchemaCache
from .errors import TedsError
from .generate import generate_from_source_config, parse_generate_config
from .validate import validate_file
from .version import get_version, recommended_minor_str, supported_spec_range_str


def setup_logging():
    """Setup logging from YAML config with environment variable override."""
    # Find the logging config file
    config_path = Path(__file__).parent.parent / "logging.yaml"

    if config_path.exists():
        yaml = YAML(typ="safe", pure=True)
        with open(config_path) as f:
            config = yaml.load(f)

        # Override log level from environment variable if set
        env_level = os.getenv("LOGLEVEL", "").upper()
        if (
            env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            and "loggers" in config
            and "teds_core" in config["loggers"]
        ):
            # Set the teds_core logger level from environment
            config["loggers"]["teds_core"]["level"] = env_level

        logging.config.dictConfig(config)
    else:
        # Fallback to basic config
        level = os.getenv("LOGLEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, level, logging.INFO),
            format="%(name)s:%(levelname)s: %(message)s",
            stream=sys.stderr,
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
            with TedsSchemaCache() as cache:
                pairs, rc = run_report_per_spec(
                    [Path(s) for s in args.spec], tpl_id, args.output_level, cache
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
        with TedsSchemaCache() as cache:
            for spec in args.spec:
                spec_path = Path(spec)
                if args.in_place:
                    print(f"Updating {spec_path}", file=sys.stderr)
                else:
                    print(f"Verifying {spec_path}", file=sys.stderr)
                rc_all = max(
                    rc_all,
                    validate_file(spec_path, args.output_level, args.in_place, cache),
                )
        return rc_all


class GenerateCommand(Command):
    """Command to generate test specifications."""

    def execute(self, args: argparse.Namespace) -> int:
        self._configure_network(args)

        try:
            with TedsSchemaCache() as cache:
                # Process each mapping argument
                for mapping_str in args.mapping:
                    config = parse_generate_config(mapping_str)

                    # All inputs are now normalized to dict format by parse_generate_config
                    if not isinstance(config, dict):
                        raise TedsError(
                            f"Unexpected configuration format: {type(config)}"
                        )

                    # Use unified processing pipeline
                    base_dir = Path.cwd()
                    # Status messages will be handled inside generate_from_source_config
                    generate_from_source_config(config, base_dir, cache)
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


class CacheCommand(Command):
    """Command for cache management operations."""

    def execute(self, args: argparse.Namespace) -> int:
        if args.cache_action == "status":
            return self._handle_status()
        elif args.cache_action == "clear":
            return self._handle_clear()
        elif args.cache_action == "stats":
            return self._handle_stats()
        else:
            print(f"Unknown cache action: {args.cache_action}", file=sys.stderr)
            return 1

    def _handle_status(self) -> int:
        """Show cache status."""
        try:
            with TedsSchemaCache() as cache:
                stats = cache.get_stats()

                if not Path(stats["cache_file"]).exists():
                    print("Cache file does not exist")
                    return 0

                print("TeDS Schema Cache Status:")
                print(
                    f"- Cache file: {stats['cache_file']} ({stats['cache_size_bytes']} bytes)"
                )
                print(f"- Cached files: {stats['cached_files']}")
                print(f"- Cached pointers: {stats['cached_pointers']}")
                print(f"- Last updated: {stats.get('last_updated', 'Never')}")
                print(f"- Created: {stats.get('created', 'Unknown')}")

        except Exception as e:
            print(f"Error reading cache: {e}", file=sys.stderr)
            return 1

        return 0

    def _handle_clear(self) -> int:
        """Clear cache."""
        try:
            with TedsSchemaCache() as cache:
                cache.clear()
                print("Cache cleared successfully")

        except Exception as e:
            print(f"Error clearing cache: {e}", file=sys.stderr)
            return 1

        return 0

    def _handle_stats(self) -> int:
        """Show detailed cache statistics."""
        try:
            with TedsSchemaCache() as cache:
                stats = cache.get_stats()

                print("TeDS Schema Cache Statistics:")
                print(f"Cache Version: {cache.CACHE_VERSION}")
                print(f"Cache File: {stats['cache_file']}")
                print(f"File Size: {stats['cache_size_bytes']} bytes")
                print(f"Cached Files: {stats['cached_files']}")
                print(f"Cached Pointers: {stats['cached_pointers']}")
                print(f"Created: {stats.get('created', 'Unknown')}")
                print(f"Last Updated: {stats.get('last_updated', 'Never')}")

                # Show cache entries if they exist
                if stats["cached_files"] > 0:
                    print("\nCached Schema Files:")
                    entries = cache.cache_data.get("entries", {})
                    for file_hash, entry in entries.items():
                        file_path = entry.get("file_path", "Unknown")
                        pointer_count = len(entry.get("pointers", {}))
                        print(
                            f"  {file_path} ({pointer_count} pointers, hash: {file_hash[:12]}...)"
                        )

        except Exception as e:
            print(f"Error reading cache stats: {e}", file=sys.stderr)
            return 1

        return 0


class ServeCommand(Command):
    """Command for starting HTTP API server."""

    def execute(self, args: argparse.Namespace) -> int:
        """Start the HTTP API server."""
        try:
            import uvicorn

            from .http_api import create_teds_app

            # Create FastAPI app
            root_dir = getattr(args, "root", os.getcwd())
            app = create_teds_app(root_directory=root_dir)

            # Set port in app state for status endpoint
            port = getattr(args, "port", 8000)
            app.state.port = port

            # Configure uvicorn
            config = uvicorn.Config(
                app=app,
                host=getattr(args, "host", "localhost"),
                port=port,
                log_level="info",
            )

            print(
                f"Starting TeDS HTTP API server on http://{config.host}:{config.port}"
            )
            print(f"Root directory: {root_dir}")
            print("Press Ctrl+C to stop")

            # Start server
            server = uvicorn.Server(config)
            server.run()

        except KeyboardInterrupt:
            print("\nServer stopped")
            return 0
        except ImportError as e:
            print(f"Error: Missing dependencies for HTTP server: {e}", file=sys.stderr)
            print("Install with: pip install fastapi uvicorn", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"Error starting server: {e}", file=sys.stderr)
            return 2

        return 0


class CommandRegistry:
    """Registry for CLI commands."""

    def __init__(self):
        self._commands: dict[str, Command] = {
            "version": VersionCommand(),
            "list-templates": ListTemplatesCommand(),
            "verify": VerifyCommand(),
            "generate": GenerateCommand(),
            "cache": CacheCommand(),
            "serve": ServeCommand(),
        }

    def get_command(self, name: str) -> Command | None:
        """Get command by name."""
        return self._commands.get(name)

    def has_command(self, name: str) -> bool:
        """Check if command exists."""
        return name in self._commands


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

    # Cache management subcommand
    p_cache = sub.add_parser(
        "cache",
        help="Manage schema cache",
        description="Manage the persistent schema cache used to speed up operations.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_cache.add_argument(
        "cache_action",
        choices=["status", "clear", "stats"],
        help=(
            "Cache action to perform:\n"
            "  status  show basic cache information\n"
            "  clear   clear entire cache\n"
            "  stats   show detailed cache statistics"
        ),
    )

    # HTTP API server subcommand
    p_serve = sub.add_parser(
        "serve",
        help="Start HTTP API server",
        description="Start a local HTTP API server for TeDS operations.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    p_serve.add_argument(
        "--host",
        default="localhost",
        help="Host to bind the server to (default: localhost)",
    )
    p_serve.add_argument(
        "--root",
        default=os.getcwd(),
        help="Root directory for file operations (default: current working directory)",
    )

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

    if not argv or argv[0] not in {"verify", "generate", "cache", "serve"}:
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
