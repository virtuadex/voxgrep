"""
VoxGrep Vector Store Module

Provides vector storage and similarity search for semantic search across the entire library.
Uses sqlite-vss or falls back to in-memory numpy for vector operations.
"""
import os
import json
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime

from sqlmodel import Session, select

from ..config import get_cache_dir, DEFAULT_SEMANTIC_MODEL
from ..utils import setup_logger
from .db import engine
from .models import Video, Embedding

logger = setup_logger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class EmbeddingModel:
    """Singleton for the sentence transformer model used for embeddings."""
    _instance: Optional[SentenceTransformer] = None
    _model_name: str = DEFAULT_SEMANTIC_MODEL
    
    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> SentenceTransformer:
        """Get or create the embedding model instance."""
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("sentence-transformers is not installed")
        
        target_model = model_name or cls._model_name
        if cls._instance is None or target_model != cls._model_name:
            logger.info(f"Loading embedding model: {target_model}")
            cls._instance = SentenceTransformer(target_model)
            cls._model_name = target_model
        return cls._instance
    
    @classmethod
    def get_embedding_dim(cls) -> int:
        """Get the dimension of embeddings produced by the model."""
        model = cls.get_instance()
        return model.get_sentence_embedding_dimension()


class VectorStore:
    """
    Vector store for semantic search across the VoxGrep library.
    
    Stores embeddings in SQLite with the Embedding model and uses
    numpy for similarity calculations. Can be extended to use
    specialized vector databases like sqlite-vss or LanceDB.
    """
    
    def __init__(self):
        self._embedding_cache: Dict[int, np.ndarray] = {}
        self._index_dirty = True
        self._combined_embeddings: Optional[np.ndarray] = None
        self._embedding_video_map: List[Tuple[int, int, dict]] = []  # (video_id, segment_idx, segment_data)
    
    def index_video(
        self, 
        video_id: int, 
        transcript: List[dict],
        session: Session,
        force: bool = False
    ) -> int:
        """
        Generate and store embeddings for a video's transcript.
        
        Args:
            video_id: Database ID of the video
            transcript: List of transcript segments with 'content' key
            session: Database session
            force: If True, regenerate embeddings even if they exist
            
        Returns:
            Number of embeddings created
        """
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Cannot index video: sentence-transformers not available")
            return 0
        
        # Check if already indexed
        if not force:
            existing = session.exec(
                select(Embedding).where(Embedding.video_id == video_id)
            ).first()
            if existing:
                logger.debug(f"Video {video_id} already indexed, skipping")
                return 0
        else:
            # Delete existing embeddings for this video
            existing_embeddings = session.exec(
                select(Embedding).where(Embedding.video_id == video_id)
            ).all()
            for emb in existing_embeddings:
                session.delete(emb)
            session.commit()
        
        # Generate embeddings
        model = EmbeddingModel.get_instance()
        texts = [seg.get("content", "") for seg in transcript]
        
        if not texts:
            return 0
        
        logger.info(f"Generating {len(texts)} embeddings for video {video_id}")
        embeddings = model.encode(texts, show_progress_bar=False)
        
        # Store in database
        for i, (segment, embedding) in enumerate(zip(transcript, embeddings)):
            emb_record = Embedding(
                video_id=video_id,
                segment_index=i,
                segment_start=segment.get("start", 0),
                segment_end=segment.get("end", 0),
                segment_content=segment.get("content", ""),
                embedding_blob=embedding.tobytes(),
                embedding_dim=len(embedding)
            )
            session.add(emb_record)
        
        session.commit()
        self._index_dirty = True
        logger.info(f"Indexed {len(transcript)} segments for video {video_id}")
        return len(transcript)
    
    def _rebuild_index(self, session: Session) -> None:
        """Rebuild the in-memory index from database."""
        logger.debug("Rebuilding vector index from database")
        
        all_embeddings = session.exec(select(Embedding)).all()
        
        if not all_embeddings:
            self._combined_embeddings = None
            self._embedding_video_map = []
            self._index_dirty = False
            return
        
        # Build numpy array and metadata
        embedding_list = []
        self._embedding_video_map = []
        
        for emb in all_embeddings:
            vector = np.frombuffer(emb.embedding_blob, dtype=np.float32)
            embedding_list.append(vector)
            self._embedding_video_map.append((
                emb.video_id,
                emb.segment_index,
                {
                    "start": emb.segment_start,
                    "end": emb.segment_end,
                    "content": emb.segment_content
                }
            ))
        
        self._combined_embeddings = np.vstack(embedding_list)
        self._index_dirty = False
        logger.debug(f"Vector index rebuilt with {len(embedding_list)} vectors")
    
    def search(
        self,
        query: str,
        session: Session,
        threshold: float = 0.45,
        limit: int = 100,
        video_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Perform semantic search across the entire indexed library.
        
        Args:
            query: Search query text
            session: Database session
            threshold: Minimum similarity score (0-1)
            limit: Maximum number of results
            video_ids: Optional list of video IDs to restrict search to
            
        Returns:
            List of matching segments with scores
        """
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Semantic search requires sentence-transformers")
        
        # Rebuild index if needed
        if self._index_dirty:
            self._rebuild_index(session)
        
        if self._combined_embeddings is None or len(self._combined_embeddings) == 0:
            return []
        
        # Encode query
        model = EmbeddingModel.get_instance()
        query_embedding = model.encode([query], show_progress_bar=False)[0]
        
        # Calculate cosine similarity
        # Normalize embeddings for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = self._combined_embeddings / np.linalg.norm(
            self._combined_embeddings, axis=1, keepdims=True
        )
        
        scores = np.dot(embeddings_norm, query_norm)
        
        # Filter by threshold and video_ids
        results = []
        for idx, score in enumerate(scores):
            if score < threshold:
                continue
            
            video_id, segment_idx, segment_data = self._embedding_video_map[idx]
            
            if video_ids is not None and video_id not in video_ids:
                continue
            
            # Get video path from database
            video = session.get(Video, video_id)
            if not video:
                continue
            
            results.append({
                "file": video.path,
                "start": segment_data["start"],
                "end": segment_data["end"],
                "content": segment_data["content"],
                "score": float(score),
                "video_id": video_id
            })
        
        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def get_stats(self, session: Session) -> dict:
        """Get statistics about the vector index."""
        total_embeddings = len(session.exec(select(Embedding)).all())
        indexed_videos = len(set(
            e.video_id for e in session.exec(select(Embedding)).all()
        ))
        
        return {
            "total_embeddings": total_embeddings,
            "indexed_videos": indexed_videos,
            "embedding_dim": EmbeddingModel.get_embedding_dim() if TRANSFORMERS_AVAILABLE else 0,
            "model_name": EmbeddingModel._model_name if TRANSFORMERS_AVAILABLE else None
        }
    
    def remove_video(self, video_id: int, session: Session) -> int:
        """Remove all embeddings for a video."""
        embeddings = session.exec(
            select(Embedding).where(Embedding.video_id == video_id)
        ).all()
        
        count = len(embeddings)
        for emb in embeddings:
            session.delete(emb)
        
        session.commit()
        self._index_dirty = True
        return count


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
