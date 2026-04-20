"""
Document fingerprinting for near-duplicate detection.

New idea: uses a simple SimHash / shingling approach so users can detect
when they have loaded the same (or very similar) PDF twice.  This avoids
indexing duplicates and cluttering search results.

The approach is intentionally lightweight — no external libraries beyond
what is already in the repo (hashlib from stdlib).
"""

from __future__ import annotations

import hashlib
from typing import Dict, FrozenSet, List, Set, Tuple

from ..core.models import PDFDocument


def _shingles(text: str, k: int = 5) -> FrozenSet[str]:
    """Generate character-level k-shingles from text."""
    text = text.lower()
    if len(text) < k:
        return frozenset([text])
    return frozenset(text[i : i + k] for i in range(len(text) - k + 1))


def _hash_shingle(shingle: str) -> int:
    return int(hashlib.md5(shingle.encode("utf-8")).hexdigest(), 16)


def _simhash(shingles: FrozenSet[str], bits: int = 64) -> int:
    """Compute a SimHash fingerprint from a set of shingles."""
    vec = [0] * bits
    for shingle in shingles:
        h = _hash_shingle(shingle)
        for i in range(bits):
            if h & (1 << i):
                vec[i] += 1
            else:
                vec[i] -= 1
    result = 0
    for i in range(bits):
        if vec[i] > 0:
            result |= 1 << i
    return result


def _hamming_distance(a: int, b: int, bits: int = 64) -> int:
    return bin(a ^ b).count("1")


class DocumentFingerprinter:
    """
    Detect near-duplicate PDFs using SimHash.

    Usage::

        fp = DocumentFingerprinter()
        doc1 = extractor.extract("a.pdf")
        doc2 = extractor.extract("b.pdf")
        fp.register(doc1)
        fp.register(doc2)
        dupes = fp.find_duplicates(threshold=3)
    """

    def __init__(self, shingle_k: int = 5, bits: int = 64) -> None:
        self.shingle_k = shingle_k
        self.bits = bits
        self._fingerprints: Dict[str, int] = {}  # pdf_path -> simhash

    def fingerprint(self, doc: PDFDocument) -> int:
        """Compute and store the SimHash for a document."""
        full_text = " ".join(c.text for c in doc.chunks)
        shingles = _shingles(full_text, self.shingle_k)
        fp = _simhash(shingles, self.bits)
        self._fingerprints[doc.file_path] = fp
        doc.fingerprint = hex(fp)
        return fp

    def register(self, doc: PDFDocument) -> int:
        """Alias for ``fingerprint``."""
        return self.fingerprint(doc)

    def similarity(self, path_a: str, path_b: str) -> float:
        """
        Return a 0-1 similarity score between two registered documents.

        1.0 means identical fingerprints; 0.0 means maximally different.
        """
        fa = self._fingerprints.get(path_a)
        fb = self._fingerprints.get(path_b)
        if fa is None or fb is None:
            raise KeyError("Both documents must be registered first")
        dist = _hamming_distance(fa, fb, self.bits)
        return 1.0 - (dist / self.bits)

    def find_duplicates(
        self, threshold: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Find all pairs of documents whose SimHash Hamming distance
        is at most *threshold*.

        Returns:
            List of ``(path_a, path_b, similarity)`` tuples.
        """
        paths = list(self._fingerprints.keys())
        dupes: List[Tuple[str, str, float]] = []
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                dist = _hamming_distance(
                    self._fingerprints[paths[i]],
                    self._fingerprints[paths[j]],
                    self.bits,
                )
                if dist <= threshold:
                    sim = 1.0 - (dist / self.bits)
                    dupes.append((paths[i], paths[j], sim))
        return dupes
