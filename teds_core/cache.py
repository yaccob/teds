"""TeDS Schema Cache with persistent storage."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import TedsError
from .yamlio import yaml_loader


class SchemaCacheError(TedsError):
    """Schema cache related errors."""


class TedsSchemaCache:
    """Persistent cache for schema files and JSON pointer references.

    Cache structure:
    {
        "cache_version": "1.0",
        "created": "2025-09-30T10:30:00Z",
        "last_updated": "2025-09-30T14:22:15Z",
        "entries": {
            "sha256_hash": {
                "file_path": "/absolute/path/to/schema.yaml",
                "file_size": 2048,
                "last_modified": "2025-09-30T14:20:00Z",
                "pointers": {
                    "#/components/schemas/User": {
                        "schema": {...},
                        "cached_at": "2025-09-30T14:22:15Z",
                        "dependencies": ["#/components/schemas/Address"]
                    }
                }
            }
        }
    }
    """

    CACHE_VERSION = "1.0"
    CACHE_FILENAME = ".teds-schema-cache.json"

    def __init__(self, project_root: str | Path = "."):
        """Initialize cache with project root directory."""
        self.project_root = Path(project_root).resolve()
        self.cache_file = self.project_root / self.CACHE_FILENAME
        self.cache_data: dict[str, Any] = {}
        self.dirty = False

    def load(self) -> None:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    self.cache_data = json.load(f)

                # Validate cache version
                if self.cache_data.get("cache_version") != self.CACHE_VERSION:
                    self._init_empty_cache()
                    self.dirty = True

            except (json.JSONDecodeError, OSError):
                # Corrupted cache file - reinitialize
                self._init_empty_cache()
                self.dirty = True
        else:
            self._init_empty_cache()
            self.dirty = True

    def save(self) -> None:
        """Save cache to disk if dirty."""
        if self.dirty:
            self.cache_data["last_updated"] = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            try:
                # Atomic write using temporary file
                temp_file = self.cache_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
                temp_file.replace(self.cache_file)
                self.dirty = False
            except OSError as e:
                raise SchemaCacheError(f"Failed to save cache: {e}") from e

    def get_schema(
        self, file_path: str | Path, json_pointer: str = "#/"
    ) -> dict[str, Any]:
        """Get schema from cache or load from file.

        Args:
            file_path: Path to schema file (relative or absolute)
            json_pointer: JSON pointer (e.g., "#/components/schemas/User")

        Returns:
            Resolved schema object

        Raises:
            SchemaCacheError: If file not found or invalid pointer
        """
        abs_path = self._resolve_path(file_path)

        if not abs_path.exists():
            raise SchemaCacheError(f"Schema file not found: {abs_path}")

        file_hash = self._compute_file_hash(abs_path)

        # Check if cache entry is valid
        if self._is_cache_valid(file_hash, abs_path, json_pointer):
            return self.cache_data["entries"][file_hash]["pointers"][json_pointer][
                "schema"
            ]

        # Cache miss - load and cache the schema
        return self._load_and_cache_schema(abs_path, file_hash, json_pointer)

    def invalidate_file(self, file_path: str | Path) -> None:
        """Invalidate all cache entries for a file."""
        abs_path = self._resolve_path(file_path)
        file_hash = self._compute_file_hash(abs_path)

        if file_hash in self.cache_data.get("entries", {}):
            del self.cache_data["entries"][file_hash]
            self.dirty = True

    def clear(self) -> None:
        """Clear entire cache."""
        self._init_empty_cache()
        self.dirty = True

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        entries = self.cache_data.get("entries", {})
        total_pointers = sum(
            len(entry.get("pointers", {})) for entry in entries.values()
        )

        cache_size = 0
        if self.cache_file.exists():
            cache_size = self.cache_file.stat().st_size

        return {
            "cache_file": str(self.cache_file),
            "cache_size_bytes": cache_size,
            "cached_files": len(entries),
            "cached_pointers": total_pointers,
            "last_updated": self.cache_data.get("last_updated"),
            "created": self.cache_data.get("created"),
        }

    def __enter__(self) -> TedsSchemaCache:
        """Context manager entry."""
        self.load()
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any
    ) -> None:
        """Context manager exit - save if dirty."""
        self.save()

    def _init_empty_cache(self) -> None:
        """Initialize empty cache structure."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.cache_data = {
            "cache_version": self.CACHE_VERSION,
            "created": now,
            "last_updated": now,
            "entries": {},
        }

    def _resolve_path(self, file_path: str | Path) -> Path:
        """Resolve file path to absolute path."""
        path = Path(file_path)
        if path.is_absolute():
            return path.resolve()
        else:
            return (self.project_root / path).resolve()

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        if not file_path.exists():
            raise SchemaCacheError(f"File not found: {file_path}")

        try:
            content = file_path.read_bytes()
            return hashlib.sha1(content).hexdigest()
        except OSError as e:
            raise SchemaCacheError(f"Failed to read file {file_path}: {e}") from e

    def _is_cache_valid(
        self, file_hash: str, file_path: Path, json_pointer: str
    ) -> bool:
        """Check if cache entry is valid."""
        entries = self.cache_data.get("entries", {})

        if file_hash not in entries:
            return False

        entry = entries[file_hash]

        # Check if file path matches (in case of hash collision)
        if entry.get("file_path") != str(file_path):
            return False

        # Check if file has been modified
        try:
            stat = file_path.stat()
            if entry.get("file_size") != stat.st_size:
                return False

            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
            if entry.get("last_modified") != last_modified:
                return False
        except OSError:
            return False

        # Check if specific pointer is cached
        pointers = entry.get("pointers", {})
        return json_pointer in pointers

    def _load_and_cache_schema(
        self, file_path: Path, file_hash: str, json_pointer: str
    ) -> dict[str, Any]:
        """Load schema from file and cache it with optimized multi-pointer extraction."""
        try:
            # Load the full schema document
            content = file_path.read_text(encoding="utf-8")
            full_schema = yaml_loader.load(content) or {}

            # Update cache entry metadata
            stat = file_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
            cached_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            entries = self.cache_data.setdefault("entries", {})
            if file_hash not in entries:
                entries[file_hash] = {
                    "file_path": str(file_path),
                    "file_size": stat.st_size,
                    "last_modified": last_modified,
                    "pointers": {},
                }

            # Extract the requested pointer
            schema_fragment = self._extract_pointer(full_schema, json_pointer)

            # OPTIMIZATION: Pre-cache common schema pointers from components/schemas
            # This dramatically improves performance for subsequent schema accesses
            self._preemptively_cache_common_pointers(
                entries[file_hash], full_schema, cached_at
            )

            # Cache the specific requested pointer (might already be cached by preemptive caching)
            if json_pointer not in entries[file_hash]["pointers"]:
                entries[file_hash]["pointers"][json_pointer] = {
                    "schema": schema_fragment,
                    "cached_at": cached_at,
                }

            self.dirty = True
            return schema_fragment

        except Exception as e:
            raise SchemaCacheError(
                f"Failed to load schema from {file_path}#{json_pointer}: {e}"
            ) from e

    def _extract_pointer(
        self, document: dict[str, Any], json_pointer: str
    ) -> dict[str, Any]:
        """Extract schema fragment using JSON pointer."""
        if json_pointer == "#/" or json_pointer == "#":
            return document

        # Remove leading # and /
        pointer = json_pointer.lstrip("#/")
        if not pointer:
            return document

        # Split pointer into parts and decode
        parts = []
        for part in pointer.split("/"):
            # JSON Pointer unescaping: ~1 -> /, ~0 -> ~
            part = part.replace("~1", "/").replace("~0", "~")
            parts.append(part)

        # Traverse the document
        current = document
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise SchemaCacheError(f"JSON pointer not found: {json_pointer}")

        return current if isinstance(current, dict) else {}

    def _preemptively_cache_common_pointers(
        self, cache_entry: dict[str, Any], full_schema: dict[str, Any], cached_at: str
    ) -> None:
        """Pre-cache common schema pointers to improve subsequent access performance."""
        # Cache common OpenAPI/AsyncAPI structure pointers
        # Note: common_patterns could be used for future pattern-based caching

        # Try to find and cache all schemas in components/schemas
        try:
            components = full_schema.get("components", {})
            schemas = components.get("schemas", {})

            if schemas:
                # Cache the container
                cache_entry["pointers"]["#/components/schemas"] = {
                    "schema": schemas,
                    "cached_at": cached_at,
                }

                # Cache individual schemas
                for schema_name, schema_def in schemas.items():
                    if isinstance(schema_def, dict):
                        pointer = f"#/components/schemas/{schema_name}"
                        cache_entry["pointers"][pointer] = {
                            "schema": schema_def,
                            "cached_at": cached_at,
                        }
        except Exception:
            # Don't fail on preemptive caching errors
            pass

        # Try to find and cache definitions (JSON Schema draft-04/07 style)
        try:
            definitions = full_schema.get("definitions", {})
            if definitions:
                cache_entry["pointers"]["#/definitions"] = {
                    "schema": definitions,
                    "cached_at": cached_at,
                }

                for def_name, def_schema in definitions.items():
                    if isinstance(def_schema, dict):
                        pointer = f"#/definitions/{def_name}"
                        cache_entry["pointers"][pointer] = {
                            "schema": def_schema,
                            "cached_at": cached_at,
                        }
        except Exception:
            pass

    def _extract_dependencies(self, schema: dict[str, Any]) -> list[str]:
        """Extract $ref dependencies from schema (simple extraction)."""
        dependencies = []

        def collect_refs(obj: Any) -> None:
            if isinstance(obj, dict):
                if "$ref" in obj and isinstance(obj["$ref"], str):
                    ref = obj["$ref"]
                    if ref.startswith("#/"):
                        dependencies.append(ref)
                for value in obj.values():
                    collect_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    collect_refs(item)

        collect_refs(schema)
        return dependencies
