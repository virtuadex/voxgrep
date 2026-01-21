import shutil
import sys
import subprocess
import os


from ..utils.helpers import setup_logger

logger = setup_logger(__name__)

# Cache for MPV availability
_MPV_AVAILABLE: bool | None = None

def check_mpv_available(force_refresh: bool = False) -> bool:
    """
    Check if MPV is installed and available in the system PATH.
    
    Args:
        force_refresh: If True, ignore cache and re-check system.
        
    Returns:
        True if MPV is available and working.
    """
    global _MPV_AVAILABLE
    
    if _MPV_AVAILABLE is not None and not force_refresh:
        return _MPV_AVAILABLE

    # Check if executable exists
    path = shutil.which("mpv")
    if not path:
        _MPV_AVAILABLE = False
        return False

    # Check if executable actually runs
    try:
        subprocess.run(
            ["mpv", "--version"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=3  # Add timeout to prevent hangs
        )
        _MPV_AVAILABLE = True
    except (subprocess.SubprocessError, OSError):
        # Covers TimeoutExpired, CalledProcessError, FileNotFoundError, etc.
        logger.warning("MPV executable found but failed to run --version check.")
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

def launch_mpv_file(file_path: str) -> bool:
    """
    Launch MPV to play a single file.
    
    Args:
        file_path: Path to the video file.
        
    Returns:
        True if launched successfully (exit code 0), False otherwise.
    """
    if not check_mpv_available():
        logger.warning("MPV not found when attempting to launch file.")
        return False
        
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False

    logger.info(f"Launching MPV for file: {file_path}")
    
    try:
        # We don't capture stdout/stderr here so the user can see MPV output directly if needed
        # or interact with the TUI if MPV has one (though usually it opens a window).
        subprocess.run(
            ["mpv", file_path],
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"MPV exited with error code {e.returncode}")
        return False
    except (FileNotFoundError, OSError) as e:
        logger.error(f"Failed to execute MPV: {e}")
        return False

def launch_mpv_preview(segments: list[dict]) -> bool:
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
            # We must use absolute paths
            abs_path = os.path.abspath(s['file'])
            if not os.path.exists(abs_path):
                logger.warning(f"Skipping missing file in preview: {abs_path}")
                continue
                
            start = max(0, float(s.get('start', 0)))
            end = float(s.get('end', 0))
            if end <= start:
                continue
                
            duration = end - start
            lines.append(f"{abs_path},{start:.4f},{duration:.4f}")
            
        if len(lines) <= 1:
            logger.warning("No valid segments to preview.")
            return False

        playlist_str = "\n".join(lines)
        
        logger.info(f"Launching MPV with {len(lines)-1} segments...")
        
        # Run MPV taking playlist from stdin
        subprocess.run(
            ["mpv", "-"], 
            input=playlist_str.encode("utf-8"), 
            check=True
        )
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"MPV exited with error (code {e.returncode}).")
        return False
    except (FileNotFoundError, OSError) as e:
        logger.error(f"Failed to launch MPV: {e}")
        return False
