#!/usr/bin/env python3
"""
Offline PDF Intelligence - Main Entry Point

A fully offline PDF query tool with zero LLM, zero API calls.
Evidence-first search using BM25 indexing.

Usage:
    python -m app.main                    # Launch GUI
    python -m app.main --file doc.pdf     # Load specific PDF
    python -m app.main --search "query"   # CLI search mode
"""

import argparse
import sys
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Offline PDF Intelligence - Evidence-based PDF querying",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Launch the GUI
  %(prog)s --file document.pdf      Load a specific PDF
  %(prog)s --folder ./docs/         Index all PDFs in a folder
  %(prog)s --search "contract terms" Search loaded documents (CLI mode)
  %(prog)s --verbose                Show detailed output
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='Path to a PDF file to load'
    )
    
    parser.add_argument(
        '--folder', '-d',
        type=str,
        help='Path to a folder containing PDFs to index'
    )
    
    parser.add_argument(
        '--search', '-s',
        type=str,
        help='Search query (CLI mode)'
    )
    
    parser.add_argument(
        '--export', '-e',
        type=str,
        help='Export results to CSV file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--clear-data',
        action='store_true',
        help='Clear all indexed data and exit'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Handle clear data
    if args.clear_data:
        from .utils.db import DatabaseManager
        db = DatabaseManager()
        db.clear_all_data()
        print("✓ All data cleared successfully.")
        return 0
    
    # Import here to avoid circular imports
    from .extractor import PDFExtractor
    from .indexer import BM25Indexer, TFIDFIndexer
    from .retriever import QueryRetriever, detect_question_type
    from .utils.db import DatabaseManager
    
    # Initialize components
    db = DatabaseManager()
    extractor = PDFExtractor()
    bm25_indexer = BM25Indexer()
    
    # If search query provided without loading files, try to use existing index
    if args.search:
        # Check if we have any indexed documents
        pdfs = db.get_all_pdfs()
        if not pdfs:
            print("No documents indexed. Load a PDF first using --file or --folder.")
            return 1
        
        # For now, just launch GUI since we need the index in memory
        print("Launching GUI with search query...")
        from .gui.chat_app import ChatApp
        app = ChatApp()
        # Pre-populate search (would need to implement this)
        app.run()
        return 0
    
    # If folder provided, process all PDFs
    if args.folder:
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"Error: Folder not found: {folder_path}")
            return 1
        
        pdf_files = list(folder_path.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return 1
        
        print(f"Found {len(pdf_files)} PDF files in {folder_path}")
        
        for pdf_file in pdf_files:
            try:
                print(f"\nProcessing: {pdf_file.name}")
                
                # Extract chunks
                metadata = extractor.get_pdf_metadata(str(pdf_file))
                is_scanned = metadata.get('is_scanned', False)
                
                if is_scanned:
                    if extractor.is_ocr_available():
                        print(f"  → Scanned PDF, will use OCR")
                    else:
                        print(f"  → Warning: Scanned PDF but OCR not available")
                
                chunks = extractor.extract_chunks(str(pdf_file), force_ocr=is_scanned)
                print(f"  → Extracted {len(chunks)} text chunks")
                
                # Save to database
                pdf_id = db.insert_pdf_file(
                    file_name=pdf_file.stem,
                    file_path=str(pdf_file),
                    file_size=metadata['file_size'],
                    page_count=metadata['page_count'],
                    is_scanned=is_scanned
                )
                
                for chunk in chunks:
                    db.insert_chunk(
                        pdf_id=pdf_id,
                        chunk_index=chunk['chunk_index'],
                        page_number=chunk['page_number'],
                        text=chunk['text'],
                        section_heading=chunk.get('section_heading')
                    )
                
                print(f"  → Saved to database (ID: {pdf_id})")
                
            except Exception as e:
                print(f"  → Error: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
        
        print(f"\n✓ Indexed {len(pdf_files)} PDF files")
        return 0
    
    # If single file provided
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1
        
        try:
            print(f"Processing: {file_path.name}")
            
            metadata = extractor.get_pdf_metadata(str(file_path))
            is_scanned = metadata.get('is_scanned', False)
            
            if is_scanned and not extractor.is_ocr_available():
                print("Warning: This appears to be a scanned PDF but OCR is not available.")
            
            chunks = extractor.extract_chunks(str(file_path), force_ocr=is_scanned)
            print(f"Extracted {len(chunks)} text chunks")
            
            # Build index
            bm25_indexer.build_index(chunks)
            
            # Save to database
            pdf_id = db.insert_pdf_file(
                file_name=file_path.stem,
                file_path=str(file_path),
                file_size=metadata['file_size'],
                page_count=metadata['page_count'],
                is_scanned=is_scanned
            )
            
            for chunk in chunks:
                db.insert_chunk(
                    pdf_id=pdf_id,
                    chunk_index=chunk['chunk_index'],
                    page_number=chunk['page_number'],
                    text=chunk['text'],
                    section_heading=chunk.get('section_heading')
                )
            
            print(f"✓ Loaded and indexed: {file_path.name}")
            
            # If also searching
            if args.search:
                retriever = QueryRetriever(bm25_indexer)
                results = retriever.retrieve(args.search, k=5)
                response = retriever.format_response(args.search, results)
                
                print(f"\nQuery: {args.search}")
                print(f"Type: {detect_question_type(args.search)}")
                print(f"\n{response['message']}")
                
                for i, excerpt in enumerate(response.get('excerpts', []), 1):
                    print(f"\n{i}. Page {excerpt['page_number']} (score: {excerpt['score']:.2f})")
                    print(f"   \"{excerpt['text'][:200]}...\"")
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    # Default: Launch GUI
    print("Launching Offline PDF Intelligence GUI...")
    from .gui.chat_app import ChatApp
    app = ChatApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
