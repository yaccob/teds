"""Unit tests for TeDS schema cache functionality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from teds_core.cache import SchemaCacheError, TedsSchemaCache


class TestTedsSchemaCacheBasics(unittest.TestCase):
    """Test basic cache functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.cache = TedsSchemaCache(self.temp_path)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_cache_initialization_creates_empty_cache(self):
        """Test that cache initializes with empty structure."""
        self.cache.load()

        self.assertEqual(self.cache.cache_data["cache_version"], "1.0")
        self.assertIn("created", self.cache.cache_data)
        self.assertIn("last_updated", self.cache.cache_data)
        self.assertEqual(self.cache.cache_data["entries"], {})

    def test_cache_file_creation_on_save(self):
        """Test that cache file is created when saving."""
        self.cache.load()
        self.cache.save()

        cache_file = self.temp_path / ".teds-schema-cache.json"
        self.assertTrue(cache_file.exists())

        # Verify JSON structure
        with open(cache_file) as f:
            data = json.load(f)
        self.assertEqual(data["cache_version"], "1.0")
        self.assertIn("entries", data)

    def test_context_manager_loads_and_saves(self):
        """Test that context manager automatically loads and saves cache."""
        cache_file = self.temp_path / ".teds-schema-cache.json"

        with TedsSchemaCache(self.temp_path) as cache:
            # Should create cache structure
            self.assertIn("cache_version", cache.cache_data)
            cache.dirty = True  # Mark as dirty to force save

        # Cache file should exist after context exit
        self.assertTrue(cache_file.exists())

    def test_get_stats_returns_correct_information(self):
        """Test that get_stats returns accurate cache statistics."""
        self.cache.load()
        stats = self.cache.get_stats()

        self.assertIn("cache_file", stats)
        self.assertIn("cache_size_bytes", stats)
        self.assertIn("cached_files", stats)
        self.assertIn("cached_pointers", stats)
        self.assertEqual(stats["cached_files"], 0)
        self.assertEqual(stats["cached_pointers"], 0)

    def test_clear_empties_cache(self):
        """Test that clear() removes all cache entries."""
        self.cache.load()

        # Add fake entry
        self.cache.cache_data["entries"]["fake_hash"] = {"test": "data"}

        self.cache.clear()
        self.assertEqual(self.cache.cache_data["entries"], {})
        self.assertTrue(self.cache.dirty)


class TestTedsSchemaCacheFileOperations(unittest.TestCase):
    """Test cache operations with actual schema files."""

    def setUp(self):
        """Set up test fixtures with temporary schema files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.cache = TedsSchemaCache(self.temp_path)

        # Create test schema file
        self.schema_file = self.temp_path / "test_schema.yaml"
        self.schema_content = """
type: object
properties:
  id:
    type: integer
  name:
    type: string
components:
  schemas:
    User:
      type: object
      properties:
        username:
          type: string
        email:
          type: string
"""
        self.schema_file.write_text(self.schema_content)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_get_schema_loads_and_caches_full_document(self):
        """Test loading complete schema document."""
        self.cache.load()

        schema = self.cache.get_schema(self.schema_file, "#/")

        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        self.assertIn("components", schema)

        # Verify caching occurred
        self.assertTrue(self.cache.dirty)
        stats = self.cache.get_stats()
        self.assertEqual(stats["cached_files"], 1)
        # With preemptive caching, multiple pointers are cached (root + extracted schemas)
        self.assertGreaterEqual(stats["cached_pointers"], 1)

    def test_get_schema_extracts_json_pointer(self):
        """Test extracting specific schema parts via JSON pointer."""
        self.cache.load()

        user_schema = self.cache.get_schema(
            self.schema_file, "#/components/schemas/User"
        )

        self.assertEqual(user_schema["type"], "object")
        self.assertIn("username", user_schema["properties"])
        self.assertIn("email", user_schema["properties"])

    def test_get_schema_cache_hit_avoids_file_read(self):
        """Test that cache hit doesn't re-read file."""
        self.cache.load()

        # First access - should read file
        schema1 = self.cache.get_schema(self.schema_file, "#/")

        # Mock file reading to verify it's not called again
        with patch("pathlib.Path.read_text") as mock_read:
            schema2 = self.cache.get_schema(self.schema_file, "#/")
            mock_read.assert_not_called()

        self.assertEqual(schema1, schema2)

    def test_get_schema_file_not_found_raises_error(self):
        """Test error handling for non-existent files."""
        self.cache.load()

        non_existent = self.temp_path / "missing.yaml"

        with self.assertRaises(SchemaCacheError) as cm:
            self.cache.get_schema(non_existent, "#/")

        self.assertIn("not found", str(cm.exception))

    def test_get_schema_invalid_pointer_raises_error(self):
        """Test error handling for invalid JSON pointers."""
        self.cache.load()

        with self.assertRaises(SchemaCacheError) as cm:
            self.cache.get_schema(self.schema_file, "#/nonexistent/path")

        self.assertIn("not found", str(cm.exception))

    def test_invalidate_file_removes_cache_entry(self):
        """Test that file invalidation removes cache entries."""
        self.cache.load()

        # Cache the file
        self.cache.get_schema(self.schema_file, "#/")
        self.assertEqual(self.cache.get_stats()["cached_files"], 1)

        # Invalidate
        self.cache.invalidate_file(self.schema_file)
        self.assertEqual(self.cache.get_stats()["cached_files"], 0)
        self.assertTrue(self.cache.dirty)


