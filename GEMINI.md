# Gemini Project Context: VoxGrep

This document provides a high-level overview for Gemini to understand and work with the VoxGrep project.

## 📖 Primary Documentation

For detailed information, refer to the following guides:

- 🚀 [**Getting Started**](docs/GETTING_STARTED.md) - Installation and running the app.
- 🏗️ [**Architecture**](docs/ARCHITECTURE.md) - System design, API endpoints, and database schema.
- 📚 [**User Guide**](docs/USER_GUIDE.md) - Feature usage, local file support, and troubleshooting.
- 🛠️ [**CLI Reference**](docs/CLI_REFERENCE.md) - Detailed command-line options.

## 📺 Project Overview

**VoxGrep** is a "grep for video" tool. It searches through dialogue in media files to generate automatic supercuts.

### Core Stack

- **Backend**: Python 3.10+, FastAPI, SQLModel (SQLite), MoviePy 2.x.
- **AI**: Whisper (MLX/faster-whisper), Sentence-Transformers (Vector Search), Pyannote (Diarization).
- **Frontend**: Tauri, React, Vite, TypeScript.

### Key Principles

- **Local-First**: All processing remains on the user's machine.
- **Service-Oriented**: The core logic is exposed via a persistent FastAPI server.
- **Background-Driven**: High-latency tasks like transcription and export run asynchronously.

## 🛠️ Essential Commands

- **Start Backend**: `python -m voxgrep.server.app`
- **Start Desktop (Dev)**: `cd desktop && npm run tauri dev`
- **Run Tests**: `pytest`
- **Full Install**: `pip install "voxgrep[full]"`
