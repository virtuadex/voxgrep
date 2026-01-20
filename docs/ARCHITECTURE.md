# VoxGrep Architecture & Development

VoxGrep is a modular, service-oriented application designed to search through time-based media as if it were text.

## 🏗️ System Architecture

VoxGrep has evolved from a stateless CLI tool into a **Service-Oriented Desktop Application** comprising three main components:

### 1. Core Package (`voxgrep/`)

The Python library containing the business logic:

- `search_engine.py`: Transcript parsing and regex/semantic search logic.
- `transcribe.py`: Unified wrapper for transcription backends.
- `exporter.py`: Media processing using MoviePy 2.x.
- `voxgrep.py`: High-level orchestration for CLI and API.

### 2. FastAPI Server (`voxgrep/server/`)

A persistent REST API that manages the library and background tasks:

- `app.py`: Main endpoints for the desktop application.
- `vector_store.py`: Embedding storage using Sentence-Transformers.
- `diarization.py`: Speaker detection via pyannote.audio.
- `transitions.py`: Video transition and audio smoothing logic.
- `multi_model.py`: Management of MLX, faster-whisper, and OpenAI backends.

### 3. Desktop App (`desktop/`)

A premium GUI built with **Tauri**, **React**, and **TypeScript**:

- Uses native system APIs for file management and window control.
- Communicates with the Python backend via a high-performance local bridge.

---

## 📊 Database Schema

VoxGrep uses **SQLModel (SQLite)** for persistent state.

### Video Table

Metadata for indexed media files (path, duration, transcription status).

### Embedding Table

Vector embeddings for semantic search segments, linked to video segments.

### Speaker Table

Diarization results mapping speakers to time ranges and labels.

---

## 🛰️ API Overview

| Category     | Endpoints                                                                 |
| :----------- | :------------------------------------------------------------------------ |
| **Core**     | `/health`, `/library`, `/library/scan`, `/download`, `/search`, `/export` |
| **Semantic** | `/index/{id}`, `/index/all`, `/index/stats`                               |
| **Speaker**  | `/diarize/{id}`, `/speakers/{id}`                                         |
| **Models**   | `/models`, `/transcribe/{id}`, `/subtitle-presets`                        |

---

## 🚦 Phase Status (v3.0.0)

### Phase 1: Foundation ✅

- [x] Migration to FastAPI persistent service.
- [x] SQLite central database for indexing.
- [x] Background task processing for long-running jobs.

### Phase 2: Semantic Power ✅

- [x] Vector indexing with `all-MiniLM-L6-v2`.
- [x] Global library search across all videos.
- [x] Speaker diarization support.

### Phase 3: Advanced Media ✅

- [x] Dynamic transitions (crossfade, dissolve, etc.).
- [x] Embedded subtitle burning with style presets.
- [x] Unified model management for MLX/Whisper/OpenAI.

---

## 🛠️ Development Conventions

- **Local-First**: All AI processing happens locally; data never leaves the machine.
- **Feature Flags**: Toggle features (e.g., `enable_semantic_search`) in `voxgrep/config.py`.
- **Naming Service**: Media and transcripts share base names (e.g., `clip.mp4` -> `clip.json`).
- **Caching**: Transcripts and embeddings are aggressively cached for performance.

## 📈 Performance Notes

- **MLX Acceleration**: 2-5x speedup on Apple Silicon vs CPU.
- **Vector Search**: Near-instant after the model is first loaded into memory.
- **Batching**: Large exports are automatically batched to prevent memory exhaustion.
