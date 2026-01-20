"""
Routers for VoxGrep Server
"""
from .library import router as library_router
from .ingest import router as ingest_router
from .media import router as media_router
from .search import router as search_router
from .index import router as index_router
from .speaker import router as speaker_router
from .export import router as export_router
from .system import router as system_router
