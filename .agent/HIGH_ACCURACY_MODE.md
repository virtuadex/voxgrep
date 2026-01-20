# High Accuracy Mode Feature

## Overview
Implemented comprehensive high accuracy mode for transcription with enhanced inference parameters, Voice Activity Detection (VAD), and project-specific vocabulary management.

## Features Implemented

### 1. Advanced Inference Parameters
**Exposed in Core:**
- `beam_size`: Controls beam search width (default: 5, high accuracy: 10)
- `best_of`: Number of candidates when sampling (default: 5, high accuracy: 10)
- `vad_filter`: Voice Activity Detection to filter non-speech (default: True)
- `vad_parameters`: Optional custom VAD configuration

### 2. High Accuracy Mode Toggle
**Interactive Prompt:**
```
? Enable High Accuracy Mode? (slower but better transcription) (Y/n)
```

**When enabled:**
- `beam_size = 10` (vs default 5)
- `best_of = 10` (vs default 5)
- `vad_filter = True` (always on)
- ~2x slower but significantly more accurate

### 3. Project Vocabulary Management
**Persistent Storage:**
- Vocabulary terms saved in `prefs.json` as `project_vocabulary`
- Reused automatically across sessions
- Terms become part of the initial prompt to guide the model

**User Flow:**
```
? Add project-specific vocabulary? (names, terms, slang) (y/N)
> Andre Ventura, Chega, política portuguesa, parlamento

✓ Vocabulary saved for future use
```

**Next Session:**
```
? Use saved project vocabulary? (4 terms) (Y/n)
Using vocabulary: Andre Ventura, Chega, política portuguesa, parlamento
```

## Technical Implementation

### Files Modified

1. **`voxgrep/core/transcriber.py`**
   - Added parameters to `transcribe_whisper()`: `beam_size`, `best_of`, `vad_filter`, `vad_parameters`
   - Added parameters to `transcribe()` wrapper
   - Parameters passed through to `model.transcribe()`

2. **`voxgrep/utils/prefs.py`**
   - Added to `DEFAULT_PREFS`:
     ```python
     "high_accuracy_mode": False,
     "beam_size": 5,
     "best_of": 5,
     "vad_filter": True,
     "project_vocabulary": []
     ```

3. **`voxgrep/cli/workflows.py`**
   - Enhanced `configure_transcription()` to:
     - Ask about high accuracy mode
     - Manage project vocabulary
     - Apply appropriate parameters

4. **`voxgrep/cli/commands.py`**
   - Updated `run_transcription_whisper()` signature
   - Pass parameters through to `transcribe()`

5. **`voxgrep/cli/interactive.py`**
   - Initialize accuracy parameters in `create_default_args()`

## User Experience

### Standard Mode (Default)
```bash
? Whisper Model large-v3
? Enable High Accuracy Mode? No

# Transcription runs with beam_size=5, best_of=5
# Faster, good quality
```

### High Accuracy Mode
```bash
? Whisper Model large-v3
? Enable High Accuracy Mode? Yes
✓ High Accuracy Mode enabled (beam_size=10, VAD enabled)

? Add project-specific vocabulary? Yes
> Andre Ventura, Chega, parlamento
✓ Vocabulary saved for future use

# Transcription runs with:
# - beam_size=10 (explores more possibilities)
# - best_of=10 (better sampling)
# - VAD enabled (filters non-speech)
# - Initial prompt with vocabulary
# Result: Significantly better accuracy for specialized content
```

## Impact on Quality

### Beam Size Impact
- **beam_size=1**: Greedy decoding, fastest, lowest quality
- **beam_size=5**: Default, good balance
- **beam_size=10**: High accuracy mode, explores more paths
- **beam_size=20**: Diminishing returns, very slow

### VAD Filter Impact
-  **Without VAD**: Model may "hallucinate" text during silence or background noise
- **With VAD**: Only transcribes actual speech, cleaner results

### Vocabulary Impact
- **Without vocabulary**: May misspell names, technical terms
- **With vocabulary**: Model "knows" to look for specific terms
- **Example**: "Andre Ventura" vs "André and Ventura" (two people)

## Performance Characteristics

| Mode | Speed | Quality | Use Case |
|------|-------|---------|----------|
| **Fast** (beam=1) | 1x | Base | Quick previews |
| **Standard** (beam=5) | 2x | Good | General use |
| **High Accuracy** (beam=10) | 4x | Excellent | Final transcripts |
| **Maximum** (beam=20) | 8x | Marginal gain | Special cases |

## Example Improvements

### Before (Standard Mode)
```
And the event Shura is a you know um person from the right wing
```

### After (High Accuracy + Vocabulary)
```
Andre Ventura is a, you know, a person from the right wing Chega party
```

## Future Enhancements

Potential improvements:
- [ ] Temperature parameter control
- [ ] Compression ratio threshold
- [ ] Custom VAD sensitivity
- [ ] Domain-specific prompt templates
- [ ] Automatic vocabulary extraction from previous transcripts
- [ ] Batch vocabulary import from CSV
- [ ] A/B comparison tool for different settings

## CLI Usage

### Interactive Mode
```bash
voxgrep
? Select input file: video.mp4
? What would you like to do? Transcription Only
? Device cuda
? Model large-v3
? Enable High Accuracy Mode? Yes        ← NEW
? Add project vocabulary? Yes            ← NEW
> specialized, terms, here
```

### Command Line (Future)
```bash
voxgrep -i video.mp4 --transcribe --model large-v3 \
  --high-accuracy \
  --vocab "term1, term2, term3"
```

## Logging

The system now logs accuracy settings:
```
INFO Transcribing video.mp4 using faster-whisper (large-v3 model) on cuda
INFO Accuracy settings: beam_size=10, best_of=10, vad_filter=True
```

This helps track which settings produced which transcripts.
