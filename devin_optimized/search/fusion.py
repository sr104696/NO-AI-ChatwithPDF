"""
Reciprocal Rank Fusion (RRF) for combining results from multiple engines.

This is a new idea not present in any of the original sub-projects:
instead of relying on a single ranking signal, we fuse BM25, TF-IDF,
and exact-match scores into a single unified ranking using RRF, which
is robust and parameter-free.

Reference: Cormack, Clarke & Buettcher, "Reciprocal Rank Fusion
outperforms Condorcet and individual Rank Learning Methods", SIGIR 2009.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from ..core.models import Chunk
from .engines import BM25Engine, TFIDFEngine, ExactMatchEngine


class FusionRanker:
    """
    Combine multiple search engines via Reciprocal Rank Fusion.

    Each engine produces an independent ranked list.  RRF merges them
    into a single ranking that is more robust than any individual engine.
    """

    def __init__(
        self,
        bm25: BM25Engine,
        tfidf: TFIDFEngine,
        exact: ExactMatchEngine,
        rrf_k: int = 60,
        weights: Dict[str, float] | None = None,
    ) -> None:
        self.bm25 = bm25
        self.tfidf = tfidf
        self.exact = exact
        self.rrf_k = rrf_k
        self.weights = weights or {"bm25": 1.0, "tfidf": 0.8, "exact": 1.2}

    def build(self, chunks: List[Chunk]) -> None:
        """Build all engine indexes."""
        self.bm25.build(chunks)
        self.tfidf.build(chunks)
        self.exact.build(chunks)

    def search(
        self, query: str, k: int = 10, per_engine_k: int = 50
    ) -> List[Tuple[int, float, Dict[str, float]]]:
        """
        Search all engines and fuse rankings.

        Returns:
            List of ``(chunk_index, fused_score, engine_scores)`` tuples,
            sorted by fused_score descending.
        """
        engine_results: Dict[str, List[Tuple[int, float]]] = {}

        if self.bm25.is_ready:
            engine_results["bm25"] = self.bm25.search(query, k=per_engine_k)
        if self.tfidf.is_ready:
            engine_results["tfidf"] = self.tfidf.search(query, k=per_engine_k)
        if self.exact.is_ready:
            engine_results["exact"] = self.exact.search(query, k=per_engine_k)

        # ---- Reciprocal Rank Fusion ----
        rrf_scores: Dict[int, float] = defaultdict(float)
        per_doc_engine_scores: Dict[int, Dict[str, float]] = defaultdict(dict)

        for engine_name, results in engine_results.items():
            weight = self.weights.get(engine_name, 1.0)
            for rank, (doc_idx, raw_score) in enumerate(results):
                rrf_scores[doc_idx] += weight / (self.rrf_k + rank + 1)
                per_doc_engine_scores[doc_idx][engine_name] = raw_score

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            (idx, score, per_doc_engine_scores[idx]) for idx, score in ranked[:k]
        ]
