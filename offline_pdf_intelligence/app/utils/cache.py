"""
In-memory cache for text chunks.

Provides fast access to recently accessed chunks without database queries.
"""

from typing import Dict, List, Optional, Any
from collections import OrderedDict


class ChunkCache:
    """
    LRU cache for text chunks.
    
    Stores chunks in memory for fast retrieval, with a configurable
    maximum size to prevent memory bloat.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the chunk cache.
        
        Args:
            max_size: Maximum number of chunks to cache
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
    
    def _make_key(self, pdf_id: int, chunk_index: int) -> str:
        """Create a cache key from PDF ID and chunk index."""
        return f"{pdf_id}:{chunk_index}"
    
    def get(self, pdf_id: int, chunk_index: int) -> Optional[Dict[str, Any]]:
        """
        Get a chunk from the cache.
        
        Args:
            pdf_id: ID of the PDF
            chunk_index: Index of the chunk
            
        Returns:
            Chunk data as dict, or None if not cached
        """
        key = self._make_key(pdf_id, chunk_index)
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def put(self, pdf_id: int, chunk_index: int, chunk_data: Dict[str, Any]) -> None:
        """
        Put a chunk into the cache.
        
        Args:
            pdf_id: ID of the PDF
            chunk_index: Index of the chunk
            chunk_data: Chunk data to cache
        """
        key = self._make_key(pdf_id, chunk_index)
        
        # If already exists, update and move to end
        if key in self._cache:
            self._cache[key] = chunk_data
            self._cache.move_to_end(key)
        else:
            # Add new entry
            self._cache[key] = chunk_data
            
            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
    
    def get_for_pdf(self, pdf_id: int) -> List[Dict[str, Any]]:
        """
        Get all cached chunks for a PDF.
        
        Args:
            pdf_id: ID of the PDF
            
        Returns:
            List of chunk data dicts
        """
        prefix = f"{pdf_id}:"
        chunks = []
        for key, value in self._cache.items():
            if key.startswith(prefix):
                chunks.append(value)
        return sorted(chunks, key=lambda x: x.get('chunk_index', 0))
    
    def clear(self) -> None:
        """Clear all cached chunks."""
        self._cache.clear()
    
    def clear_pdf(self, pdf_id: int) -> None:
        """
        Clear cached chunks for a specific PDF.
        
        Args:
            pdf_id: ID of the PDF
        """
        prefix = f"{pdf_id}:"
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def contains(self, pdf_id: int, chunk_index: int) -> bool:
        """Check if a chunk is cached."""
        key = self._make_key(pdf_id, chunk_index)
        return key in self._cache
