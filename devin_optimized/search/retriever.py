"""
Query retriever with smart snippet extraction and confidence scoring.

Combines:
- Question-type detection (from offline_pdf_intelligence)
- Entity extraction via regex (from offline_pdf_intelligence)
- Snippet extraction around query terms (new idea)
- Confidence calibration across engines (new idea)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..core.models import Chunk, SearchResult, SearchResponse
from .fusion import FusionRanker


# ---- Question type patterns (expanded from offline_pdf_intelligence) ----

_QUESTION_PATTERNS: Dict[str, List[str]] = {
    "locate": [r"\bwhich page\b", r"\bon what page\b", r"\bpage number\b"],
    "find": [r"\bwhere\b", r"\bmention\b", r"\bfind\b", r"\bsearch\b"],
    "define": [r"\bwhat is\b", r"\bdefine\b", r"\bmeans\b", r":\s*$"],
    "extract": [r"\blist all\b", r"\bextract\b", r"\ball dates\b", r"\ball amounts\b"],
    "compare": [r"\bacross\b", r"\bcompare\b", r"\bbetween\b"],
    "list": [r"\blist\b", r"\ball sections\b"],
    "checklist": [r"\bdoes.*include\b", r"\bdoes.*have\b", r"\bis there a\b"],
    "who": [r"\bwho\b"],
    "when": [r"\bwhen\b", r"\bdate\b", r"\bdated\b"],
    "count": [r"\bhow many\b", r"\bcount\b", r"\bnumber of\b"],
}

# ---- Entity extraction patterns ----

_ENTITY_PATTERNS: Dict[str, str] = {
    "dates": (
        r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b"
        r"|"
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b"
    ),
    "emails": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "amounts": (
        r"\$[\d,]+(?:\.\d{2})?"
        r"|"
        r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:dollars?|USD|cents?)\b"
    ),
    "phone_numbers": r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b",
}


def detect_question_type(query: str) -> str:
    q = query.lower()
    for qtype, patterns in _QUESTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, q):
                return qtype
    return "find"


def extract_entities(text: str) -> Dict[str, List[str]]:
    entities: Dict[str, List[str]] = {}
    for etype, pattern in _ENTITY_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            entities[etype] = list(set(matches))
    return entities


# ---- Snippet extraction (new idea) ----

def extract_snippet(
    text: str, query: str, context_chars: int = 200
) -> str:
    """
    Extract the most relevant snippet around the first query-term match.

    Instead of returning the entire chunk, we window around the best
    match position so the user sees the most relevant context immediately.
    """
    terms = [t for t in query.lower().split() if len(t) > 2]
    if not terms:
        return text[:context_chars * 2]

    text_lower = text.lower()
    best_pos = len(text)
    for term in terms:
        pos = text_lower.find(term)
        if 0 <= pos < best_pos:
            best_pos = pos

    if best_pos >= len(text):
        return text[:context_chars * 2]

    start = max(0, best_pos - context_chars)
    end = min(len(text), best_pos + len(terms[0]) + context_chars)

    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def highlight_terms(text: str, query: str) -> str:
    """Wrap query terms in **bold** markers."""
    terms = re.findall(r'"[^"]+"|\S+', query.lower())
    terms = [t.strip('"') for t in terms if len(t) > 2]
    result = text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        result = pattern.sub(lambda m: f"**{m.group()}**", result)
    return result


# ---- Retriever ----

class Retriever:
    """
    High-level retriever: accepts a query, runs fusion search,
    extracts snippets, and returns a structured ``SearchResponse``.
    """

    def __init__(self, ranker: FusionRanker, chunks: List[Chunk]) -> None:
        self.ranker = ranker
        self.chunks = chunks

    def query(self, query_text: str, k: int = 5) -> SearchResponse:
        qtype = detect_question_type(query_text)

        fused = self.ranker.search(query_text, k=k * 2)

        results: List[SearchResult] = []
        all_entities: Dict[str, List[str]] = {}

        for chunk_idx, fused_score, engine_scores in fused:
            if chunk_idx < 0 or chunk_idx >= len(self.chunks):
                continue
            chunk = self.chunks[chunk_idx]

            snippet = extract_snippet(chunk.text, query_text)
            highlighted = highlight_terms(snippet, query_text)
            entities = extract_entities(chunk.text)

            # Merge entities into global set
            for etype, vals in entities.items():
                all_entities.setdefault(etype, []).extend(vals)

            results.append(
                SearchResult(
                    chunk=chunk,
                    score=fused_score,
                    snippet=snippet,
                    highlighted_snippet=highlighted,
                    engine_scores=engine_scores,
                    entities=entities,
                )
            )

        results = results[:k]

        # De-duplicate global entities
        for etype in all_entities:
            all_entities[etype] = list(set(all_entities[etype]))

        # Build message
        message = self._build_message(qtype, results)
        suggestions = self._build_suggestions(results)

        return SearchResponse(
            query=query_text,
            query_type=qtype,
            results=results,
            total_chunks_searched=len(self.chunks),
            message=message,
            suggestions=suggestions,
            extracted_entities=all_entities,
        )

    @staticmethod
    def _build_message(qtype: str, results: List[SearchResult]) -> str:
        if not results:
            return "No direct evidence found. Try different keywords."

        top = results[0]
        loc = f"page {top.chunk.page_number}"
        if top.chunk.section_heading:
            loc += f" ({top.chunk.section_heading})"

        if top.confidence == "high":
            return f"Found on {loc} of {top.chunk.pdf_name}:"
        if top.confidence == "medium":
            return f"Possibly relevant - from {loc} of {top.chunk.pdf_name}:"
        return f"Weak match from {loc} of {top.chunk.pdf_name}:"

    @staticmethod
    def _build_suggestions(results: List[SearchResult]) -> List[str]:
        if not results:
            return [
                "Try more specific keywords",
                "Check spelling of key terms",
                "Use simpler phrasing",
            ]
        if results[0].confidence == "low":
            return ["Try rephrasing with different terms"]
        return []
