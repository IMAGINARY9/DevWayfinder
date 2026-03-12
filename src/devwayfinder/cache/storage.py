"""File-based cache storage backend.

Implements content-hash-based caching stored in `.devwayfinder/cache/`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry:
    """A cached item with metadata."""

    key: str
    data: dict[str, Any]
    content_hash: str
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    tags: list[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Create from dictionary."""
        return cls(**data)


class CacheStorage:
    """File-based cache storage.

    Stores cached data in `.devwayfinder/cache/` directory structure:
    - analysis/: Analysis results per file
    - summaries/: LLM summaries keyed by content hash + model
    """

    CACHE_VERSION = "1"
    ANALYSIS_DIR = "analysis"
    SUMMARIES_DIR = "summaries"

    def __init__(
        self,
        cache_dir: Path | None = None,
        *,
        project_root: Path | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Initialize cache storage.

        Args:
            cache_dir: Explicit cache directory path
            project_root: Project root to derive cache dir from
            ttl_seconds: Default time-to-live for cache entries (None = no expiry)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        elif project_root:
            self.cache_dir = Path(project_root) / ".devwayfinder" / "cache"
        else:
            self.cache_dir = Path.cwd() / ".devwayfinder" / "cache"

        self.ttl_seconds = ttl_seconds
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure cache directory structure exists."""
        (self.cache_dir / self.ANALYSIS_DIR).mkdir(parents=True, exist_ok=True)
        (self.cache_dir / self.SUMMARIES_DIR).mkdir(parents=True, exist_ok=True)

        # Write version file
        version_file = self.cache_dir / "VERSION"
        if not version_file.exists():
            version_file.write_text(self.CACHE_VERSION)

    @staticmethod
    def compute_content_hash(content: str | bytes) -> str:
        """Compute SHA-256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hexadecimal hash string
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_cache_path(self, category: str, key: str) -> Path:
        """Get path to cache file.

        Args:
            category: Cache category (analysis, summaries)
            key: Cache key

        Returns:
            Path to cache file
        """
        # Use first 2 characters of key as subdirectory for better distribution
        subdir = key[:2] if len(key) >= 2 else "00"
        return self.cache_dir / category / subdir / f"{key}.json"

    def get(self, category: str, key: str) -> CacheEntry | None:
        """Retrieve a cached entry.

        Args:
            category: Cache category
            key: Cache key

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        cache_path = self._get_cache_path(category, key)

        if not cache_path.exists():
            logger.debug("Cache miss: %s/%s", category, key[:16])
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            entry = CacheEntry.from_dict(data)

            if entry.is_expired():
                logger.debug("Cache expired: %s/%s", category, key[:16])
                self.delete(category, key)
                return None

            logger.debug("Cache hit: %s/%s", category, key[:16])
            return entry

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Invalid cache entry %s/%s: %s", category, key[:16], e)
            self.delete(category, key)
            return None

    def set(
        self,
        category: str,
        key: str,
        data: dict[str, Any],
        content_hash: str,
        *,
        ttl_seconds: int | None = None,
        tags: list[str] | None = None,
    ) -> CacheEntry:
        """Store a cache entry.

        Args:
            category: Cache category
            key: Cache key
            data: Data to cache
            content_hash: Hash of the original content (for invalidation)
            ttl_seconds: Override default TTL
            tags: Optional tags for grouping

        Returns:
            The created CacheEntry
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        expires_at = time.time() + ttl if ttl else None

        entry = CacheEntry(
            key=key,
            data=data,
            content_hash=content_hash,
            created_at=time.time(),
            expires_at=expires_at,
            tags=tags or [],
        )

        cache_path = self._get_cache_path(category, key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(entry.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        logger.debug("Cached: %s/%s", category, key[:16])
        return entry

    def delete(self, category: str, key: str) -> bool:
        """Delete a cache entry.

        Args:
            category: Cache category
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        cache_path = self._get_cache_path(category, key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug("Deleted: %s/%s", category, key[:16])
            return True
        return False

    def clear(self, category: str | None = None) -> int:
        """Clear cache entries.

        Args:
            category: Category to clear, or None for all

        Returns:
            Number of entries deleted
        """
        count = 0
        categories = [category] if category else [self.ANALYSIS_DIR, self.SUMMARIES_DIR]

        for cat in categories:
            cat_path = self.cache_dir / cat
            if cat_path.exists():
                for subdir in cat_path.iterdir():
                    if subdir.is_dir():
                        for cache_file in subdir.glob("*.json"):
                            cache_file.unlink()
                            count += 1

        logger.info("Cleared %d cache entries", count)
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        stats: dict[str, Any] = {
            "cache_dir": str(self.cache_dir),
            "categories": {},
            "total_entries": 0,
            "total_size_bytes": 0,
        }

        for category in [self.ANALYSIS_DIR, self.SUMMARIES_DIR]:
            cat_path = self.cache_dir / category
            cat_stats = {"entries": 0, "size_bytes": 0}

            if cat_path.exists():
                for subdir in cat_path.iterdir():
                    if subdir.is_dir():
                        for cache_file in subdir.glob("*.json"):
                            cat_stats["entries"] += 1
                            cat_stats["size_bytes"] += cache_file.stat().st_size

            stats["categories"][category] = cat_stats
            stats["total_entries"] += cat_stats["entries"]
            stats["total_size_bytes"] += cat_stats["size_bytes"]

        return stats

    def invalidate_by_hash(self, category: str, content_hash: str) -> int:
        """Invalidate entries matching a content hash.

        Args:
            category: Category to search
            content_hash: Hash to match

        Returns:
            Number of entries invalidated
        """
        count = 0
        cat_path = self.cache_dir / category
        if not cat_path.exists():
            return 0

        for subdir in cat_path.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.glob("*.json"):
                    try:
                        data = json.loads(cache_file.read_text(encoding="utf-8"))
                        if data.get("content_hash") == content_hash:
                            cache_file.unlink()
                            count += 1
                    except (json.JSONDecodeError, KeyError):
                        pass

        return count
