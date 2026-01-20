"""
Formats package for VoxGrep.

This package contains modules for parsing and rendering various subtitle
and export formats (VTT, SRT, Sphinx, FCPXML).
"""

# Import all format modules for easy access
from . import vtt
from . import srt
from . import sphinx
from . import fcpxml

__all__ = ["vtt", "srt", "sphinx", "fcpxml"]
