"""
Common dependencies for VoxGrep Server routers.
"""
from typing import Generator
from sqlmodel import Session
from fastapi import Depends

from .db import engine, get_session as _get_db_session
from .vector_store import get_vector_store as _get_vector_store
from .multi_model import get_model_manager as _get_model_manager
from ..utils.config import ServerConfig, FeatureFlags
from ..utils.helpers import setup_logger

# Initialize configuration
config = ServerConfig()
features = FeatureFlags()

logger = setup_logger("voxgrep.server", level=config.log_level)

def get_session():
    """Dependency wrapper for database session."""
    return _get_db_session()

def get_vector_store():
    """Dependency wrapper for vector store."""
    return _get_vector_store()

def get_model_manager():
    """Dependency wrapper for model manager."""
    return _get_model_manager()
