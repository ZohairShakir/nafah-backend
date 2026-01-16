"""File and data hashing utilities."""

import hashlib
from pathlib import Path
from typing import Union


def hash_file(file_path: Union[str, Path]) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        SHA256 hash as hex string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def hash_data(data: Union[str, bytes]) -> str:
    """
    Compute SHA256 hash of data.
    
    Args:
        data: String or bytes data
        
    Returns:
        SHA256 hash as hex string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()
