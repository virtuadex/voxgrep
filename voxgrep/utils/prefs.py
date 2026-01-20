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

def load_prefs() -> Dict[str, Any]:
    """Load user preferences from JSON file."""
    if not PREFS_FILE.exists():
        return DEFAULT_PREFS.copy()
    
    try:
        with open(PREFS_FILE, "r") as f:
            prefs = json.load(f)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_PREFS, **prefs}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_PREFS.copy()

def save_prefs(prefs: Dict[str, Any]):
    """Save user preferences to JSON file."""
    try:
        with open(PREFS_FILE, "w") as f:
            json.dump(prefs, f, indent=4)
    except OSError:
        pass # Silently fail if we can't write prefs
