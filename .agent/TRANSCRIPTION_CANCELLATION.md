# Transcription Cancellation Feature

## Overview
Implemented graceful cancellation of transcription processes, allowing users to stop transcription at any time by pressing **Ctrl+C**.

## Implementation Details

### Core Changes

1. **`voxgrep/core/transcriber.py`**
   - Wrapped the transcription loop in a `try-except KeyboardInterrupt` block
   - When interrupted, the function saves all segments processed up to that point
   - Partial results are saved to the `.json` transcript file
   - Works with both callback-based (CLI) and tqdm-based (direct) progress tracking

2. **`voxgrep/cli/commands.py`**
   - Added `KeyboardInterrupt` handling in `run_transcription_whisper()`
   - Displays user-friendly message: "Press Ctrl+C to cancel transcription at any time"
   - Shows confirmation message when cancelled: "⚠ Transcription cancelled by user. Partial results have been saved."
   - Properly cleans up progress bars and returns gracefully

### User Experience

**Before cancellation:**
```
Press Ctrl+C to cancel transcription at any time

⠴ Transcribing video.mp4 (1/1)... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   45%
[dim]This is the detected subtitle text...[/dim]
```

**After pressing Ctrl+C:**
```
⚠ Transcription cancelled by user. Partial results have been saved.
```

### Benefits

1. **No wasted work**: All processed segments are saved, even if transcription is interrupted
2. **Quick iteration**: Users can test different models/settings without waiting for full completion
3. **Quality control**: Stop immediately if transcription quality is poor
4. **Graceful cleanup**: Progress bars close properly, no hanging processes

## Testing

Created comprehensive unit tests in `tests/test_cancellation.py`:

- ✅ `test_transcribe_whisper_keyboard_interrupt`: Verifies partial results are saved
- ✅ `test_transcribe_whisper_keyboard_interrupt_with_callback`: Tests with progress callbacks

Both tests pass successfully.

## Documentation

Updated `docs/USER_GUIDE.md` with a new "Cancelling Transcription" section explaining:
- How to cancel (Ctrl+C / Cmd+C)
- What happens to partial results
- How to restart with different settings

## Example Usage

```bash
# Start transcription
python -m voxgrep.cli.main -i video.mp4 --transcribe --model tiny

# Press Ctrl+C after seeing poor quality
# Partial transcript saved to video.json

# Restart with better model
python -m voxgrep.cli.main -i video.mp4 --transcribe --model medium --language pt
```

## Technical Notes

- The implementation uses Python's standard `KeyboardInterrupt` exception
- Partial results are valid JSON and can be used for searching
- The feature works across all transcription backends (CPU, CUDA, MLX)
- No changes required to the transcription models themselves
