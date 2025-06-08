"""
Miscellaneous utility functions for the backend.
This module contains reusable helper functions that are framework-agnostic.
"""

import logging
import time
import os
import hashlib
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

# Type variable for generic function type
T = TypeVar('T')

def timing_decorator(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to measure and log the execution time of a function.
    
    Args:
        func: The function to measure
        
    Returns:
        Wrapped function that logs execution time
        
    Example:
        @timing_decorator
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Function '{func.__name__}' executed in {duration:.4f} seconds")
        return result
    return wrapper

def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Clean and normalize text by removing extra whitespace and special characters.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text or None if input is None
        
    Example:
        >>> clean_text("  Hello   World  ")
        'Hello World'
    """
    if not isinstance(text, str):
        return text
    
    # Remove leading/trailing whitespace and normalize internal spaces
    cleaned = ' '.join(text.strip().split())
    return cleaned

def generate_id(content: str) -> str:
    """
    Generate a unique ID for the provided content using SHA-256 hashing.
    
    Args:
        content: Content to generate ID for
        
    Returns:
        SHA-256 hash of the content
        
    Example:
        >>> generate_id("test content")
        'a8cfcd74832004951b4408cdb0e5c166'
    """
    return hashlib.sha256(content.encode()).hexdigest()

def format_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    
    Returns:
        Current timestamp as ISO format string
        
    Example:
        >>> format_timestamp()
        '2024-02-14T12:34:56.789Z'
    """
    return datetime.utcnow().isoformat() + 'Z'

def ensure_directory(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to directory
        
    Example:
        >>> ensure_directory("path/to/dir")
    """
    if not os.path.exists(directory):
        logger.info(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)

def clean_dict(d: dict) -> dict:
    """
    Remove None values from a dictionary.
    
    Args:
        d: Dictionary to clean
        
    Returns:
        Dictionary with None values removed
        
    Example:
        >>> clean_dict({"a": 1, "b": None, "c": 3})
        {'a': 1, 'c': 3}
    """
    return {k: v for k, v in d.items() if v is not None}

def safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values without raising KeyError.
    
    Args:
        obj: Object to get value from
        *keys: Sequence of keys to traverse
        default: Default value if key not found
        
    Returns:
        Value if found, default otherwise
        
    Example:
        >>> safe_get({"a": {"b": 1}}, "a", "b")
        1
        >>> safe_get({"a": {"b": 1}}, "a", "c", default=0)
        0
    """
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is None:
            return default
    return current

def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
        
    Example:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
        
    Example:
        >>> format_file_size(1024)
        '1.0 KB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB" 