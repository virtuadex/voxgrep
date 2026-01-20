# Model Metadata Tracking Feature

## Overview
Implemented automatic tracking of transcription model settings and interactive prompts when attempting to reuse transcripts created with different models.

## Implementation Details

### Core Changes

1. **`voxgrep/core/transcriber.py`**
   - Added `on_existing_transcript` callback parameter to `transcribe()` function
   - Creates `.transcript_meta.json` file alongside each transcript with:
     - Model name
     - Device (cpu/cuda/mlx)
     - Language (if specified)
     - Compute type
   - Checks metadata before reusing cached transcripts
   - Calls callback when model/device differs from existing transcript
   - Falls back to logging warning in non-interactive mode

2. **`voxgrep/cli/commands.py`**
   - Added `ask_about_existing_transcript()` callback function
   - Displays clear comparison of existing vs requested settings
   - Provides 3 options:
     - Use existing transcript (faster)
     - Regenerate with new settings (recommended for quality)
     - Cancel
   - Default choice is "regenerate" for quality

### User Experience

**When model differs:**
```
⚠ Found existing transcript created with different settings:
  Existing: tiny on cpu
  Requested: large-v3 on cuda

? What would you like to do?
❯ Use existing transcript (faster)
  Regenerate with new settings (recommended for quality)
  Cancel
```

### Metadata File Format

Example `.transcript_meta.json`:
```json
{
  "model": "large-v3",
  "device": "cuda",
  "language": "pt",
  "compute_type": "float16"
}
```

### Benefits

1. **Quality Control**: Prevents accidentally using low-quality transcripts from smaller models
2. **Transparency**: Users always know what model created their transcript
3. **Flexibility**: Can choose to reuse for speed or regenerate for quality
4. **Backward Compatible**: Works with existing transcripts (no metadata = shows warning)

## Testing

Created comprehensive unit tests in `tests/test_metadata.py`:

- ✅ `test_transcribe_with_matching_metadata`: Reuses when settings match
- ✅ `test_transcribe_with_different_model_no_callback`: Logs warning in non-interactive mode
- ✅ `test_transcribe_with_different_model_callback_reuse`: User chooses to reuse
- ✅ `test_transcribe_with_different_model_callback_regenerate`: User chooses to regenerate

All tests pass successfully.

## Use Cases

### Scenario 1: Quick Test → Production
```bash
# Quick test with tiny model
voxgrep -i video.mp4 --transcribe --model tiny

# Later, want better quality
voxgrep -i video.mp4 --transcribe --model large-v3
# → Prompted to regenerate or reuse
```

### Scenario 2: CPU → GPU Migration
```bash
# Initial transcription on CPU
voxgrep -i video.mp4 --transcribe --device cpu

# Got a GPU, want to use it
voxgrep -i video.mp4 --transcribe --device cuda
# → Prompted about device change
```

### Scenario 3: Wrong Language Detection
```bash
# Auto-detected wrong language
voxgrep -i video.mp4 --transcribe

# Specify correct language
voxgrep -i video.mp4 --transcribe --language pt
# → Can choose to regenerate with language hint
```

## Technical Notes

- Metadata files are small (~100 bytes) and stored alongside transcripts
- The check happens before loading the model, saving time and memory
- MLX model names are normalized to full repository paths in metadata
- Backward compatible: missing metadata files trigger warning but allow reuse
- The feature works in both CLI and programmatic usage
