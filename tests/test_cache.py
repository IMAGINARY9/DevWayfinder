"""Tests for the caching layer."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from devwayfinder.cache.manager import CacheManager
from devwayfinder.cache.storage import CacheEntry, CacheStorage

# =============================================================================
# CacheEntry Tests
# =============================================================================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_creation(self) -> None:
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            data={"imports": ["os", "sys"]},
            content_hash="abc123",
        )
        assert entry.key == "test_key"
        assert entry.data == {"imports": ["os", "sys"]}
        assert entry.content_hash == "abc123"
        assert entry.expires_at is None

    def test_entry_not_expired(self) -> None:
        """Test that entry without expiry never expires."""
        entry = CacheEntry(
            key="test",
            data={},
            content_hash="abc",
        )
        assert not entry.is_expired()

    def test_entry_expired(self) -> None:
        """Test expired entry detection."""
        entry = CacheEntry(
            key="test",
            data={},
            content_hash="abc",
            expires_at=time.time() - 100,  # Expired 100 seconds ago
        )
        assert entry.is_expired()

    def test_entry_not_yet_expired(self) -> None:
        """Test entry that expires in the future."""
        entry = CacheEntry(
            key="test",
            data={},
            content_hash="abc",
            expires_at=time.time() + 3600,  # Expires in 1 hour
        )
        assert not entry.is_expired()

    def test_round_trip_serialization(self) -> None:
        """Test to_dict and from_dict."""
        original = CacheEntry(
            key="test_key",
            data={"foo": "bar"},
            content_hash="hash123",
            tags=["analysis", "python"],
        )

        as_dict = original.to_dict()
        restored = CacheEntry.from_dict(as_dict)

        assert restored.key == original.key
        assert restored.data == original.data
        assert restored.content_hash == original.content_hash
        assert restored.tags == original.tags


# =============================================================================
# CacheStorage Tests
# =============================================================================


class TestCacheStorage:
    """Tests for CacheStorage backend."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> CacheStorage:
        """Create a temporary cache storage."""
        return CacheStorage(cache_dir=tmp_path / "cache")

    def test_directory_structure_created(self, storage: CacheStorage) -> None:
        """Test that cache directories are created."""
        assert storage.cache_dir.exists()
        assert (storage.cache_dir / "analysis").exists()
        assert (storage.cache_dir / "summaries").exists()
        assert (storage.cache_dir / "VERSION").exists()

    def test_compute_content_hash(self) -> None:
        """Test content hashing."""
        hash1 = CacheStorage.compute_content_hash("hello world")
        hash2 = CacheStorage.compute_content_hash("hello world")
        hash3 = CacheStorage.compute_content_hash("different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_file_hash(self, tmp_path: Path) -> None:
        """Test file hashing."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = CacheStorage.compute_file_hash(test_file)
        test_file.write_text("modified content")
        hash2 = CacheStorage.compute_file_hash(test_file)

        assert hash1 != hash2

    def test_set_and_get(self, storage: CacheStorage) -> None:
        """Test storing and retrieving cache entries."""
        data = {"imports": ["os", "sys"], "exports": ["main"]}
        storage.set("analysis", "mykey", data, "contenthash123")

        entry = storage.get("analysis", "mykey")
        assert entry is not None
        assert entry.data == data
        assert entry.content_hash == "contenthash123"

    def test_get_nonexistent(self, storage: CacheStorage) -> None:
        """Test getting a missing entry."""
        entry = storage.get("analysis", "nonexistent")
        assert entry is None

    def test_delete(self, storage: CacheStorage) -> None:
        """Test deleting an entry."""
        storage.set("analysis", "to_delete", {"data": 1}, "hash")
        assert storage.get("analysis", "to_delete") is not None

        result = storage.delete("analysis", "to_delete")
        assert result is True
        assert storage.get("analysis", "to_delete") is None

    def test_delete_nonexistent(self, storage: CacheStorage) -> None:
        """Test deleting a missing entry."""
        result = storage.delete("analysis", "does_not_exist")
        assert result is False

    def test_clear_category(self, storage: CacheStorage) -> None:
        """Test clearing a specific category."""
        storage.set("analysis", "key1", {"a": 1}, "h1")
        storage.set("analysis", "key2", {"b": 2}, "h2")
        storage.set("summaries", "key3", {"c": 3}, "h3")

        count = storage.clear("analysis")
        assert count == 2
        assert storage.get("analysis", "key1") is None
        assert storage.get("summaries", "key3") is not None

    def test_clear_all(self, storage: CacheStorage) -> None:
        """Test clearing all categories."""
        storage.set("analysis", "key1", {"a": 1}, "h1")
        storage.set("summaries", "key2", {"b": 2}, "h2")

        count = storage.clear()
        assert count == 2

    def test_ttl_expiry(self, storage: CacheStorage) -> None:
        """Test that entries with TTL expire."""
        storage.set("analysis", "expiring", {"x": 1}, "hash", ttl_seconds=-1)

        time.sleep(0.1)
        entry = storage.get("analysis", "expiring")
        assert entry is None

    def test_get_stats(self, storage: CacheStorage) -> None:
        """Test cache statistics."""
        storage.set("analysis", "key1", {"a": 1}, "h1")
        storage.set("summaries", "key2", {"b": 2}, "h2")

        stats = storage.get_stats()
        assert stats["total_entries"] == 2
        assert "categories" in stats
        assert stats["categories"]["analysis"]["entries"] == 1
        assert stats["categories"]["summaries"]["entries"] == 1


# =============================================================================
# CacheManager Tests
# =============================================================================


class TestCacheManager:
    """Tests for CacheManager."""

    @pytest.fixture
    def sample_project(self, tmp_path: Path) -> Path:
        """Create a sample project structure."""
        project = tmp_path / "project"
        project.mkdir()

        # Create some source files
        src = project / "src"
        src.mkdir()
        (src / "main.py").write_text("import os\ndef main(): pass")
        (src / "utils.py").write_text("def helper(): return 42")

        return project

    @pytest.fixture
    def manager(self, sample_project: Path) -> CacheManager:
        """Create a cache manager for the sample project."""
        return CacheManager(sample_project)

    def test_manager_creation(self, manager: CacheManager) -> None:
        """Test cache manager initialization."""
        assert manager.enabled
        assert manager.storage is not None

    def test_disabled_manager(self, sample_project: Path) -> None:
        """Test that disabled manager doesn't cache."""
        manager = CacheManager(sample_project, enabled=False)

        file_path = sample_project / "src" / "main.py"
        manager.set_analysis(file_path, {"imports": ["os"]})

        result = manager.get_analysis(file_path)
        assert result is None

    def test_analysis_cache(self, manager: CacheManager, sample_project: Path) -> None:
        """Test caching analysis results."""
        file_path = sample_project / "src" / "main.py"

        # Mock AnalysisResult-like object
        mock_result = MagicMock()
        mock_result.path = file_path
        mock_result.imports = ["os"]
        mock_result.exports = ["main"]
        mock_result.is_entry_point = True
        mock_result.language = "python"
        mock_result.metadata = {}

        manager.set_analysis(file_path, mock_result)

        cached = manager.get_analysis(file_path)
        assert cached is not None
        assert cached["imports"] == ["os"]
        assert cached["exports"] == ["main"]

    def test_analysis_freshness(self, manager: CacheManager, sample_project: Path) -> None:
        """Test cache freshness detection."""
        file_path = sample_project / "src" / "main.py"

        # Create cache entry
        manager.set_analysis(file_path, {
            "path": str(file_path),
            "imports": [],
            "exports": [],
            "is_entry_point": False,
            "language": "python",
            "metadata": {},
        })

        # Should be fresh
        assert manager.is_analysis_fresh(file_path)

        # Modify file
        file_path.write_text("modified content")

        # Should no longer be fresh
        assert not manager.is_analysis_fresh(file_path)

    def test_summary_cache(self, manager: CacheManager, sample_project: Path) -> None:
        """Test caching LLM summaries."""
        file_path = sample_project / "src" / "main.py"
        model_id = "gpt-4"
        summary = "This module provides the main entry point."

        manager.set_summary(file_path, model_id, summary)

        cached = manager.get_summary(file_path, model_id)
        assert cached == summary

    def test_summary_different_models(self, manager: CacheManager, sample_project: Path) -> None:
        """Test that different models have separate cache entries."""
        file_path = sample_project / "src" / "main.py"

        manager.set_summary(file_path, "gpt-4", "Summary from GPT-4")
        manager.set_summary(file_path, "llama-3", "Summary from LLama")

        assert manager.get_summary(file_path, "gpt-4") == "Summary from GPT-4"
        assert manager.get_summary(file_path, "llama-3") == "Summary from LLama"

    def test_metrics_cache(self, manager: CacheManager, sample_project: Path) -> None:
        """Test caching metrics."""
        file_path = sample_project / "src" / "main.py"
        metrics = {"loc": 100, "complexity": 5.5}

        manager.set_metrics(file_path, metrics)

        cached = manager.get_metrics(file_path)
        assert cached == metrics

    def test_invalidate_file(self, manager: CacheManager, sample_project: Path) -> None:
        """Test invalidating cache for a file."""
        file_path = sample_project / "src" / "main.py"

        manager.set_analysis(file_path, {
            "path": str(file_path),
            "imports": [],
            "exports": [],
            "is_entry_point": False,
            "language": "python",
            "metadata": {},
        })
        manager.set_metrics(file_path, {"loc": 50})

        manager.invalidate_file(file_path)

        assert manager.get_analysis(file_path) is None

    def test_hit_rate_tracking(self, manager: CacheManager, sample_project: Path) -> None:
        """Test hit rate statistics."""
        file_path = sample_project / "src" / "main.py"

        # Miss
        manager.get_analysis(file_path)

        # Set and hit
        manager.set_analysis(file_path, {
            "path": str(file_path),
            "imports": [],
            "exports": [],
            "is_entry_point": False,
            "language": "python",
            "metadata": {},
        })
        manager.get_analysis(file_path)

        rates = manager.hit_rate
        assert rates["analysis"] == 0.5  # 1 hit, 1 miss

    def test_get_stats(self, manager: CacheManager, sample_project: Path) -> None:
        """Test getting combined statistics."""
        file_path = sample_project / "src" / "main.py"

        manager.set_analysis(file_path, {
            "path": str(file_path),
            "imports": [],
            "exports": [],
            "is_entry_point": False,
            "language": "python",
            "metadata": {},
        })

        stats = manager.get_stats()
        assert "total_entries" in stats
        assert "session_stats" in stats
        assert "hit_rates" in stats
        assert stats["total_entries"] >= 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestCacheIntegration:
    """Integration tests for cache with real file operations."""

    @pytest.fixture
    def project_with_code(self, tmp_path: Path) -> Path:
        """Create a project with Python code."""
        project = tmp_path / "myproject"
        project.mkdir()

        main_py = project / "main.py"
        main_py.write_text("""
import os
import sys
from typing import List

def main(args: List[str]) -> int:
    '''Main entry point.'''
    print("Hello, world!")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
""")

        utils_py = project / "utils.py"
        utils_py.write_text("""
def helper() -> str:
    '''A helper function.'''
    return "help"
""")

        return project

    def test_full_workflow(self, project_with_code: Path) -> None:
        """Test complete caching workflow."""
        manager = CacheManager(project_with_code)
        main_py = project_with_code / "main.py"

        # 1. Cache miss
        assert manager.get_analysis(main_py) is None

        # 2. Analyze and cache
        analysis = {
            "path": str(main_py),
            "imports": ["os", "sys", "typing.List"],
            "exports": ["main"],
            "is_entry_point": True,
            "language": "python",
            "metadata": {},
        }
        manager.set_analysis(main_py, analysis)

        # 3. Cache hit
        cached = manager.get_analysis(main_py)
        assert cached is not None
        assert "os" in cached["imports"]

        # 4. File modified - cache should be stale
        original_content = main_py.read_text()
        main_py.write_text(original_content + "\n# Modified")

        # Key changes because content hash changes
        new_cached = manager.get_analysis(main_py)
        assert new_cached is None  # Miss because file changed

    def test_persist_across_instances(self, project_with_code: Path) -> None:
        """Test that cache persists across manager instances."""
        main_py = project_with_code / "main.py"

        # First manager - cache data
        manager1 = CacheManager(project_with_code)
        manager1.set_analysis(main_py, {
            "path": str(main_py),
            "imports": ["os"],
            "exports": [],
            "is_entry_point": False,
            "language": "python",
            "metadata": {},
        })

        # Second manager - should find cached data
        manager2 = CacheManager(project_with_code)
        cached = manager2.get_analysis(main_py)
        assert cached is not None
        assert cached["imports"] == ["os"]

    def test_summary_cache_invalidation_on_content_change(
        self, project_with_code: Path
    ) -> None:
        """Test that summary cache invalidates when file changes."""
        manager = CacheManager(project_with_code)
        main_py = project_with_code / "main.py"
        model_id = "test-model"

        # Cache a summary
        manager.set_summary(main_py, model_id, "Original summary")
        assert manager.get_summary(main_py, model_id) == "Original summary"

        # Modify file
        main_py.write_text("# Completely new content")

        # Summary should be invalidated (key changed due to content hash)
        assert manager.get_summary(main_py, model_id) is None
