"""
CLI entry point for Devin Optimized PDF Intelligence.

Provides a rich terminal interface for:
- Loading and indexing PDFs
- Querying with multi-engine fusion search
- Exporting results to JSON / CSV / Markdown
- Detecting duplicate documents

Usage::

    python -m devin_optimized --help
    python -m devin_optimized --file doc.pdf --search "contract terms"
    python -m devin_optimized --folder ./docs/ --search "deadline" --export results.md
    python -m devin_optimized --folder ./docs/ --duplicates
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from .core.extractor import PDFExtractor
from .core.models import Chunk, PDFDocument, SearchResponse
from .search.engines import BM25Engine, TFIDFEngine, ExactMatchEngine
from .search.fusion import FusionRanker
from .search.retriever import Retriever
from .utils.export import Exporter
from .utils.fingerprint import DocumentFingerprinter
from .utils.security import validate_pdf_path


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="devin_optimized",
        description=(
            "Devin Optimized PDF Intelligence — multi-engine ranked-fusion "
            "search over PDF documents.  Zero LLM, zero hallucination."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file", "-f", type=str, help="Path to a single PDF to load"
    )
    parser.add_argument(
        "--folder", "-d", type=str, help="Path to a folder of PDFs to load"
    )
    parser.add_argument(
        "--search", "-s", type=str, help="Search query (runs in CLI mode)"
    )
    parser.add_argument(
        "--top-k", "-k", type=int, default=5, help="Number of results (default: 5)"
    )
    parser.add_argument(
        "--export", "-e", type=str, help="Export results to file (json/csv/md)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "md"],
        default=None,
        help="Export format (inferred from extension if omitted)",
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="Detect near-duplicate documents and print report",
    )
    parser.add_argument(
        "--ocr", action="store_true", help="Force OCR on all pages"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    return parser.parse_args(argv)


def _collect_pdfs(args: argparse.Namespace) -> List[str]:
    """Gather PDF paths from --file and/or --folder."""
    paths: List[str] = []

    if args.file:
        ok, err = validate_pdf_path(args.file)
        if not ok:
            print(f"Error: {err}")
            sys.exit(1)
        paths.append(str(Path(args.file).resolve()))

    if args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"Error: not a directory: {folder}")
            sys.exit(1)
        pdf_files = sorted(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {folder}")
            sys.exit(1)
        for pf in pdf_files:
            ok, err = validate_pdf_path(str(pf))
            if ok:
                paths.append(str(pf.resolve()))
            else:
                print(f"  Skipping {pf.name}: {err}")

    return paths


def _infer_format(path: str) -> str:
    suffix = Path(path).suffix.lower()
    mapping = {".json": "json", ".csv": "csv", ".md": "md", ".markdown": "md"}
    return mapping.get(suffix, "json")


def _print_response(resp: SearchResponse) -> None:
    print()
    print(f"Query: {resp.query}")
    print(f"Type:  {resp.query_type}")
    print(f"Chunks searched: {resp.total_chunks_searched}")
    print()

    if resp.message:
        print(f"  {resp.message}")
        print()

    if not resp.results:
        print("  No results found.")
        if resp.suggestions:
            print()
            print("  Suggestions:")
            for s in resp.suggestions:
                print(f"    - {s}")
        return

    for i, r in enumerate(resp.results, 1):
        conf_tag = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(
            r.confidence, ""
        )
        print(f"  {i}. {conf_tag} score={r.score:.4f}  "
              f"p.{r.chunk.page_number} of {r.chunk.pdf_name}")
        if r.chunk.section_heading:
            print(f"     Section: {r.chunk.section_heading}")
        print(f"     {r.snippet}")

        if r.entities:
            parts = [f"{k}: {', '.join(v)}" for k, v in r.entities.items()]
            print(f"     Entities: {'; '.join(parts)}")

        scores = ", ".join(f"{e}={s:.4f}" for e, s in r.engine_scores.items())
        print(f"     Engines: {scores}")
        print()

    if resp.extracted_entities:
        print("  Global entities across results:")
        for etype, vals in resp.extracted_entities.items():
            print(f"    {etype}: {', '.join(vals)}")
        print()


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    if not args.file and not args.folder:
        print("Provide --file or --folder. Use --help for usage.")
        return 1

    # ---- Collect PDFs ----
    pdf_paths = _collect_pdfs(args)
    if not pdf_paths:
        print("No valid PDFs to process.")
        return 1

    print(f"Loading {len(pdf_paths)} PDF(s)...")

    # ---- Extract ----
    extractor = PDFExtractor()
    t0 = time.time()

    documents: List[PDFDocument] = []
    for path in pdf_paths:
        name = Path(path).name
        if args.verbose:
            print(f"  Extracting: {name}")
        doc = extractor.extract(path, force_ocr=args.ocr)
        documents.append(doc)
        if args.verbose:
            print(f"    {doc.page_count} pages, {len(doc.chunks)} chunks")

    all_chunks: List[Chunk] = []
    for doc in documents:
        all_chunks.extend(doc.chunks)

    elapsed = time.time() - t0
    print(f"Extracted {len(all_chunks)} chunks from "
          f"{len(documents)} PDF(s) in {elapsed:.1f}s")

    if not all_chunks:
        print("No text extracted from any document.")
        return 1

    # ---- Duplicate detection ----
    if args.duplicates and len(documents) > 1:
        fp = DocumentFingerprinter()
        for doc in documents:
            fp.register(doc)
        dupes = fp.find_duplicates(threshold=5)
        if dupes:
            print("\nNear-duplicate documents detected:")
            for a, b, sim in dupes:
                print(f"  {Path(a).name} <-> {Path(b).name}  "
                      f"similarity={sim:.2%}")
        else:
            print("\nNo near-duplicates detected.")
        print()

    # ---- Build search indexes ----
    if not args.search:
        print("No --search query provided. Indexed and ready.")
        return 0

    bm25 = BM25Engine()
    tfidf = TFIDFEngine()
    exact = ExactMatchEngine()
    ranker = FusionRanker(bm25, tfidf, exact)
    ranker.build(all_chunks)
    retriever = Retriever(ranker, all_chunks)

    # ---- Search ----
    response = retriever.query(args.search, k=args.top_k)
    _print_response(response)

    # ---- Export ----
    if args.export:
        fmt = args.format or _infer_format(args.export)
        Exporter.write(response, args.export, fmt=fmt)
        print(f"Results exported to {args.export} ({fmt})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
