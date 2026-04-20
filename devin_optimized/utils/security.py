"""
Security utilities: input validation and sanitization.

Merged and streamlined from 3_FTS_OCR_Search and offline_pdf_intelligence
security modules.  Key improvements:
- Single ``validate_pdf_path`` that checks existence, extension, and signature
- ``sanitize_text`` and ``sanitize_search_term`` kept concise
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Tuple


def sanitize_text(text: str) -> str:
    """Escape HTML entities and strip control characters."""
    if not text:
        return ""
    escaped = html.escape(text)
    return "".join(c for c in escaped if ord(c) >= 32 or c in "\n\r\t")


def sanitize_search_term(term: str, max_length: int = 500) -> str:
    """Remove SQL-injection characters and cap length."""
    if not term:
        return ""
    cleaned = re.sub(r"[;'\"\\]", "", term)
    return cleaned[:max_length].strip()


def validate_pdf_path(path: str) -> Tuple[bool, str]:
    """
    Validate that *path* points to an existing, readable PDF.

    Returns:
        ``(True, "")`` on success, ``(False, reason)`` on failure.
    """
    if not path:
        return False, "Empty path"

    p = Path(path).resolve()

    if ".." in str(path):
        return False, "Path traversal detected"

    if not p.exists():
        return False, f"File not found: {p}"

    if not p.is_file():
        return False, f"Not a regular file: {p}"

    if p.suffix.lower() != ".pdf":
        return False, f"Not a .pdf file: {p.suffix}"

    try:
        with open(p, "rb") as f:
            sig = f.read(4)
        if sig != b"%PDF":
            return False, "Invalid PDF signature"
    except Exception as exc:
        return False, f"Cannot read file: {exc}"

    return True, ""
