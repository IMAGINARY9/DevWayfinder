"""Caching layer for DevWayfinder.

Provides file-based caching for:
- Analysis results (imports, exports, metrics)
- LLM summaries (keyed by content hash + model)
"""

from devwayfinder.cache.manager import CacheManager
from devwayfinder.cache.storage import CacheEntry, CacheStorage

__all__ = [
    "CacheEntry",
    "CacheManager",
    "CacheStorage",
]
