"""
VoxGrep FastAPI Service

Main API server for the VoxGrep desktop application.
Provides endpoints for library management, search, transcription, and export.
"""
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .db import engine, create_db_and_tables
from .vector_store import EmbeddingModel
from .routers import (
    library_router, ingest_router, media_router,
    search_router, index_router, speaker_router,
    export_router, system_router
)
from .dependencies import config, features, logger
from .routers.library import _scan_path

app = FastAPI(
    title="VoxGrep Service",
    version="0.3.0",
    description="VoxGrep API - Search through video dialog and create supercuts"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(system_router)
app.include_router(library_router)
app.include_router(ingest_router) # Top-level /download, /add-local
app.include_router(media_router)  # Top-level /media
app.include_router(search_router)
app.include_router(index_router)
app.include_router(speaker_router)
app.include_router(export_router)


# ============================================================================
# Startup & Lifecycle
# ============================================================================
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Auto-scan downloads folder on startup
    with Session(engine) as session:
        _scan_path(config.downloads_dir, session)
    
    # Pre-warm the semantic model in a background thread
    if features.enable_semantic_search:
        def pre_load_model():
            try:
                logger.info("Pre-loading semantic model...")
                EmbeddingModel.get_instance()
                logger.info("Semantic model loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to pre-load semantic model: {e}")
        
        threading.Thread(target=pre_load_model, daemon=True).start()
            
    logger.info(f"VoxGrep Server v0.3.0 started. Database initialized.")


def main():
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)

if __name__ == "__main__":
    main()
