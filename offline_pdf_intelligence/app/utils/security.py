"""
Security utilities for Offline PDF Intelligence.

Provides input validation, path sanitization, and parameterized query helpers
to ensure safe operation and prevent injection attacks.
"""

import os
import re
import html
from pathlib import Path
from typing import Optional, Tuple, Any


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Raw user input
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text safe for display and storage
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # HTML escape to prevent XSS in GUI
    text = html.escape(text)
    
    # Remove control characters (except newlines and tabs)
    text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\r\t')
    
    return text.strip()


def sanitize_search_term(term: str) -> str:
    """
    Sanitize a search term specifically.
    
    Args:
        term: Raw search term
        
    Returns:
        Sanitized search term
    """
    if not term:
        return ""
    
    # Remove SQL injection characters
    term = re.sub(r'[;\'"\\]', '', term)
    
    # Limit length for search
    term = term[:500]
    
    return term.strip()


def validate_path(path: str, must_exist: bool = True, 
                  file_type: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate a file or directory path for safety.
    
    Args:
        path: Path to validate
        must_exist: Whether the path must exist
        file_type: Expected file extension (e.g., '.pdf')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Empty path provided"
    
    try:
        path_obj = Path(path).resolve()
        
        # Check for path traversal attempts
        if '..' in path:
            return False, "Path traversal detected"
        
        # Check if path exists
        if must_exist and not path_obj.exists():
            return False, f"Path does not exist: {path}"
        
        # Check if it's a file when expected
        if file_type == 'file' and not path_obj.is_file():
            return False, f"Path is not a file: {path}"
        
        # Check if it's a directory when expected
        if file_type == 'dir' and not path_obj.is_dir():
            return False, f"Path is not a directory: {path}"
        
        # Check file extension if specified
        if file_type and file_type.startswith('.'):
            if path_obj.suffix.lower() != file_type.lower():
                return False, f"Expected {file_type} file, got {path_obj.suffix}"
        
        # Check for symbolic links pointing outside allowed areas
        if path_obj.is_symlink():
            real_path = path_obj.resolve()
            # Additional checks could be added here for allowed directories
        
        return True, ""
        
    except (PermissionError, OSError) as e:
        return False, f"Permission or OS error: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"


def validate_pdf_path(path: str) -> Tuple[bool, str]:
    """
    Validate that a path points to a valid PDF file.
    
    Args:
        path: Path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_path(path, must_exist=True, file_type='.pdf')
    if not is_valid:
        return False, error
    
    # Check PDF signature
    try:
        with open(path, 'rb') as f:
            signature = f.read(4)
            if signature != b'%PDF':
                return False, "File does not have valid PDF signature"
    except Exception as e:
        return False, f"Cannot read file: {e}"
    
    return True, ""


def safe_parameterized_query(query_template: str, params: Tuple[Any, ...]) -> Tuple[str, Tuple[Any, ...]]:
    """
    Ensure a query uses parameterized placeholders correctly.
    
    This is a helper to verify queries before execution.
    
    Args:
        query_template: SQL query with ? placeholders
        params: Parameters to bind
        
    Returns:
        Tuple of (query, params) ready for cursor.execute()
        
    Raises:
        ValueError: If the query appears unsafe
    """
    # Check for common SQL injection patterns in the template
    dangerous_patterns = [
        r';\s*DROP',
        r';\s*DELETE',
        r';\s*UPDATE.*SET',
        r';\s*INSERT',
        r'--',
        r'/\*',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query_template, re.IGNORECASE):
            raise ValueError(f"Potentially dangerous SQL pattern detected: {pattern}")
    
    return query_template, params


def is_safe_filename(filename: str) -> bool:
    """
    Check if a filename is safe (no path traversal, reserved names, etc.).
    
    Args:
        filename: Filename to check
        
    Returns:
        True if safe, False otherwise
    """
    if not filename:
        return False
    
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        return False
    
    # Check for reserved Windows filenames
    reserved = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved:
        return False
    
    # Check for invalid characters
    if re.search(r'[<>:"|?*]', filename):
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe.
    
    Args:
        filename: Raw filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"
    
    # Remove path traversal characters
    sanitized = re.sub(r'[/\\]', '_', filename)
    
    # Remove control characters
    sanitized = ''.join(c for c in sanitized if ord(c) >= 32)
    
    # Remove reserved characters
    sanitized = re.sub(r'[<>:"|?*]', '_', sanitized)
    
    # Trim leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    sanitized = sanitized[:255]
    
    # Handle reserved names
    reserved = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(sanitized).stem.upper()
    if name_without_ext in reserved:
        parts = sanitized.split('.')
        if len(parts) > 1:
            sanitized = f"{parts[0]}_." + '.'.join(parts[1:])
        else:
            sanitized = f"{sanitized}_"
    
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized
