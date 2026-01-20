import shutil
import sys
import subprocess
import os
from typing import Optional, List

from ..utils.helpers import setup_logger

logger = setup_logger(__name__)

# Cache for MPV availability
_MPV_AVAILABLE: Optional[bool] = None

def check_mpv_available() -> bool:
    """
    Check if MPV is installed and available in the system PATH.
    Refreshes cache only if previously unchecked.
    """
    global _MPV_AVAILABLE
    if _MPV_AVAILABLE is None:
        _MPV_AVAILABLE = shutil.which("mpv") is not None
        if _MPV_AVAILABLE:
            # Optional: Check version to be sure it's working
            try:
                subprocess.run(
                    ["mpv", "--version"], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                _MPV_AVAILABLE = False
    
    return _MPV_AVAILABLE

def get_mpv_install_instructions() -> str:
    """Get platform-specific MPV installation instructions."""
    if sys.platform == "win32":
        return (
            "MPV is not installed or not in your PATH.\n"
            "To install on Windows:\n"
            "  1. Run 'winget install mpv'\n"
            "  2. Or download from https://mpv.io/installation/"
        )
    elif sys.platform == "darwin":
        return (
            "MPV is not installed.\n"
            "To install on macOS:\n"
            "  brew install mpv"
        )
    else:  # Linux/Other
        return (
            "MPV is not installed.\n"
            "To install on Linux (Ubuntu/Debian):\n"
            "  sudo apt install mpv"
        )

def launch_mpv_preview(segments: List[dict]) -> bool:
    """
    Launch MPV to preview the given segments as a playlist.
    
    Args:
        segments: List of segment dictionaries with 'file', 'start', 'end' keys
        
    Returns:
        True if launched successfully, False otherwise
    """
    if not segments:
        return False
        
    if not check_mpv_available():
        logger.warning("MPV not found when attempting to launch preview.")
        return False
    
    try:
        # Construct EDL (Edit Decision List) for MPV
        # Format: # mpv EDL v0
        # file,start,length
        lines = ["# mpv EDL v0"]
        for s in segments:
            abs_path = os.path.abspath(s['file'])
            duration = s['end'] - s['start']
            lines.append(f"{abs_path},{s['start']},{duration}")
            
        playlist_str = "\n".join(lines)
        
        logger.info(f"Launching MPV with {len(segments)} segments...")
        
        # Run MPV taking playlist from stdin
        subprocess.run(
            ["mpv", "-"], 
            input=playlist_str.encode("utf-8"), 
            check=True
        )
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        logger.error(f"Failed to launch MPV: {e}")
        return False
