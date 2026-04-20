# NO-AI-ChatwithPDF

This repository consolidates several high-performance, local-first PDF search and querying tools. These tools are designed to work without relying on external LLM services for their core search logic.

## Directory Structure

### [1_TFIDF_Scratch](./1_TFIDF_Scratch)
- **Source**: [shreyansh-kothari/PDF-Querying-using-TF-IDF-from-Scratch](https://github.com/shreyansh-kothari/PDF-Querying-using-TF-IDF-from-Scratch)
- **Use Case**: Core TF-IDF ranking logic built from scratch. Ideal for lightweight integration or learning the math behind search.

### [2_BM25_Search](./2_BM25_Search)
- **Source**: [Topping1/BM25-PDF-Search](https://github.com/Topping1/BM25-PDF-Search)
- **Use Case**: A PyQt5 GUI application implementing BM25 search. Features keyword highlighting and result navigation.

### [3_FTS_OCR_Search](./3_FTS_OCR_Search)
- **Source**: [Ap6pack/PDF-Search-Plus](https://github.com/Ap6pack/PDF-Search-Plus)
- **Use Case**: Feature-complete application with SQLite FTS5 (Full-Text Search), OCR capabilities via Tesseract, and deep document indexing.

## Setup

Refer to the individual `README.md` files in each directory for specific setup and usage instructions.
