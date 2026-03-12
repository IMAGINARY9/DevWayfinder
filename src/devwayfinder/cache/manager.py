"""Cache manager providing high-level caching API.

The CacheManager wraps CacheStorage to provide domain-specific caching
operations for analysis results and LLM summaries.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from devwayfinder.cache.storage import CacheStorage

if TYPE_CHECKING:
    from devwayfinder.core.protocols import AnalysisResult


logger = logging.getLogger(__name__)


class CacheManager:
    """High-level cache manager for DevWayfinder.

    Provides domain-specific methods for caching:
    - Analysis results (per-file, by content hash)
    - LLM summaries (by content hash + model ID)
    - Module metrics (complexity, LOC, etc.)
    """

    def __init__(
        self,
        project_root: Path,
        *,
        enabled: bool = True,
        ttl_seconds: int | None = None,
    ) -> None:
        """Initialize cache manager.

        Args:
            project_root: Project root directory
            enabled: Whether caching is enabled
            ttl_seconds: Default TTL for entries
        """
        self.project_root = Path(project_root).resolve()
        self.enabled = enabled
        self._storage = CacheStorage(
            project_root=self.project_root,
            ttl_seconds=ttl_seconds,
        )
        self._stats = {
            "analysis_hits": 0,
            "analysis_misses": 0,
            "summary_hits": 0,
            "summary_misses": 0,
        }

    @property
    def storage(self) -> CacheStorage:
        """Access underlying storage."""
        return self._storage

    @property
    def hit_rate(self) -> dict[str, float]:
        """Calculate cache hit rates."""
        rates = {}
        for category in ["analysis", "summary"]:
            hits = self._stats[f"{category}_hits"]
            misses = self._stats[f"{category}_misses"]
            total = hits + misses
            rates[category] = hits / total if total > 0 else 0.0
        return rates

    # =========================================================================
    # Analysis Caching
    # =========================================================================

    def _make_analysis_key(self, file_path: Path) -> str:
        """Generate cache key for analysis results.

        Uses relative path + content hash for uniqueness.
        """
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            rel_path = file_path

        # Key includes path hash to handle same content in different locations
        path_component = CacheStorage.compute_content_hash(str(rel_path))[:16]
        try:
            content_hash = CacheStorage.compute_file_hash(file_path)[:32]
        except FileNotFoundError:
            return f"analysis_{path_component}_missing"

        return f"analysis_{path_component}_{content_hash}"

    def get_analysis(self, file_path: Path) -> dict[str, Any] | None:
        """Get cached analysis results.

        Args:
            file_path: Path to the analyzed file

        Returns:
            Cached analysis data or None
        """
        if not self.enabled:
            return None

        key = self._make_analysis_key(file_path)
        entry = self._storage.get(CacheStorage.ANALYSIS_DIR, key)

        if entry:
            self._stats["analysis_hits"] += 1
            return entry.data
        else:
            self._stats["analysis_misses"] += 1
            return None

    def set_analysis(
        self,
        file_path: Path,
        result: AnalysisResult | dict[str, Any],
    ) -> None:
        """Cache analysis results.

        Args:
            file_path: Path to the analyzed file
            result: Analysis result to cache
        """
        if not self.enabled:
            return

        key = self._make_analysis_key(file_path)
        try:
            content_hash = CacheStorage.compute_file_hash(file_path)
        except FileNotFoundError:
            logger.warning("Cannot cache analysis for missing file: %s", file_path)
            return

        # Convert AnalysisResult to dict if needed
        if isinstance(result, dict):
            data = result
            language = result.get("language", "unknown")
        else:
            # It's an AnalysisResult protocol object
            data = {
                "path": str(result.path),
                "imports": list(result.imports),
                "exports": list(result.exports),
                "is_entry_point": result.is_entry_point,
                "language": result.language,
                "metadata": dict(result.metadata),
            }
            language = result.language or "unknown"

        self._storage.set(
            CacheStorage.ANALYSIS_DIR,
            key,
            data,
            content_hash,
            tags=["analysis", language],
        )

    def is_analysis_fresh(self, file_path: Path) -> bool:
        """Check if cached analysis is still valid.

        Args:
            file_path: Path to check

        Returns:
            True if cache is fresh (file unchanged), False otherwise
        """
        if not self.enabled:
            return False

        key = self._make_analysis_key(file_path)
        entry = self._storage.get(CacheStorage.ANALYSIS_DIR, key)

        if not entry:
            return False

        try:
            current_hash = CacheStorage.compute_file_hash(file_path)
            return entry.content_hash == current_hash
        except FileNotFoundError:
            return False

    # =========================================================================
    # Summary Caching
    # =========================================================================

    def _make_summary_key(
        self,
        file_path: Path,
        model_id: str,
        summary_type: str = "module",
    ) -> str:
        """Generate cache key for LLM summaries.

        Key combines content hash + model ID for invalidation on either change.
        """
        try:
            content_hash = CacheStorage.compute_file_hash(file_path)[:32]
        except FileNotFoundError:
            content_hash = "missing"

        model_hash = CacheStorage.compute_content_hash(model_id)[:16]
        return f"summary_{summary_type}_{content_hash}_{model_hash}"

    def get_summary(
        self,
        file_path: Path,
        model_id: str,
        summary_type: str = "module",
    ) -> str | None:
        """Get cached summary.

        Args:
            file_path: Path to the summarized file
            model_id: Model identifier (for cache invalidation on model change)
            summary_type: Type of summary (module, architecture, etc.)

        Returns:
            Cached summary text or None
        """
        if not self.enabled:
            return None

        key = self._make_summary_key(file_path, model_id, summary_type)
        entry = self._storage.get(CacheStorage.SUMMARIES_DIR, key)

        if entry:
            self._stats["summary_hits"] += 1
            return entry.data.get("summary")
        else:
            self._stats["summary_misses"] += 1
            return None

    def set_summary(
        self,
        file_path: Path,
        model_id: str,
        summary: str,
        summary_type: str = "module",
        *,
        tokens_used: int | None = None,
        provider: str | None = None,
    ) -> None:
        """Cache a summary.

        Args:
            file_path: Path to the summarized file
            model_id: Model identifier
            summary: Summary text
            summary_type: Type of summary
            tokens_used: Optional token count
            provider: Optional provider name
        """
        if not self.enabled:
            return

        key = self._make_summary_key(file_path, model_id, summary_type)
        try:
            content_hash = CacheStorage.compute_file_hash(file_path)
        except FileNotFoundError:
            logger.warning("Cannot cache summary for missing file: %s", file_path)
            return

        data = {
            "summary": summary,
            "summary_type": summary_type,
            "model_id": model_id,
            "tokens_used": tokens_used,
            "provider": provider,
        }

        self._storage.set(
            CacheStorage.SUMMARIES_DIR,
            key,
            data,
            content_hash,
            tags=["summary", summary_type, model_id],
        )

    # =========================================================================
    # Module Metrics Caching
    # =========================================================================

    def _make_metrics_key(self, file_path: Path) -> str:
        """Generate cache key for metrics."""
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            rel_path = file_path

        path_component = CacheStorage.compute_content_hash(str(rel_path))[:16]
        try:
            content_hash = CacheStorage.compute_file_hash(file_path)[:32]
        except FileNotFoundError:
            return f"metrics_{path_component}_missing"

        return f"metrics_{path_component}_{content_hash}"

    def get_metrics(self, file_path: Path) -> dict[str, Any] | None:
        """Get cached metrics.

        Args:
            file_path: Path to the file

        Returns:
            Cached metrics or None
        """
        if not self.enabled:
            return None

        key = self._make_metrics_key(file_path)
        entry = self._storage.get(CacheStorage.ANALYSIS_DIR, key)

        if entry:
            return entry.data
        return None

    def set_metrics(
        self,
        file_path: Path,
        metrics: dict[str, Any],
    ) -> None:
        """Cache metrics.

        Args:
            file_path: Path to the file
            metrics: Metrics dictionary
        """
        if not self.enabled:
            return

        key = self._make_metrics_key(file_path)
        try:
            content_hash = CacheStorage.compute_file_hash(file_path)
        except FileNotFoundError:
            return

        self._storage.set(
            CacheStorage.ANALYSIS_DIR,
            key,
            metrics,
            content_hash,
            tags=["metrics"],
        )

    # =========================================================================
    # Cache Management
    # =========================================================================

    def invalidate_file(self, file_path: Path) -> None:
        """Invalidate all cache entries for a file.

        Args:
            file_path: File whose cache should be invalidated
        """
        # Get the old content hash if available
        analysis_key = self._make_analysis_key(file_path)

        # Delete analysis cache
        self._storage.delete(CacheStorage.ANALYSIS_DIR, analysis_key)

        # Also delete metrics
        metrics_key = self._make_metrics_key(file_path)
        self._storage.delete(CacheStorage.ANALYSIS_DIR, metrics_key)

        logger.debug("Invalidated cache for: %s", file_path)

    def clear_all(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        return self._storage.clear()

    def clear_summaries(self) -> int:
        """Clear all summary cache entries.

        Returns:
            Number of entries cleared
        """
        return self._storage.clear(CacheStorage.SUMMARIES_DIR)

    def clear_analysis(self) -> int:
        """Clear all analysis cache entries.

        Returns:
            Number of entries cleared
        """
        return self._storage.clear(CacheStorage.ANALYSIS_DIR)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Combined storage and hit rate statistics
        """
        storage_stats = self._storage.get_stats()
        return {
            **storage_stats,
            "session_stats": dict(self._stats),
            "hit_rates": self.hit_rate,
        }
