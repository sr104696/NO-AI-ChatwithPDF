"""
Database utilities for Offline PDF Intelligence.

Provides parameterized query helpers and database connection management.
All queries use parameterized statements to prevent SQL injection.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager


class DatabaseManager:
    """
    Manages SQLite database connections and provides safe query methods.
    
    All methods use parameterized queries to prevent SQL injection.
    """
    
    def __init__(self, db_path: str = "pdf_intelligence.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # Enable dict-like row access
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_pdf_file(self, file_name: str, file_path: str, 
                        file_size: int, page_count: int, 
                        is_scanned: bool = False) -> int:
        """
        Insert a PDF file record into the database.
        
        Uses parameterized query to prevent SQL injection.
        
        Args:
            file_name: Name of the PDF file
            file_path: Absolute path to the PDF file
            file_size: File size in bytes
            page_count: Number of pages in the PDF
            is_scanned: Whether the PDF is scanned (requires OCR)
            
        Returns:
            The ID of the inserted record
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pdf_files (file_name, file_path, file_size, page_count, is_scanned)
                VALUES (?, ?, ?, ?, ?)
            """, (file_name, file_path, file_size, page_count, 1 if is_scanned else 0))
            conn.commit()
            return cursor.lastrowid
    
    def get_pdf_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get PDF record by file path using parameterized query.
        
        Args:
            file_path: Absolute path to the PDF file
            
        Returns:
            PDF record as dict, or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pdf_files WHERE file_path = ?
            """, (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_pdf_by_id(self, pdf_id: int) -> Optional[Dict[str, Any]]:
        """Get PDF record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pdf_files WHERE id = ?", (pdf_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def insert_chunk(self, pdf_id: int, chunk_index: int, page_number: int,
                     text: str, section_heading: Optional[str] = None,
                     bbox: Optional[Tuple[float, float, float, float]] = None) -> int:
        """
        Insert a text chunk into the database.
        
        Args:
            pdf_id: ID of the parent PDF
            chunk_index: Index of the chunk within the PDF
            page_number: Page number where the chunk appears
            text: Text content of the chunk
            section_heading: Detected section heading (if any)
            bbox: Bounding box coordinates (x, y, width, height)
            
        Returns:
            The ID of the inserted chunk
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            bbox_params = bbox if bbox else (None, None, None, None)
            cursor.execute("""
                INSERT INTO chunks (pdf_id, chunk_index, page_number, text, 
                                    section_heading, bbox_x, bbox_y, bbox_width, bbox_height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (pdf_id, chunk_index, page_number, text, section_heading, 
                  *bbox_params))
            conn.commit()
            return cursor.lastrowid
    
    def get_chunks_for_pdf(self, pdf_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a PDF."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chunks WHERE pdf_id = ? ORDER BY chunk_index
            """, (pdf_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def save_query(self, query_text: str, detected_type: Optional[str], 
                   result_count: int) -> int:
        """Save a query to history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO query_history (query_text, detected_type, result_count)
                VALUES (?, ?, ?)
            """, (query_text, detected_type, result_count))
            conn.commit()
            return cursor.lastrowid
    
    def get_query_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent query history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM query_history 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_tag(self, name: str, color: str = "#808080") -> int:
        """Add a new tag."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)
            """, (name, color))
            conn.commit()
            cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row['id'] if row else 0
    
    def tag_pdf(self, pdf_id: int, tag_id: int) -> None:
        """Associate a tag with a PDF."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO pdf_tags (pdf_id, tag_id) VALUES (?, ?)
            """, (pdf_id, tag_id))
            conn.commit()
    
    def add_note(self, pdf_id: int, page_number: Optional[int],
                 chunk_id: Optional[int], note_text: str) -> int:
        """Add a note."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (pdf_id, page_number, chunk_id, note_text)
                VALUES (?, ?, ?, ?)
            """, (pdf_id, page_number, chunk_id, note_text))
            conn.commit()
            return cursor.lastrowid
    
    def add_bookmark(self, pdf_id: int, page_number: int, 
                     label: Optional[str] = None) -> int:
        """Add a bookmark."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bookmarks (pdf_id, page_number, label)
                VALUES (?, ?, ?)
            """, (pdf_id, page_number, label))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_pdfs(self) -> List[Dict[str, Any]]:
        """Get all indexed PDFs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pdf_files ORDER BY file_name")
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_pdf(self, pdf_id: int) -> None:
        """Delete a PDF and all associated data (cascades)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pdf_files WHERE id = ?", (pdf_id,))
            conn.commit()
    
    def clear_all_data(self) -> None:
        """Clear all data from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Delete in order respecting foreign keys
            cursor.execute("DELETE FROM bm25_index_meta")
            cursor.execute("DELETE FROM bookmarks")
            cursor.execute("DELETE FROM notes")
            cursor.execute("DELETE FROM pdf_tags")
            cursor.execute("DELETE FROM tags")
            cursor.execute("DELETE FROM query_history")
            cursor.execute("DELETE FROM fts_chunks")
            cursor.execute("DELETE FROM chunks")
            cursor.execute("DELETE FROM pdf_files")
            conn.commit()
