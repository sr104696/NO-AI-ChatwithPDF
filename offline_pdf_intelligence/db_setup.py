"""
Database setup for Offline PDF Intelligence.

This module initializes the SQLite database schema for storing:
- PDF metadata (file paths, names)
- Extracted text chunks with page numbers
- BM25 index metadata
- Query history
- User tags, notes, and bookmarks
"""

import sqlite3
from pathlib import Path


def get_connection(db_path: str = "pdf_intelligence.db") -> sqlite3.Connection:
    """Get a database connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(db_path: str = "pdf_intelligence.db") -> None:
    """
    Create the database schema if it doesn't exist.
    
    Tables:
    - pdf_files: Metadata about indexed PDFs
    - chunks: Text chunks extracted from PDFs with page info
    - query_history: Search/query history for persistence
    - tags: User-defined tags for documents
    - notes: User notes attached to specific chunks/pages
    - bookmarks: Bookmarked locations in documents
    - bm25_index_meta: Metadata about BM25 index state
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # PDF files table - stores metadata about indexed PDFs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            file_size INTEGER,
            page_count INTEGER,
            is_scanned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chunks table - stores extracted text chunks with location info
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            section_heading TEXT,
            bbox_x REAL,
            bbox_y REAL,
            bbox_width REAL,
            bbox_height REAL,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE
        )
    """)
    
    # Index on chunks for fast lookup by PDF and page
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_pdf_page 
        ON chunks(pdf_id, page_number)
    """)
    
    # Index for text search (fallback when not using BM25)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_text 
        ON chunks(text)
    """)
    
    # Query history table - persists user queries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            detected_type TEXT,
            result_count INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tags table - user-defined document tags
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#808080',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # PDF-Tags relationship (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_tags (
            pdf_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(pdf_id, tag_id),
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    
    # Notes table - user notes on specific chunks/pages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER NOT NULL,
            page_number INTEGER,
            chunk_id INTEGER,
            note_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE,
            FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE SET NULL
        )
    """)
    
    # Bookmarks table - saved locations in documents
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE
        )
    """)
    
    # BM25 index metadata - tracks index state
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bm25_index_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER NOT NULL UNIQUE,
            index_path TEXT,
            num_chunks INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE
        )
    """)
    
    # FTS5 virtual table for full-text search (alternative to BM25)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
            text,
            section_heading,
            pdf_id UNINDEXED,
            page_number UNINDEXED,
            tokenize='porter unicode61'
        )
    """)
    
    # Trigger to sync chunks to FTS table on insert
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO fts_chunks(text, section_heading, pdf_id, page_number)
            VALUES (new.text, new.section_heading, new.pdf_id, new.page_number);
        END
    """)
    
    # Trigger to sync chunks to FTS table on delete
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            DELETE FROM fts_chunks WHERE rowid = old.id;
        END
    """)
    
    # Trigger to sync chunks to FTS table on update
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            UPDATE fts_chunks 
            SET text = new.text, section_heading = new.section_heading,
                pdf_id = new.pdf_id, page_number = new.page_number
            WHERE rowid = old.id;
        END
    """)
    
    conn.commit()
    conn.close()
    print(f"Database schema created successfully at: {db_path}")


def clear_all_data(db_path: str = "pdf_intelligence.db") -> None:
    """
    Clear all data from the database (for "Clear all data" feature).
    
    This deletes all records but keeps the schema intact.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Delete in order respecting foreign
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
    conn.close()
    print(f"All data cleared from database: {db_path}")


def drop_schema(db_path: str = "pdf_intelligence.db") -> None:
    """
    Drop all tables from the database (complete wipe).
    
    Use this to fully reset the database.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Drop tables in reverse dependency order
    cursor.execute("DROP TABLE IF EXISTS bm25_index_meta")
    cursor.execute("DROP TABLE IF EXISTS bookmarks")
    cursor.execute("DROP TABLE IF EXISTS notes")
    cursor.execute("DROP TABLE IF EXISTS pdf_tags")
    cursor.execute("DROP TABLE IF EXISTS tags")
    cursor.execute("DROP TABLE IF EXISTS query_history")
    cursor.execute("DROP TABLE IF EXISTS fts_chunks")
    cursor.execute("DROP TABLE IF EXISTS chunks")
    cursor.execute("DROP TABLE IF EXISTS pdf_files")
    
    conn.commit()
    conn.close()
    print(f"Database schema dropped: {db_path}")


if __name__ == "__main__":
    # Run schema creation when executed directly
    db_file = Path(__file__).parent / "pdf_intelligence.db"
    create_schema(str(db_file))
    print(f"Database initialized at: {db_file.absolute()}")
