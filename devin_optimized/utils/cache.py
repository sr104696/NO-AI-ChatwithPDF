"""
Lightweight LRU cache.

Simplified from 3_FTS_OCR_Search's MemoryAwareLRUCache — strips the
psutil dependency and keeps the core OrderedDict-based eviction logic
that the offline_pdf_intelligence ChunkCache also used.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Dict, Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """Thread-safe LRU cache with a fixed maximum size."""

    def __init__(self, max_size: int = 500) -> None:
        self.max_size = max_size
        self._data: OrderedDict[K, V] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._hits += 1
                return self._data[key]
            self._misses += 1
            return None

    def put(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._data:
                self._data[key] = value
                self._data.move_to_end(key)
            else:
                self._data[key] = value
                while len(self._data) > self.max_size:
                    self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total else 0.0