class TestTedsSchemaCacheInvalidation(unittest.TestCase):
    """Test cache invalidation based on file changes."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.cache = TedsSchemaCache(self.temp_path)

        self.schema_file = self.temp_path / "test_schema.yaml"
        self.schema_file.write_text(
            "type: object\nproperties:\n  id:\n    type: integer"
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_file_modification_invalidates_cache(self):
        """Test that modified files invalidate cache."""
        self.cache.load()

        # Cache initial content
        schema1 = self.cache.get_schema(self.schema_file, "#/")
        self.assertEqual(schema1["type"], "object")

        # Modify file content
        self.schema_file.write_text("type: string")

        # Should detect change and reload
        schema2 = self.cache.get_schema(self.schema_file, "#/")
        self.assertEqual(schema2["type"], "string")
        self.assertNotEqual(schema1, schema2)

    def test_file_size_change_invalidates_cache(self):
        """Test that file size changes invalidate cache."""
        self.cache.load()

        # Cache initial content
        original_content = self.schema_file.read_text()
        self.cache.get_schema(self.schema_file, "#/")

        # Change file size (add content)
        self.schema_file.write_text(original_content + "\ndescription: Modified")

        # Should detect size change and reload
        new_schema = self.cache.get_schema(self.schema_file, "#/")
        self.assertIn("description", new_schema)


class TestTedsSchemaCacheErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.cache = TedsSchemaCache(self.temp_path)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_corrupted_cache_file_reinitializes(self):
        """Test handling of corrupted cache files."""
        cache_file = self.temp_path / ".teds-schema-cache.json"

        # Create corrupted cache file
        cache_file.write_text("invalid json content")

        # Should reinitialize without error
        self.cache.load()
        self.assertEqual(self.cache.cache_data["cache_version"], "1.0")
        self.assertTrue(self.cache.dirty)

    def test_old_cache_version_reinitializes(self):
        """Test handling of old cache format versions."""
        cache_file = self.temp_path / ".teds-schema-cache.json"

        # Create old version cache
        old_cache = {"cache_version": "0.5", "entries": {}}
        with open(cache_file, "w") as f:
            json.dump(old_cache, f)

        # Should reinitialize with current version
        self.cache.load()
        self.assertEqual(self.cache.cache_data["cache_version"], "1.0")
        self.assertTrue(self.cache.dirty)

    def test_relative_path_resolution(self):
        """Test that relative paths are resolved correctly."""
        schema_file = self.temp_path / "schema.yaml"
        schema_file.write_text("type: object")

        self.cache.load()

        # Use relative path
        relative_path = "schema.yaml"
        schema = self.cache.get_schema(relative_path, "#/")

        self.assertEqual(schema["type"], "object")

    def test_absolute_path_handling(self):
        """Test that absolute paths work correctly."""
        schema_file = self.temp_path / "schema.yaml"
        schema_file.write_text("type: string")

        self.cache.load()

        # Use absolute path
        abs_path = str(schema_file.resolve())
        schema = self.cache.get_schema(abs_path, "#/")

        self.assertEqual(schema["type"], "string")


if __name__ == "__main__":
    unittest.main()
