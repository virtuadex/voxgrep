# Getting Started with VoxGrep

This guide will help you get VoxGrep up and running for both command-line use and as a desktop application.

## Prerequisites

### All Platforms
- **FFmpeg**: Required for media processing
- **mpv**: Recommended (optional) for the `--preview` feature
- **Node.js & npm**: Required for the desktop application (optional)
- **Poetry**: Recommended for development installation

### Platform-Specific Requirements

#### Windows
- **Python 3.10, 3.11, or 3.12** (⚠️ **NOT 3.13** - many AI libraries don't have pre-built wheels yet)
- Check your Python version: `python --version` or `py --version`
- If you have Python 3.13, install 3.10-3.12 alongside it

#### macOS
- **Python 3.10+**
- For Apple Silicon Macs: MLX-Whisper support available for faster transcription

#### Linux
- **Python 3.10+**
- Build tools: `sudo apt install build-essential` (Debian/Ubuntu)

## �️ Installing External Tools

VoxGrep depends on two powerful system tools that must be installed separately from Python:

### Windows
The easiest way is using **Winget** (built-in) or **Chocolatey** (requires an **Administrator terminal**):
```powershell
# Using Winget
winget install mpv.mpv

# Using Chocolatey
choco install ffmpeg mpv -y
```

**If Winget fails**, download manually:
1. Download the latest **x86_64-v3** build from the [shinchiro/mpv-winbuild-cmake releases](https://github.com/shinchiro/mpv-winbuild-cmake/releases) (recommended for Windows).
2. Extract the file.
3. **Quickest Fix**: Just place `mpv.exe` and `ffmpeg.exe` directly inside your `voxgrep` repository folder. VoxGrep will find them there automatically.
4. **Permanent Fix**: Extract to `C:\mpv` and add that folder to your System PATH.

### macOS
Use **Homebrew**:
```bash
brew install ffmpeg mpv
```

### Linux
Use your package manager:
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install ffmpeg mpv

# Fedora
sudo dnf install ffmpeg mpv
```

## �📥 Installation

### Windows Installation

#### 🚀 Automated Installation (Recommended)

The easiest way to install VoxGrep on Windows:

```powershell
# 1. Clone the repository
git clone https://github.com/virtuadex/voxgrep.git
cd voxgrep

# 2. Run the automated installer
.\installvoxgrep.ps1
```

The installer will:
- ✅ Check your Python version (requires 3.10-3.12)
- ✅ Install Poetry automatically
- ✅ Download FFmpeg and mpv binaries
- ✅ Install all Python dependencies
- ✅ Verify the installation with `--doctor`

**That's it!** The entire process takes 5-10 minutes.

#### Manual Installation (Advanced)

If you prefer manual control:

```powershell
# 1. Clone the repository
git clone https://github.com/virtuadex/voxgrep.git
cd voxgrep

# 2. Install Poetry (if not already installed)
pip install poetry

# 3. Configure Poetry to use Python 3.10-3.12 (if you have multiple versions)
poetry env use 3.10  # or 3.11, 3.12

# 4. Install dependencies (excluding Mac-only MLX)
poetry install --extras "nlp diarization openai"

# 5. Download system tools manually (see "Installing External Tools" section)

# 6. Verify installation
poetry run voxgrep --doctor
```

**Note:** On Windows, always prefix commands with `poetry run`:
```powershell
poetry run voxgrep -i video.mp4 -s "search term"
poetry run python -m voxgrep.server.app
```

### macOS Installation

```bash
# 1. Clone the repository
git clone https://github.com/virtuadex/voxgrep.git
cd voxgrep

# 2. Install Poetry (if not already installed)
pip install poetry

# 3. Install all dependencies
# For Apple Silicon (M1/M2/M3):
poetry install --extras "full"

# For Intel Macs:
poetry install --extras "nlp diarization openai"

# 4. Verify installation
poetry run voxgrep --help
```

### Linux Installation

```bash
# 1. Install build dependencies
sudo apt install build-essential python3-dev  # Debian/Ubuntu
# or
sudo yum install gcc python3-devel  # RHEL/CentOS

# 2. Clone the repository
git clone https://github.com/virtuadex/voxgrep.git
cd voxgrep

# 3. Install Poetry
pip install poetry

# 4. Install dependencies
poetry install --extras "nlp diarization openai"

# 5. Verify installation
poetry run voxgrep --help
```

### Quick Install (pip)

If you just want to try VoxGrep without development features:

```bash
# Basic installation
pip install voxgrep

# With AI features (may require compilation on some platforms)
pip install "voxgrep[nlp,diarization,openai]"
```

## 🚀 Running VoxGrep

VoxGrep consists of three components that can be used together for the full experience:

### 1. The Backend Server (FastAPI)

The backend handles all heavy lifting: transcription, semantic search, and video export.

```bash
# If installed via Poetry (development)
poetry run python -m voxgrep.server.app

# If installed via pip
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
# If installed via Poetry (development)
poetry run voxgrep -i "video.mp4" -s "hello world"
poetry run voxgrep -i "video.mp4" -s "yeah" -o supercut.mp4

# If installed via pip
voxgrep -i "video.mp4" -s "hello world"
voxgrep -i "video.mp4" -s "yeah" -o supercut.mp4
```

## 🛠️ Quick Commands

### Poetry Installation (Development)

| Component           | Command                                      |
| :------------------ | :------------------------------------------- |
| **Backend**         | `poetry run python -m voxgrep.server.app`    |
| **CLI**             | `poetry run voxgrep -i video.mp4 -s "query"` |
| **Desktop (Dev)**   | `cd desktop && npm run tauri dev`            |
| **Desktop (Build)** | `cd desktop && npm run tauri build`          |
| **Tests**           | `poetry run pytest`                          |

### Pip Installation

| Component           | Command                                  |
| :------------------ | :--------------------------------------- |
| **Backend**         | `python -m voxgrep.server.app`           |
| **CLI**             | `voxgrep -i video.mp4 -s "query"`        |
| **Desktop (Dev)**   | `cd desktop && npm run tauri dev`        |
| **Desktop (Build)** | `cd desktop && npm run tauri build`      |
| **Tests**           | `pytest`                                 |

## 📖 Next Steps

- 📚 [**User Guide**](USER_GUIDE.md) - Learn how to use the app, add local files, and troubleshoot.
- 🏗️ [**Architecture**](ARCHITECTURE.md) - Deep dive into how VoxGrep works.
- 🛠️ [**CLI Reference**](CLI_REFERENCE.md) - All flags and search options.
- 🐍 [**API Reference**](API_REFERENCE.md) - Use VoxGrep as a Python library.
