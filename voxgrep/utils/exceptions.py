"""
VoxGrep Exception Hierarchy

Defines custom exceptions for better error handling and debugging.
"""


class VoxGrepError(Exception):
    """Base exception for all VoxGrep errors."""
    pass


# ============================================================================
# File and I/O Errors
# ============================================================================
class FileNotFoundError(VoxGrepError):
    """Raised when a required file is not found."""
    pass


class TranscriptNotFoundError(VoxGrepError):
    """Raised when a transcript file cannot be found for a media file."""
    pass


class InvalidFileFormatError(VoxGrepError):
    """Raised when a file format is not supported."""
    pass


# ============================================================================
# Transcription Errors
# ============================================================================
class TranscriptionError(VoxGrepError):
    """Base exception for transcription-related errors."""
    pass


class TranscriptionModelNotAvailableError(TranscriptionError):
    """Raised when a transcription model is not available."""
    pass


class TranscriptionFailedError(TranscriptionError):
    """Raised when transcription fails."""
    pass


# ============================================================================
# Search Errors
# ============================================================================
class SearchError(VoxGrepError):
    """Base exception for search-related errors."""
    pass


class NoResultsFoundError(SearchError):
    """Raised when a search returns no results."""
    pass


class InvalidSearchTypeError(SearchError):
    """Raised when an invalid search type is specified."""
    pass


class SemanticSearchNotAvailableError(SearchError):
    """Raised when semantic search is requested but dependencies are missing."""
    pass


# ============================================================================
# Export Errors
# ============================================================================
class ExportError(VoxGrepError):
    """Base exception for export-related errors."""
    pass


class InvalidOutputFormatError(ExportError):
    """Raised when an unsupported output format is specified."""
    pass


class ExportFailedError(ExportError):
    """Raised when export operation fails."""
    pass


# ============================================================================
# Server Errors
# ============================================================================
class ServerError(VoxGrepError):
    """Base exception for server-related errors."""
    pass


class DatabaseError(ServerError):
    """Raised when a database operation fails."""
    pass


class LibraryScanError(ServerError):
    """Raised when library scanning fails."""
    pass
