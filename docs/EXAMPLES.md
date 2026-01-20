# VoxGrep Examples & Advanced Workflows

Explore the scripts in the `examples/` directory to see how VoxGrep can be automated and extended.

## Prerequisites

Ensure you have the full installation:

```bash
poetry install --extras "full"
# or
pip install voxgrep[full]
```

## Available Example Scripts

### 🔍 Search & Extraction

- **`auto_supercut.py`**: Identifies the most frequent non-stop words in a video and builds a compilation of them.
- **`auto_youtube.py`**: Fetches top search results from YouTube, downloads them, transcribes them, and generates a supercut.
- **`only_silence.py`**: Extracts all silent gaps between words/sentences.

### ✂️ Video Editing

- **`remove_silence.py`**: Trims out all silences longer than a specific threshold (e.g., 0.5s) to create a tightened version of a video.

### 🧠 NLP & Linguistic Patterns

- **`parts_of_speech.py`**: Create a supercut containing all instances of a specific part of speech (e.g., all nouns, all verbs).
- **`pattern_matcher.py`**: Uses Spacy's rule-based matching for complex queries like `[Adjective] + [Noun]`.

## Usage Instructions

Run these scripts from the project root:

```bash
python examples/auto_youtube.py "climate change"
```

Refer to the source of each script for specific argument details.
