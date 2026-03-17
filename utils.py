"""Utility functions for safe JSON operations and data handling"""
import json
import os
import tempfile
from pathlib import Path


def safe_save_json(data, filepath):
    """
    Save JSON data safely using atomic write.
    
    Prevents file corruption if bot crashes during write by:
    1. Writing to temporary file first
    2. Atomically renaming temp file to target path
    
    Args:
        data: Dictionary to save
        filepath: Path to save JSON file
    """
    # Ensure directory exists
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temporary file in same directory (ensures same filesystem)
    dir_path = os.path.dirname(filepath) or '.'
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=dir_path,
        delete=False,
        suffix='.json'
    ) as tf:
        json.dump(data, tf, indent=2)
        tempname = tf.name
    
    # Atomic rename - this operation cannot be interrupted
    try:
        os.replace(tempname, filepath)
    except Exception as e:
        # Clean up temp file if rename fails
        try:
            os.unlink(tempname)
        except:
            pass
        raise e
