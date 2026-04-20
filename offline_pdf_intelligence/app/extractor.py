"""
PDF text extraction module.

Extracts text from PDFs using PyMuPDF (fitz), with optional OCR support
for scanned documents using Tesseract.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF


class PDFExtractor:
    """
    Extracts text from PDF files in chunks.
    
    Supports both text-based PDFs and scanned PDFs (via OCR).
    Chunks are ~3 sentences each for optimal search granularity.
    """
    
    def __init__(self, use_ocr: bool = False):
        """
        Initialize the PDF extractor.
        
        Args:
            use_ocr: Whether to use OCR for all pages (for scanned PDFs)
        """
        self.use_ocr = use_ocr
        self._ocr_available = None
    
    def is_ocr_available(self) -> bool:
        """Check if Tesseract OCR is available on the system."""
        if self._ocr_available is not None:
            return self._ocr_available
        
        try:
            import pytesseract
            # Try to run tesseract --version
            import subprocess
            result = subprocess.run(
                ['tesseract', '--version'],
                capture_output=True,
                timeout=5
            )
            self._ocr_available = (result.returncode == 0)
        except Exception:
            self._ocr_available = False
        
        return self._ocr_available
    
    def detect_if_scanned(self, pdf_path: str, sample_pages: int = 3) -> bool:
        """
        Detect if a PDF is likely scanned (image-based) vs text-based.
        
        Args:
            pdf_path: Path to the PDF file
            sample_pages: Number of pages to sample
            
        Returns:
            True if the PDF appears to be scanned
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = min(len(doc), sample_pages)
            
            text_chars = 0
            for i in range(total_pages):
                page = doc[i]
                text = page.get_text()
                text_chars += len(text.strip())
            
            doc.close()
            
            # If average chars per page is very low, likely scanned
            avg_chars = text_chars / max(total_pages, 1)
            return avg_chars < 50  # Threshold for "scanned" detection
            
        except Exception:
            return False
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Uses simple heuristics based on punctuation.
        """
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_chunks(self, sentences: List[str], 
                       sentences_per_chunk: int = 3) -> List[str]:
        """
        Group sentences into chunks.
        
        Args:
            sentences: List of sentences
            sentences_per_chunk: Target sentences per chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = ' '.join(chunk_sentences)
            if chunk_text.strip():
                chunks.append(chunk_text)
        return chunks
    
    def _detect_section_heading(self, page: fitz.Page, 
                                 page_number: int) -> Optional[str]:
        """
        Detect the section heading on a page using font size heuristics.
        
        The largest font on the page (typically at the top) is considered
        the section heading.
        """
        try:
            blocks = page.get_text("dict")["blocks"]
            
            # Find text blocks with their font sizes
            text_blocks = []
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            size = span.get("size", 0)
                            if text and size > 0:
                                text_blocks.append((text, size, block))
            
            if not text_blocks:
                return None
            
            # Sort by font size descending
            text_blocks.sort(key=lambda x: x[1], reverse=True)
            
            # The largest text is likely the heading
            largest_text = text_blocks[0][0]
            
            # Filter out page numbers, headers, etc.
            if len(largest_text) < 3 or len(largest_text) > 200:
                return None
            
            # Check if it's all caps or looks like a heading
            if largest_text.isupper() or largest_text[0].isupper():
                return largest_text
            
            return None
            
        except Exception:
            return None
    
    def extract_text_with_pymupdf(self, page: fitz.Page) -> str:
        """Extract text from a page using PyMuPDF."""
        return page.get_text("text")
    
    def extract_text_with_ocr(self, page: fitz.Page) -> str:
        """
        Extract text from a page using OCR.
        
        Renders the page as an image and runs Tesseract OCR.
        """
        try:
            import pytesseract
            from PIL import Image
            import io
            
            # Render page to image (72 DPI is usually sufficient for OCR)
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Run OCR
            text = pytesseract.image_to_string(image)
            return text
            
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
    
    def extract_chunks(self, pdf_path: str, 
                       force_ocr: bool = False) -> List[Dict[str, Any]]:
        """
        Extract text chunks from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            force_ocr: Force OCR even if text is detected
            
        Returns:
            List of chunk dicts with keys:
            - text: The chunk text
            - page_number: Page number (1-indexed)
            - chunk_index: Index within the document
            - section_heading: Detected section heading (if any)
            - bbox: Bounding box coordinates (if available)
        """
        chunks = []
        chunk_index = 0
        
        try:
            doc = fitz.open(pdf_path)
            
            # Determine if we need OCR
            needs_ocr = force_ocr or (self.use_ocr and self.detect_if_scanned(pdf_path))
            
            if needs_ocr and not self.is_ocr_available():
                print("Warning: OCR requested but Tesseract not available. Falling back to text extraction.")
                needs_ocr = False
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_number = page_num + 1  # 1-indexed
                
                # Detect section heading
                section_heading = self._detect_section_heading(page, page_number)
                
                # Extract text
                if needs_ocr:
                    text = self.extract_text_with_ocr(page)
                else:
                    text = self.extract_text_with_pymupdf(page)
                
                if not text.strip():
                    # Empty page, try OCR as fallback
                    if self.is_ocr_available():
                        text = self.extract_text_with_ocr(page)
                
                if not text.strip():
                    continue  # Skip empty pages
                
                # Split into sentences and create chunks
                sentences = self._split_into_sentences(text)
                page_chunks = self._create_chunks(sentences)
                
                for chunk_text in page_chunks:
                    # Get bounding box (approximate - first block on page)
                    bbox = None
                    try:
                        blocks = page.get_text("dict")["blocks"]
                        if blocks:
                            block = blocks[0]
                            bbox = (block.get("x0"), block.get("y0"),
                                   block.get("x1") - block.get("x0"),
                                   block.get("y1") - block.get("y0"))
                    except Exception:
                        pass
                    
                    chunks.append({
                        "text": chunk_text,
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                        "section_heading": section_heading,
                        "bbox": bbox,
                        "pdf_path": pdf_path
                    })
                    chunk_index += 1
            
            doc.close()
            
        except Exception as e:
            print(f"Error extracting from {pdf_path}: {e}")
            raise
        
        return chunks
    
    def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get metadata about a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict with keys: page_count, file_size, metadata
        """
        doc = fitz.open(pdf_path)
        
        metadata = {
            "page_count": len(doc),
            "file_size": os.path.getsize(pdf_path),
            "metadata": doc.metadata,
            "is_scanned": self.detect_if_scanned(pdf_path)
        }
        
        doc.close()
        return metadata
