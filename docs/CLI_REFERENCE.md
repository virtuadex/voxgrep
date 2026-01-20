# VoxGrep CLI Reference

Detailed documentation for the `voxgrep` command-line interface.

## Search & Logic

| Option          | Short | Description                                                          |
| :-------------- | :---- | :------------------------------------------------------------------- |
| `--search`      | `-s`  | Regex search term (can be used multiple times).                      |
| `--search-type` | `-st` | `sentence` (default), `fragment` (exact phrase), or `mash` (random). |
| `--max-clips`   | `-m`  | Maximum number of clips to include.                                  |
| `--randomize`   | `-r`  | Randomize clip order.                                                |

## Transcription (Whisper)

| Option           | Short  | Description                                         |
| :--------------- | :----- | :-------------------------------------------------- |
| `--transcribe`   | `-tr`  | Transcribe input using OpenAI Whisper.              |
| `--model`        | `-mo`  | Whisper model (`base`, `medium`, `large-v3`, etc.). |
| `--language`     | `-l`   | Language code (e.g., `en`, `pt`, `fr`).             |
| `--device`       | `-dev` | Device to use (`cpu` or `cuda`, or `mps` for Mac).  |
| `--compute-type` | `-ct`  | Precision (`int8`, `float16`, `int8_float16`).      |

## Input & Output

| Option           | Short | Description                                                  |
| :--------------- | :---- | :----------------------------------------------------------- |
| `--input`        | `-i`  | Input file(s). Supports glob patterns.                       |
| `--output`       | `-o`  | Output filename (default: `supercut.mp4`).                   |
| `--export-clips` | `-ec` | Save clips as individual files instead of a single supercut. |
| `--export-vtt`   | `-ev` | Export the supercut transcript as a `.vtt` file.             |

## Processing & Preview

| Option         | Short | Description                                  |
| :------------- | :---- | :------------------------------------------- |
| `--padding`    | `-p`  | Seconds to add to start/end of clips.        |
| `--resyncsubs` | `-rs` | Shift subtitles forward/backward in seconds. |
| `--demo`       | `-d`  | Show results without rendering the video.    |
| `--preview`    | `-pr` | Preview the supercut in `mpv`.               |
| `--ngrams`     | `-n`  | List common words and phrases.               |

## Advanced Automation

VoxGrep includes an automation script `auto_voxgrep.py` for a recursive "transcribe then search" workflow.

```bash
python auto_voxgrep.py path/to/media "search query" --model large-v3
```
