# CLAUDE.md - VoxGrep Project Guide

## Project Overview

**VoxGrep** is a powerful tool for searching through dialogue in video/audio files to automatically generate "supercuts" (compilations of matching clips). Think of it as `grep` for time-based media.

- **Version**: 3.0.0
- **License**: MIT
- **Python**: 3.10-3.12 (NOT 3.13)

## Quick Commands

```bash
# Run CLI (interactive mode)
poetry run voxgrep

# Run CLI with arguments
poetry run voxgrep -i "video.mp4" -s "search term" -o supercut.mp4

# Run server (FastAPI on :8000)
poetry run python -m voxgrep.server.app

# Run tests
poetry run pytest

# Environment diagnostics
poetry run voxgrep --doctor

# Desktop app (dev mode)
cd desktop && npm run tauri dev
```

## Directory Structure

```
voxgrep/
├── voxgrep/                 # Main Python package
│   ├── cli/                 # Command-line interface
│   │   ├── main.py         # Entry point & argument parser
│   │   ├── interactive.py  # Interactive wizard mode
│   │   ├── commands.py     # Command execution logic
│   │   └── doctor.py       # Environment diagnostics
│   ├── core/                # Core processing engines
│   │   ├── engine.py       # Search logic (regex, semantic)
│   │   ├── logic.py        # High-level orchestration
│   │   ├── exporter.py     # Video rendering & export
│   │   └── transcriber.py  # Multi-backend transcription
│   ├── server/              # FastAPI application
│   │   ├── app.py          # Main app & startup
│   │   ├── models.py       # SQLModel schemas
│   │   └── routers/        # API endpoints
│   ├── formats/             # Subtitle format handlers (VTT, SRT, FCPXML)
│   └── utils/
│       ├── config.py       # Central configuration
│       └── helpers.py      # Common utilities
├── desktop/                 # Tauri + React frontend
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Technology Stack

**Backend**: Python 3.10+, FastAPI, SQLModel (SQLite), MoviePy 2.x
**Transcription**: faster-whisper (CPU/CUDA), mlx-whisper (Apple Silicon)
**Semantic Search**: sentence-transformers, PyTorch, model: all-MiniLM-L6-v2
**Frontend**: Tauri 2.x, React 19, TypeScript, Vite, Tailwind CSS
**Required Tools**: FFmpeg, optionally mpv for preview

## Key Configuration

All constants are in `voxgrep/utils/config.py`:
- `BATCH_SIZE = 20` - Clips per batch during export
- `DEFAULT_PADDING = 0.3` - Seconds of padding around clips
- `DEFAULT_SEMANTIC_THRESHOLD = 0.45` - Similarity threshold
- `DEFAULT_WHISPER_MODEL = "base"` - Transcription model

## Search Types

- **Sentence** (default): Match full lines of dialogue
- **Fragment**: Exact phrase matching with ms precision
- **Semantic**: Concept-based similarity search using embeddings
- **Mash**: Random word compilation

## Development Patterns

### Code Style
- Full Python 3.10+ type hints throughout
- f-strings for all string formatting
- Google-style docstrings
- Line length: 100 preferred, 120 max
- Imports: stdlib -> third-party -> local

### Logging
```python
from voxgrep.utils.helpers import setup_logger
logger = setup_logger(__name__)
```

### Error Handling
Custom exceptions inherit from `VoxGrepError` in `utils/exceptions.py`

### Testing
```bash
poetry run pytest tests/test_search.py -v  # Specific file
poetry run pytest --cov=voxgrep            # With coverage
```

## Common Development Tasks

### Adding a New Search Type
1. Implement in `voxgrep/core/engine.py`
2. Add argument in `voxgrep/cli/main.py`
3. Route in `voxgrep/cli/commands.py`
4. Test in `tests/test_search.py`

### Adding a New API Endpoint
1. Define Pydantic model in `voxgrep/server/models.py`
2. Create router in `voxgrep/server/routers/`
3. Include in `voxgrep/server/app.py`

### Adding a New Transcription Backend
1. Create provider in `voxgrep/server/multi_model.py`
2. Update device detection in `voxgrep/utils/config.py`

## Performance Notes

- Batch exports in groups of 20 clips to prevent memory exhaustion
- Semantic model is lazy-loaded in background thread
- Hardware acceleration: h264_videotoolbox (Mac), h264_nvenc (NVIDIA)
- Cache transcripts and embeddings aggressively

## Troubleshooting

Run `voxgrep --doctor` to check:
- Python version compatibility
- Core dependencies (moviepy, whisper, torch)
- Optional features (spacy, pyannote, openai)
- System tools (ffmpeg, mpv)
