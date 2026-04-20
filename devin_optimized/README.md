# Devin Optimized PDF Intelligence

**A unified, optimized PDF search tool that fuses the best ideas from all four sub-projects — plus new techniques — into a single high-performance pipeline.**

Zero LLM.  Zero API calls.  Zero hallucinations.  Evidence only.

## What's Different

This folder is a ground-up rewrite that cherry-picks the strongest ideas from each original module and adds new ones:

| Idea | Origin | What Changed |
|------|--------|-------------|
| TF-IDF scoring | `1_TFIDF_Scratch` | Rebuilt without globals/hardcoded paths; uses scikit-learn's vectorizer with bigram support |
| BM25 + proximity span scoring | `2_BM25_Search` | Extracted from the 1 200-line monolith into a clean `BM25Engine` class |
| Security & caching | `3_FTS_OCR_Search` | Simplified to a thread-safe `LRUCache`; kept sanitization helpers |
| Evidence-first retrieval & question-type detection | `offline_pdf_intelligence` | Kept the regex-based intent router; expanded with a `count` type |
| **Reciprocal Rank Fusion** | **New** | Combines BM25 + TF-IDF + exact match into one ranking — more robust than any single engine |
| **Smart snippet extraction** | **New** | Returns a windowed excerpt around the best match, not the entire chunk |
| **Document fingerprinting (SimHash)** | **New** | Detects near-duplicate PDFs before indexing via character-level shingling |
| **Multi-format export** | **New** | One-liner export to JSON, CSV, or Markdown with full engine-score breakdown |
| **CLI-first design** | **New** | Fully usable from the terminal; no GUI dependency |
| **Typed dataclasses everywhere** | **New** | `Chunk`, `PDFDocument`, `SearchResult`, `SearchResponse` — no dicts-of-dicts |
| **Concurrent multi-PDF extraction** | **New** | `ThreadPoolExecutor` processes multiple PDFs in parallel |

## Architecture

```
devin_optimized/
├── core/
│   ├── models.py        # Typed dataclasses: Chunk, PDFDocument, SearchResult, SearchResponse
│   └── extractor.py     # PyMuPDF extraction + OCR fallback + concurrent processing
├── search/
│   ├── engines.py       # BM25Engine, TFIDFEngine, ExactMatchEngine
│   ├── fusion.py        # Reciprocal Rank Fusion ranker
│   └── retriever.py     # Question-type detection, snippet extraction, entity extraction
├── utils/
│   ├── cache.py         # Thread-safe LRU cache
│   ├── security.py      # Input validation & sanitization
│   ├── export.py        # JSON / CSV / Markdown export
│   └── fingerprint.py   # SimHash-based near-duplicate detection
├── cli.py               # CLI entry point
├── __main__.py           # python -m devin_optimized
└── requirements.txt
```

## Installation

```bash
pip install -r devin_optimized/requirements.txt
```

For OCR support on scanned PDFs:
```bash
sudo apt install tesseract-ocr   # Ubuntu/Debian
brew install tesseract             # macOS
```

## Usage

```bash
# Search a single PDF
python -m devin_optimized --file document.pdf --search "contract deadline"

# Index a folder and search
python -m devin_optimized --folder ./docs/ --search "termination clause" --top-k 10

# Export results to Markdown
python -m devin_optimized --folder ./docs/ --search "payment terms" --export results.md

# Export to CSV
python -m devin_optimized -d ./docs/ -s "liability" -e report.csv

# Detect duplicate PDFs
python -m devin_optimized --folder ./docs/ --duplicates

# Force OCR on all pages
python -m devin_optimized --file scanned.pdf --search "invoice" --ocr

# Verbose output
python -m devin_optimized --file doc.pdf --search "query" --verbose
```

## How Fusion Search Works

Instead of relying on a single ranking algorithm, this tool runs **three independent engines** and merges their results using [Reciprocal Rank Fusion (RRF)](https://dl.acm.org/doi/10.1145/1571941.1572114):

1. **BM25** — best for keyword relevance (via `bm25s`)
2. **TF-IDF** — best for semantic similarity with bigrams (via scikit-learn)
3. **Exact Match** — best for phrase / proximity queries (custom span scorer)

RRF assigns each document a score based on its rank in each engine's list:

```
RRF_score(d) = Σ  weight_e / (k + rank_e(d))
```

This is robust because it doesn't require score calibration across engines — only rank positions matter.

## Confidence Levels

Each result carries a confidence label:

| Level | Fused Score | Meaning |
|-------|------------|---------|
| **HIGH** | ≥ 0.70 | Strong match across multiple engines |
| **MEDIUM** | 0.40 – 0.69 | Partial or single-engine match |
| **LOW** | < 0.40 | Weak / speculative match |

## Key Design Decisions

1. **Frozen `Chunk` dataclass** — immutable after extraction for safe concurrent access
2. **No database** — indexes live in memory; re-extract on each run (fast enough for < 1 000 PDFs)
3. **Deterministic** — no neural embeddings, no randomness, same query always returns same results
4. **No GUI dependency** — the CLI is the primary interface; a GUI can be layered on top
5. **Minimal dependencies** — only PyMuPDF, bm25s, scikit-learn, numpy (+ optional pytesseract/Pillow for OCR)
