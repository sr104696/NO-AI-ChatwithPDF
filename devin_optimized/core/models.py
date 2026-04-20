"""
Data models for the PDF intelligence pipeline.

Uses dataclasses for clean, typed data structures throughout the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Chunk:
    """An atomic unit of searchable text extracted from a PDF page."""

    text: str
    page_number: int
    chunk_index: int
    pdf_path: str
    section_heading: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None

    @property
    def pdf_name(self) -> str:
        return Path(self.pdf_path).stem


@dataclass
class PDFDocument:
    """Metadata and extracted content for a single PDF file."""

    file_path: str
    page_count: int
    file_size: int
    is_scanned: bool = False
    title: Optional[str] = None
    author: Optional[str] = None
    chunks: List[Chunk] = field(default_factory=list)
    fingerprint: Optional[str] = None

    @property
    def file_name(self) -> str:
        return Path(self.file_path).name

    @property
    def stem(self) -> str:
        return Path(self.file_path).stem


@dataclass
class SearchResult:
    """A single ranked search hit with provenance."""

    chunk: Chunk
    score: float
    snippet: str
    highlighted_snippet: str
    engine_scores: Dict[str, float] = field(default_factory=dict)
    entities: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def confidence(self) -> str:
        if self.score >= 0.70:
            return "high"
        if self.score >= 0.40:
            return "medium"
        return "low"


@dataclass
class SearchResponse:
    """Aggregated response for a user query."""

    query: str
    query_type: str
    results: List[SearchResult]
    total_chunks_searched: int
    message: str = ""
    suggestions: List[str] = field(default_factory=list)
    extracted_entities: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def top_result(self) -> Optional[SearchResult]:
        return self.results[0] if self.results else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "message": self.message,
            "total_chunks_searched": self.total_chunks_searched,
            "results": [
                {
                    "score": r.score,
                    "confidence": r.confidence,
                    "snippet": r.snippet,
                    "page_number": r.chunk.page_number,
                    "pdf": r.chunk.pdf_name,
                    "section": r.chunk.section_heading or "",
                    "engine_scores": r.engine_scores,
                    "entities": r.entities,
                }
                for r in self.results
            ],
            "suggestions": self.suggestions,
            "extracted_entities": self.extracted_entities,
        }
