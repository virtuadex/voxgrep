"""
Routers for VoxGrep Server
"""
from .library import router as library_router, ingest_router, media_router
from .search import router as search_router, index_router, speaker_router
from .export import router as export_router
from .system import router as system_router
