# VoxGrep

**VoxGrep** is a powerful tool for searching through dialogue in video and audio files to automatically generate "supercuts" (compilations of clips). It's like `grep`, but for time-based media.

[![PyPI version](https://badge.fury.io/py/voxgrep.svg)](https://badge.fury.io/py/voxgrep)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📺 Overview

Search for phrases, patterns, or even semantic concepts across your video library and instantly export a compilation of every matching moment.

- **Regex Search:** Find exact phrases or complex linguistic patterns.
- **Semantic Search:** Search by concept using AI embeddings.
- **Auto-Transcription:** Local AI-powered transcription via OpenAI Whisper (optimized for MLX/GPU).
- **Dynamic Transitions:** Add crossfades and dissolves between clips.
- **Subtitle Burning:** Export videos with embedded subtitles in various styles.

---

## 🚀 Getting Started

To get started quickly, follow our [**Getting Started Guide**](docs/GETTING_STARTED.md).

```bash
# Install with full features
pip install "voxgrep[full]"

# Run the CLI
voxgrep --input movie.mp4 --search "hello world" --transcribe
```

---

## 📖 Documentation

- 🚀 [**Getting Started**](docs/GETTING_STARTED.md) - Installation and basic setup.
- 📚 [**User Guide**](docs/USER_GUIDE.md) - Deep dive into features and troubleshooting.
- 🏗️ [**Architecture**](docs/ARCHITECTURE.md) - How it works under the hood.
- 🛠️ [**CLI Reference**](docs/CLI_REFERENCE.md) - Detailed command-line options.
- 🐍 [**API Reference**](docs/API_REFERENCE.md) - Using VoxGrep as a Python library.

---

## 🖥️ Desktop Application

VoxGrep features a premium desktop interface built with **Tauri**, **React**, and **FastAPI**. See the [Desktop User Guide](docs/USER_GUIDE.md) for more info.

---

## ✍️ Credits

Maintained by **virtuadex**, originally created by [Sam Lavigne](https://lav.io). Built with [MoviePy](https://zulko.github.io/moviepy/) and [OpenAI Whisper](https://github.com/openai/whisper). Special thanks to [Charlie Macquarie](https://charliemacquarie.com).
