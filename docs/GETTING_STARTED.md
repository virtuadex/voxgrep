# Getting Started with VoxGrep

This guide will help you get VoxGrep up and running for both command-line use and as a desktop application.

## Prerequisites

- **Python 3.10+**: Ensure you have Python installed.
- **FFmpeg**: Required for media processing.
- **Node.js & npm**: Required for the desktop application.
- **Poetry** (Recommended): For managing Python dependencies.

## 📥 Installation

### Basic Installation (CLI only)

```bash
pip install voxgrep
```

### Full Installation (Recommended for Desktop/AI features)

```bash
# Using Poetry
git clone https://github.com/virtuadex/voxgrep.git
cd voxgrep
poetry install --extras "full"

# Using pip
pip install "voxgrep[full]"
```

## 🚀 Running VoxGrep

VoxGrep consists of three components that can be used together for the full experience:

### 1. The Backend Server (FastAPI)

The backend handles all heavy lifting: transcription, semantic search, and video export.

```bash
# Start the server
python -m voxgrep.server.app
```

Wait until you see `Uvicorn running on http://127.0.0.1:8000`.

### 2. The Desktop App (Tauri/React)

The premium desktop interface for managing your library and creating supercuts.

```bash
cd desktop
npm install
npm run tauri dev
```

### 3. The CLI Tool

For automation and terminal-based search.

```bash
# Search for a phrase
voxgrep -i "video.mp4" -s "hello world"

# Create a supercut of "yeah"
voxgrep -i "video.mp4" -s "yeah" -o supercut.mp4
```

## 🛠️ Quick Commands

| Component           | Command                             |
| :------------------ | :---------------------------------- |
| **Backend**         | `python -m voxgrep.server.app`      |
| **Desktop (Dev)**   | `cd desktop && npm run tauri dev`   |
| **Desktop (Build)** | `cd desktop && npm run tauri build` |
| **Tests**           | `pytest`                            |

## 📖 Next Steps

- 📚 [**User Guide**](USER_GUIDE.md) - Learn how to use the app, add local files, and troubleshoot.
- 🏗️ [**Architecture**](ARCHITECTURE.md) - Deep dive into how VoxGrep works.
- 🛠️ [**CLI Reference**](CLI_REFERENCE.md) - All flags and search options.
- 🐍 [**API Reference**](API_REFERENCE.md) - Use VoxGrep as a Python library.
