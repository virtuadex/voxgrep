# Videogrep

Videogrep is a command-line tool that searches through dialog in video or audio files and automatically generates "supercuts" based on what it finds. It supports `.srt`, `.vtt`, and `.json` (Whisper) transcriptions.

---

## 📺 Examples
- [The Meta Experience](https://www.youtube.com/watch?v=nGHbOckpifw)
- [All instances of "time" in "In Time"](https://www.youtube.com/watch?v=PQMzOUeprlk)
- [One to two second silences in "Total Recall"](https://www.youtube.com/watch?v=qEtEbXVbYJQ)
- [Press secretary telling us what he can tell us](https://www.youtube.com/watch?v=D7pymdCU5NQ)

---

## 🚀 Quick Start

### Installation
Ensure you have **Python 3.10+** and **FFmpeg** installed.

```bash
# Using Poetry (Recommended)
poetry install
poetry install --extras "full"  # For NLP features

# Using pip
pip install videogrep
```

### Basic Usage
Search for a phrase and generate a supercut:
```bash
videogrep --input video.mp4 --search "search phrase"
```

### ⚠️ Important: Subtitle Mapping
Videogrep requires a matching subtitle track for every media file. **The video/audio file and subtitle file must have the exact same name**, excluding the extension:
- ✅ `movie.mp4` + `movie.srt`
- ❌ `movie.mp4` + `movie_subtitles.srt`

---

## 🎙️ Transcription
If you don't have subtitles, Videogrep can generate them using OpenAI's Whisper.

**Built-in Transcription:**
```bash
videogrep -i video.mp4 --transcribe --model medium
```

**Using the Automation Script:**
```bash
python auto_videogrep.py video.mp4 "search query" --model large-v3
```

---

## 🛠️ CLI Options Reference

### Search & Logic
| Option | Short | Description |
| :--- | :--- | :--- |
| `--search` | `-s` | Regex search term (can be used multiple times). |
| `--search-type` | `-st` | `sentence` (default), `fragment` (exact phrase), or `mash` (random). |
| `--max-clips` | `-m` | Maximum number of clips to include. |
| `--randomize` | `-r` | Randomize clip order. |

### Transcription (Whisper)
| Option | Short | Description |
| :--- | :--- | :--- |
| `--transcribe` | `-tr` | Transcribe input using OpenAI Whisper. |
| `--model` | `-mo` | Whisper model (`base`, `medium`, `large-v3`, etc.). |
| `--language` | `-l` | Language code (e.g., `en`, `pt`, `fr`). |
| `--device` | `-dev` | Device to use (`cpu` or `cuda`). |
| `--compute-type`| `-ct` | Precision (`int8`, `float16`, `int8_float16`). |

### Input & Output
| Option | Short | Description |
| :--- | :--- | :--- |
| `--input` | `-i` | Input file(s). Supports glob patterns. |
| `--output` | `-o` | Output filename (default: `supercut.mp4`). |
| `--export-clips`| `-ec` | Save clips as individual files instead of a single supercut. |
| `--export-vtt`  | `-ev` | Export the supercut transcript as a `.vtt` file. |

### Processing & Preview
| Option | Short | Description |
| :--- | :--- | :--- |
| `--padding` | `-p` | Seconds to add to start/end of clips. |
| `--resyncsubs` | `-rs` | Shift subtitles forward/backward in seconds. |
| `--demo` | `-d` | Show results without rendering the video. |
| `--preview` | `-pr` | Preview the supercut in `mpv`. |
| `--ngrams` | `-n` | List common words and phrases. |

---

## 🐍 Use as a Python Module

```python
from videogrep import videogrep

videogrep(
    files='video.mp4', 
    query='search term', 
    search_type='sentence', 
    output='output.mp4'
)
```

---

## 🧪 Advanced Examples
Check the `examples/` folder for scripts covering:
- [Silence extraction](examples/only_silence.py)
- [YouTube-based supercuts](examples/auto_youtube.py)
- [POS Tagging & NLP](examples/parts_of_speech.py)
- [Spacy Pattern Matching](examples/pattern_matcher.py)

---

## 🗺️ Roadmap
- [ ] **Semantic Search:** Search by concept using vector embeddings.
- [ ] **Speaker Diarization:** Filter results by specific speakers.
- [ ] **Embedded Subtitles:** Burn-in subtitles directly onto the supercut.
- [ ] **Web GUI:** FastAPI backend and React frontend.

---

## ✍️ Credits
Maintained by **virtuadex**, originally created by [Sam Lavigne](https://lav.io). Built with [MoviePy](https://zulko.github.io/moviepy/) and [OpenAI Whisper](https://github.com/openai/whisper). Special thanks to [Charlie Macquarie](https://charliemacquarie.com).