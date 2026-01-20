# VoxGrep API Reference

How to use VoxGrep as a Python library.

## Basic Usage

```python
from voxgrep import voxgrep

voxgrep(
    files='video.mp4',
    query='search term',
    search_type='sentence',
    output='output.mp4'
)
```

## Advanced Usage

For more granular control, you can interface directly with the core modules.

### Search Engine

```python
from voxgrep import search_engine

# Search for matches
results = search_engine.search(
    files=['video.mp4'],
    query='phrase',
    search_type='fragment'
)
```

### Exporter

```python
from voxgrep import exporter

# Concatenate clips
exporter.create_supercut(
    clips,
    output_filename='compilation.mp4',
    padding=0.1
)
```

## Refactored Exception Handling

VoxGrep now uses custom exceptions for better error management:

```python
from voxgrep.exceptions import NoResultsFoundError, TranscriptionError

try:
    voxgrep(files='video.mp4', query='missing phrase')
except NoResultsFoundError:
    print("No matches found for that query.")
except TranscriptionError as e:
    print(f"Transcription failed: {e}")
```
