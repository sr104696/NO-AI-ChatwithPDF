"""
Search engines: BM25, TF-IDF, and exact match.

Each engine implements a common interface so they can be composed
by the FusionRanker.  Inspired by the original repo's separate
implementations but unified under a single protocol.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import bm25s

from ..core.models import Chunk


def _normalize(text: str) -> str:
    """Lower-case and strip accents for matching."""
    nfkd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# BM25 engine  (adapted from 2_BM25_Search + offline_pdf_intelligence)
# ---------------------------------------------------------------------------

class BM25Engine:
    """BM25 full-text search over chunks."""

    def __init__(self) -> None:
        self._model: Optional[bm25s.BM25] = None
        self._texts: List[str] = []

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def build(self, chunks: List[Chunk]) -> None:
        self._texts = [c.text for c in chunks]
        tokenized = bm25s.tokenize(self._texts, stopwords="en")
        self._model = bm25s.BM25()
        self._model.index(tokenized)

    def search(self, query: str, k: int = 50) -> List[Tuple[int, float]]:
        if self._model is None:
            return []
        tokenized_q = bm25s.tokenize([query], stopwords="en")
        k_actual = min(k, len(self._texts))
        if k_actual == 0:
            return []
        results, scores = self._model.retrieve(
            tokenized_q, corpus=self._texts, k=k_actual
        )
        if len(results) == 0:
            return []
        # results[0] are the matched texts; we need indices
        text_to_idx = {t: i for i, t in enumerate(self._texts)}
        out: List[Tuple[int, float]] = []
        for text_val, score_val in zip(results[0], scores[0]):
            idx = text_to_idx.get(str(text_val))
            if idx is not None:
                out.append((idx, float(score_val)))
        return out


# ---------------------------------------------------------------------------
# TF-IDF engine  (rebuilt from 1_TFIDF_Scratch + offline_pdf_intelligence)
# ---------------------------------------------------------------------------

class TFIDFEngine:
    """TF-IDF cosine similarity search, rebuilt from scratch without globals."""

    def __init__(
        self,
        max_features: int = 10_000,
        ngram_range: Tuple[int, int] = (1, 2),
    ) -> None:
        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=ngram_range,
            min_df=1,
            max_df=0.95,
        )
        self._matrix = None

    @property
    def is_ready(self) -> bool:
        return self._matrix is not None

    def build(self, chunks: List[Chunk]) -> None:
        texts = [c.text for c in chunks]
        self._matrix = self._vectorizer.fit_transform(texts)

    def search(self, query: str, k: int = 50) -> List[Tuple[int, float]]:
        if self._matrix is None:
            return []
        q_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self._matrix).flatten()
        top_k = np.argsort(sims)[::-1][:k]
        return [(int(i), float(sims[i])) for i in top_k if sims[i] > 0]

    def find_similar(self, chunk_idx: int, k: int = 5) -> List[Tuple[int, float]]:
        """Find chunks similar to a given chunk (for dedup / related docs)."""
        if self._matrix is None:
            return []
        q_vec = self._matrix[chunk_idx]
        sims = cosine_similarity(q_vec, self._matrix).flatten()
        top_k = np.argsort(sims)[::-1]
        return [
            (int(i), float(sims[i]))
            for i in top_k
            if i != chunk_idx and sims[i] > 0
        ][:k]


# ---------------------------------------------------------------------------
# Exact match engine  (adapted from 2_BM25_Search exact/simple search)
# ---------------------------------------------------------------------------

class ExactMatchEngine:
    """Case-insensitive exact substring + proximity scoring."""

    def __init__(self) -> None:
        self._chunks: List[Chunk] = []

    @property
    def is_ready(self) -> bool:
        return len(self._chunks) > 0

    def build(self, chunks: List[Chunk]) -> None:
        self._chunks = list(chunks)

    def search(self, query: str, k: int = 50) -> List[Tuple[int, float]]:
        norm_query = _normalize(query)
        terms = norm_query.split()
        scored: List[Tuple[int, float]] = []

        for idx, chunk in enumerate(self._chunks):
            norm_text = _normalize(chunk.text)

            # Exact phrase match gets highest score
            if norm_query in norm_text:
                scored.append((idx, 1.0))
                continue

            # Proximity / span-based scoring (from 2_BM25_Search minimal_span_score)
            span_score = self._minimal_span_score(norm_text, terms)
            if span_score > 0:
                scored.append((idx, span_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    @staticmethod
    def _minimal_span_score(text: str, query_terms: List[str]) -> float:
        """Score based on smallest window containing all query terms."""
        words = text.split()
        positions: Dict[str, List[int]] = {t: [] for t in query_terms}
        for i, w in enumerate(words):
            if w in positions:
                positions[w].append(i)

        # All terms must appear at least once
        for pos_list in positions.values():
            if not pos_list:
                return 0.0

        all_pos: List[Tuple[int, str]] = []
        for term, pos_list in positions.items():
            all_pos.extend((p, term) for p in pos_list)
        all_pos.sort()

        best_span = len(words) + 1
        found: Dict[str, int] = {}
        left = 0

        for right_idx in range(len(all_pos)):
            pos_r, term_r = all_pos[right_idx]
            found[term_r] = pos_r

            while len(found) == len(query_terms):
                span = max(found.values()) - min(found.values()) + 1
                best_span = min(best_span, span)
                pos_l, term_l = all_pos[left]
                if found.get(term_l) == pos_l:
                    del found[term_l]
                left += 1

        if best_span > len(words):
            return 0.0
        return 1.0 / (best_span + 1)
