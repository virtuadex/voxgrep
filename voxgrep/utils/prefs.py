import json
import os
from typing import Dict, Any
from .config import get_data_dir

PREFS_FILE = get_data_dir() / "prefs.json"

DEFAULT_PREFS = {
    "device": "cpu",
    "whisper_model": "base",
    "search_type": "sentence",
    "preview": False,
    "demo": False,
}

def _get_prefs_file():
    """Get the preferences file path (lazy evaluation)."""
    return get_data_dir() / "prefs.json"

def load_prefs() -> Dict[str, Any]:
    """Load user preferences from JSON file."""
    prefs_file = _get_prefs_file()
    if not prefs_file.exists():
        return DEFAULT_PREFS.copy()
    
    try:
        with open(prefs_file, "r") as f:
            prefs = json.load(f)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_PREFS, **prefs}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_PREFS.copy()

def save_prefs(prefs: Dict[str, Any]):
    """Save user preferences to JSON file."""
    prefs_file = _get_prefs_file()
    try:
        with open(prefs_file, "w") as f:
            json.dump(prefs, f, indent=4)
    except OSError:
        pass # Silently fail if we can't write prefs
