# VoxGrep Enhancement Summary

## Date: 2026-01-21

### Overview
Implemented three major UX enhancements to improve the VoxGrep interactive workflow based on user feedback.

---

## 1. Visual Highlighting in Search Results ✨

### What Changed
- Search terms are now **highlighted** in the results table with bold yellow text on blue background
- Works in both exact match and substring match modes
- Applies to demo mode results display

### Files Modified
- `voxgrep/core/logic.py` (lines 161-183)

### Benefits
- Instantly spot where your search term appears in long text segments
- No need to read entire sentences to find matches
- Especially useful when reviewing 25+ results

### Example
When searching for "demo", you'll see:
```
Content: "tínhamos a DEMO do Lemings, tantas horas"
         (DEMO appears highlighted in yellow on blue)
```

---

## 2. Smart Padding for "Mash" Mode 🎵

### What Changed
- Added `MASH_PADDING = 0.05` constant (50ms micro-padding)
- Automatically applies to word-level cuts in "mash" search type
- Different from fragment mode which uses 0.3s padding

### Files Modified
- `voxgrep/utils/config.py` (line 27)
- `voxgrep/core/logic.py` (lines 143-152)

### Benefits
- Word-by-word supercuts sound more natural
- Prevents choppy audio at word boundaries
- No manual padding adjustment needed

### Technical Details
- Fragment mode: 0.3s padding (unchanged)
- Mash mode: 0.05s padding (new)
- Sentence mode: 0s padding (unchanged)

---

## 3. "Ignore this Word" Shortcut 🚫

### What Changed
- Added **"[🚫] Add Word to Ignored List"** option in n-gram selection menu
- Autocomplete interface shows all words from current n-grams
- Automatically saves to user preferences
- Instantly recalculates and refreshes n-gram list

### Files Modified
- `voxgrep/cli/ngrams.py`:
  - `select_ngrams_single_mode()` - Added ignore option
  - `select_ngrams_multi_mode()` - Updated return signature
  - `ngram_selection_phase()` - Added ignore word handling
  - `interactive_ngrams_workflow()` - Added refresh logic

### Benefits
- No need to navigate to separate settings menu
- Immediate visual feedback (list refreshes)
- Persistent across sessions (saved to prefs.json)
- Autocomplete makes it easy to select the exact word

### User Flow
1. Browse n-grams list
2. Select **"[🚫] Add Word to Ignored List"**
3. Type or select word from autocomplete
4. List automatically refreshes without that word
5. Continue selecting n-grams for your search

---

## 4. Exact Match Toggle (Previously Implemented) ✓

### What Changed
- Added **"Exact Match (Whole Words Only)?"** toggle in settings menu
- Respects `--word-regexp` CLI flag
- Prevents substring matching (e.g., "demo" won't match "demonstrações")

### Files Modified
- `voxgrep/cli/ngrams.py` (lines 194, 270-276)

### Benefits
- Search for specific words without partial matches
- Case-insensitive but boundary-aware
- Useful for distinguishing between related words

---

## Testing Recommendations

### Test Case 1: Visual Highlighting
```bash
voxgrep -i video.mp4 -s "demo" --demo
```
Expected: "demo" appears highlighted in yellow on blue in the results table

### Test Case 2: Mash Mode Padding
```bash
voxgrep -i video.mp4 -s "hello world" --search-type mash -o mash_test.mp4
```
Expected: 50ms padding applied automatically, smoother audio transitions

### Test Case 3: Ignore Word Workflow
1. Run: `voxgrep -i video.mp4 -n 2`
2. Select **"[🚫] Add Word to Ignored List"**
3. Type a common word (e.g., "the")
4. Verify list refreshes without that word
5. Check `~/.local/share/voxgrep/prefs.json` (Linux/Mac) or `%LOCALAPPDATA%\voxgrep\prefs.json` (Windows)

### Test Case 4: Exact Match
1. Run: `voxgrep -i video.mp4 -n 1`
2. Select "demo"
3. Choose **Settings** → Enable **Exact Match**
4. Preview results
5. Verify only whole word "demo" matches (not "demos", "demonstrações")

---

## Configuration Files

### New Constants
- `MASH_PADDING = 0.05` in `voxgrep/utils/config.py`

### Preferences Schema (prefs.json)
```json
{
  "ignored_words": ["a", "the", "demo", ...],
  "use_ignored_words": true,
  ...
}
```

---

## Future Enhancements (Not Implemented)

### Case-Sensitive Toggle
- Would allow distinguishing "Apple" (company) from "apple" (fruit)
- Deferred based on user preference

---

## Backward Compatibility

All changes are **fully backward compatible**:
- Existing CLI flags work unchanged
- Default behaviors preserved
- New features are opt-in
- Preferences file auto-migrates

---

## Performance Impact

- **Highlighting**: Negligible (only affects display, not search)
- **Mash Padding**: None (same logic, different constant)
- **Ignore Word**: Minimal (one-time n-gram recalculation)

---

## Documentation Updates Needed

- [ ] Update `docs/USER_GUIDE.md` with new features
- [ ] Add screenshots of highlighted results
- [ ] Document ignore word workflow
- [ ] Update CLI reference for exact match

---

## Summary

These enhancements significantly improve the user experience for interactive n-gram workflows:

1. **Visual Highlighting** - See matches instantly
2. **Smart Padding** - Better audio quality for mash mode
3. **Ignore Word Shortcut** - Faster filtering workflow
4. **Exact Match** - Precise word matching

All features work together seamlessly and respect user preferences.
