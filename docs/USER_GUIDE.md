# VoxGrep User Guide

This guide covers how to use VoxGrep's features, with a focus on the Desktop Application and local file management.

## 📁 Adding Media

VoxGrep can process both online videos (via URL) and local files from your system.

### Adding Online Videos (YouTube)

You can paste a URL from **YouTube** or other supported video sites directly into the input field. VoxGrep uses **yt-dlp** to automatically download the video and any available subtitles before analysis.

### Adding Local Files

There are three ways to add local video files:

1.  **File Picker**: Click the **"Browse"** button next to the URL input to open a native file dialog.
2.  **Drag & Drop**: Drag a video file from your file manager and drop it anywhere on the input section. An orange overlay will appear to confirm the drop zone.
3.  **Manual Path**: Paste the absolute path to your file (e.g., `/Users/me/video.mp4` or `C:\Videos\clip.mov`) directly into the input field.

> **Note**: Native features like the "Browse" button and Drag & Drop **only work in the standalone app**, not when running the frontend in a regular web browser.

### Supported File Types

VoxGrep supports most common video formats: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.m4v`.

---

## 💻 CLI Usage (Interactive Mode)

In addition to the desktop app, VoxGrep provides a powerful interactive CLI. Run it with `voxgrep` (without arguments) to enter the wizard.

### New Features in CLI

- **Download from URL**: You can now download videos directly from YouTube, Vimeo, and other sites within the CLI. Select "Download from URL" in the input selection menu.
- **Fast Preview**: Use the new **MPV Preview** option to watch search results immediately without waiting for a full export (requires [mpv](https://mpv.io) installed).
- **Session Summary**: After exporting, see a detailed statistical summary showing time saved, efficiency percentage, and total footage processed.
- **Advanced File Management**: You can now rename, remove, preview, or reveal selected files directly from the CLI menu before processing.

---

## 🔍 Searching the Library

Once your videos are analyzed, you can search across your entire library using several methods:

- **Sentence Search**: Matches full lines of dialogue.
- **Fragment Search**: Matches exact words or phrases with millisecond precision.
- **Semantic Search**: Search by _meaning_ or _concept_ (e.g., searching for "greeting" might find "hello" or "hi").
- **Mash**: Generates a random compilation of words.

---

## ✂️ Creating Supercuts

After searching, you can export your results as a "supercut":

1.  Select the clips you want to include (or include all).
2.  Choose a **Transition** (None, Crossfade, Fade-to-Black, Dissolve).
3.  Choose a **Subtitle Style** (Netflix, YouTube, Cinema, etc.) if you want to burn subtitles into the video.
4.  Click **Export Supercut**.

The background server will process the video and notify you when it's ready.

---

## 🔧 Troubleshooting

### App shows a blank screen or connection error

Ensure the backend server is running: `python -m voxgrep.server.app`. Visit `http://127.0.0.1:8000/health` to verify it's active.

### Browse button or Drag & Drop doesn't work

If you are accessing the app via `localhost:1420` in a web browser, native features are disabled. Use the native app window launched via `npm run tauri dev`.

### Transcription is slow

- Check if **GPU Acceleration** is enabled in the app settings.
- On Mac, ensure the **MLX** backend is being used for optimal performance.
- For large libraries, the first semantic search may be slow while the vector model loads into RAM.

### Cancelling Transcription

If you notice the transcription quality is poor or you want to stop the process:

- Press **Ctrl+C** (or **Cmd+C** on Mac) at any time during transcription.
- VoxGrep will gracefully stop and **save all partial results** processed up to that point.
- You can then restart with different settings (e.g., different model, language, or device).
- The partial transcript will be saved as a `.json` file next to your video.

### Changing Transcription Models

VoxGrep automatically tracks which model was used to create each transcript. If you try to transcribe a video that already has a transcript but with different settings (e.g., switching from `tiny` to `large-v3`, or from `cpu` to `cuda`), you'll be prompted:

```
⚠ Found existing transcript created with different settings:
  Existing: tiny on cpu
  Requested: large-v3 on cuda

? What would you like to do?
  ❯ Use existing transcript (faster)
    Regenerate with new settings (recommended for quality)
    Cancel
```

**Recommendations:**
- Choose **"Use existing"** if you just want to search quickly and don't care about perfect accuracy
- Choose **"Regenerate"** if you need better quality (e.g., upgrading from `tiny` to `large-v3`)
- Choose **"Cancel"** if you want to check your settings first

VoxGrep stores model metadata in `.transcript_meta.json` files alongside your transcripts.

### Missing transcription models

If you see errors about missing models, ensure you have an active internet connection for the first run, as VoxGrep will download the necessary AI models automatically.

### Port 8000 is already in use

If the backend fails to start, another process might be using port 8000. Use `lsof -i :8000` to find and kill the conflicting process.
