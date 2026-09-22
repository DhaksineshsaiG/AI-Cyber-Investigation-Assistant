import hashlib
from typing import Union
import os

def calculate_sha256(data_or_path: Union[bytes, str]) -> str:
    """Calculates SHA-256 cryptographic hash of bytes or a file on disk."""
    hasher = hashlib.sha256()
    if isinstance(data_or_path, bytes):
        hasher.update(data_or_path)
    elif isinstance(data_or_path, str) and os.path.exists(data_or_path):
        with open(data_or_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
    else:
        raise ValueError("Input must be valid bytes or an existing file path.")
    return hasher.hexdigest()

def calculate_md5(data_or_path: Union[bytes, str]) -> str:
    """Calculates MD5 hash for secondary verification."""
    hasher = hashlib.md5()
    if isinstance(data_or_path, bytes):
        hasher.update(data_or_path)
    elif isinstance(data_or_path, str) and os.path.exists(data_or_path):
        with open(data_or_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
    else:
        raise ValueError("Input must be valid bytes or an existing file path.")
    return hasher.hexdigest()
