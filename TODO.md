# VoxGrep TODO List

This list tracks the planned improvements and future features for the VoxGrep project.

## 🚀 Priority: Enhanced CLI Experience

- [x] **Rich Integration**: Implement `rich` for stylistic banners, tables, and logging.
- [x] **Interactive Mode**: Add an interactive wizard using `questionary` for guided task configuration.
- [x] **Navigable File Selection**: Use checkbox menus for selecting local media files.
- [x] **Real-time Transcription Progress**: Wire up proper progress callbacks for Whisper (CPU/CUDA/MLX).
- [x] **In-Terminal Subtitle Preview**: Show a scrolling "Ticker" or panel of detected text during transcription.

## 🧠 Smart Features & AI

- [x] **Smart Search Suggestions**: Show top N-grams after transcription and allow one-click supercut generation.
  - [x] Interactive N-gram selection.
  - [x] Stop words filtering.
- [ ] **Topic Clustering**: Use embeddings to suggest cuts based on themes/concepts.
- [ ] **Semantic Search Robustness**: Fix edge-case crashes in semantic search (e.g., empty queries).

## 🎬 Pro Export & Workflow

- [ ] **NLE XML Export**: Generate `.fcpxml` or `.edl` files for professional editing workflows (Final Cut, Premiere, Resolve).
- [ ] **Deep YouTube/URL Integration**:
  - [x] Accept URLs in interactive mode.
  - [x] Automatic download using `yt-dlp`.
  - [x] background stream processing.
- [ ] **Burn-in Translation**: Support for burning translated subtitles into the output video.

## 🛠️ UX & Reliability

- [x] **Configuration Persistence**: Save user preferences (Device, Model selection) to avoid repetitive choices.
- [ ] **Session Summary**: Show post-task statistics (duration saved, clips cut, efficiency).
- [x] **Batch Error Recovery**: Continue processing remaining files if one fails in a batch.
- [x] **Dry Run Mode**: Preview clip timestamps and final duration without rendering (implemented as Demo Mode).
- [x] **MPV Preview Robustness**: Better error handling and dependency checks for MPV.

## 📦 Maintenance

- [x] Standardize Python environment across all installation paths.
- [x] Improve automated test coverage for CLI interactive modes.
- [x] **Server Refactoring**: Split monolithic app.py into modular routers.
