# CLI Refactoring - Code Migration Guide

## Quick Reference: Where Did My Code Go?

This guide helps you find where specific functionality moved during the refactoring.

## Function Migration Map

### From `main.py` → To New Modules

| Old Function (line range) | New Location | Notes |
|---------------------------|--------------|-------|
| `print_banner()` (46-59) | `ui.py` | Unchanged |
| `interactive_mode()` (62-417) | `interactive.py` | Split into multiple functions |
| File selection logic (75-128) | `workflows.select_input_files()` | Extracted |
| Settings menu (188-222) | `workflows.settings_menu()` | Extracted |
| Transcription config (250-262) | `workflows.configure_transcription()` | Extracted |
| Search workflow (268-403) | `interactive.handle_search_workflow()` | Refactored |
| Post-export menu (348-391) | `workflows.post_export_menu()` | Extracted |
| `run_voxgrep_with_progress()` (421-493) | `commands.run_voxgrep_search()` | Enhanced |
| `execute_args()` (495-893) | `commands.execute_args()` | Modularized |
| Sphinx transcription (503-518) | `commands.run_transcription_sphinx()` | Extracted |
| Whisper transcription (520-561) | `commands.run_transcription_whisper()` | Extracted |
| N-grams calculation (568-606) | `commands.calculate_ngrams()` | Extracted |
| N-grams selection (607-881) | `ngrams.interactive_ngrams_workflow()` | Completely refactored |
| Single select mode (621-660) | `ngrams.select_ngrams_single_mode()` | Extracted |
| Multi select mode (662-733) | `ngrams.select_ngrams_multi_mode()` | Extracted |
| N-gram action phase (782-878) | `ngrams.ngram_action_phase()` | Extracted |
| `main()` (896-1076) | `main.py` | Simplified |
| Argument parser (907-1063) | `main.create_argument_parser()` | Extracted |
| Platform file opening | `ui.open_file()` | Centralized |
| Platform folder opening | `ui.open_folder()` | Centralized |

## Module Purposes

### `ui.py` - UI Components
**What lives here**: All Rich-based display and platform utilities

```python
# Functions
- print_banner()           # Display VoxGrep banner
- print_ngrams_table()     # Display n-gram results table
- print_success_panel()    # Show success message after export
- open_file()             # Open file with default app (cross-platform)
- open_folder()           # Open folder in file manager (cross-platform)

# Variables
- console                 # Global Rich Console instance
```

### `workflows.py` - Interactive Workflow Components
**What lives here**: Reusable interactive workflow building blocks

```python
# File Management
- select_input_files()          # Interactive file picker
- get_output_filename()         # Smart output name generator

# Transcription
- check_transcripts()           # Check for missing transcripts
- configure_transcription()     # Transcription settings dialog

# Settings & Menus
- settings_menu()               # Ignored words settings
- search_settings_menu()        # Search settings (padding, etc.)
- post_export_menu()            # Post-export action menu
```

### `commands.py` - Command Execution Logic
**What lives here**: Core VoxGrep command execution

```python
# Transcription
- run_transcription_sphinx()    # Execute Sphinx transcription
- run_transcription_whisper()   # Execute Whisper transcription

# Analysis
- calculate_ngrams()            # Calculate and filter n-grams

# Search
- run_voxgrep_search()          # Execute VoxGrep search with progress

# Main Entry
- execute_args()                # Main command execution dispatcher
```

### `interactive.py` - Main Interactive Wizard
**What lives here**: The main interactive mode orchestration

```python
# Main Functions
- interactive_mode()            # Main interactive entry point
- handle_search_workflow()      # Search workflow orchestrator
- create_default_args()         # Create default arguments namespace
- get_default_output_name()     # Generate safe output filename
```

### `ngrams.py` - N-gram Interactive Analysis
**What lives here**: Complete n-gram analysis workflow

```python
# Selection Phase
- ngram_selection_phase()           # Main selection coordinator
- select_ngrams_single_mode()       # Single-select UI
- select_ngrams_multi_mode()        # Multi-select UI

# Action Phase
- ngram_action_phase()              # Action menu workflow

# Main Entry
- interactive_ngrams_workflow()     # Main n-gram workflow
```

### `main.py` - Entry Point (Refactored)
**What lives here**: Just the entry point and argument parsing

```python
# Main Functions
- main()                        # CLI entry point
- create_argument_parser()      # ArgumentParser factory
```

## Common Migration Patterns

### Pattern 1: Platform-Specific File Opening

**Before:**
```python
if sys.platform == 'win32':
    os.startfile(filepath)
elif sys.platform == 'darwin':
    subprocess.call(('open', filepath))
else:
    subprocess.call(('xdg-open', filepath))
```

**After:**
```python
from voxgrep.cli.ui import open_file
open_file(filepath)
```

### Pattern 2: N-gram Calculation

**Before:**
```python
# Embedded in execute_args() with complex filtering logic
if args.ngrams > 0:
    grams = get_ngrams(args.inputfile, args.ngrams)
    # ... 30+ lines of filtering and display ...
```

**After:**
```python
from voxgrep.cli.commands import calculate_ngrams
from voxgrep.cli.ui import print_ngrams_table

most_common, filtered = calculate_ngrams(
    args.inputfile, 
    args.ngrams,
    ignored_words,
    use_filter
)
print_ngrams_table(most_common, filtered, args.ngrams)
```

### Pattern 3: Interactive Search

**Before:**
```python
# Deeply nested in interactive_mode() at line ~268
if task == "search":
    # ... 135 lines of search workflow ...
```

**After:**
```python
from voxgrep.cli.interactive import handle_search_workflow

if task == "search":
    if not handle_search_workflow(args):
        break
```

## Import Quick Reference

### For External Code

If you're importing VoxGrep CLI components in external code:

```python
# Banner
from voxgrep.cli.ui import print_banner

# Interactive Mode
from voxgrep.cli.interactive import interactive_mode

# Command Execution
from voxgrep.cli.commands import execute_args, run_voxgrep_search

# N-gram Workflows
from voxgrep.cli.ngrams import interactive_ngrams_workflow

# Workflows
from voxgrep.cli.workflows import (
    select_input_files,
    settings_menu,
    post_export_menu
)

# UI Utilities
from voxgrep.cli.ui import (
    console,
    open_file,
    open_folder,
    print_success_panel
)
```

### For VoxGrep Internal Code

All CLI modules now import from sibling modules:

```python
# Within CLI modules
from .ui import console, print_banner
from .workflows import select_input_files
from .commands import execute_args
```

## Testing Migration

### Old Test Structure
```python
# Tests that imported everything from main.py
from voxgrep.cli.main import interactive_mode, execute_args, print_banner
```

### New Test Structure
```python
# Tests can now target specific modules
from voxgrep.cli.ui import print_banner
from voxgrep.cli.interactive import interactive_mode
from voxgrep.cli.commands import execute_args

# Or test smaller units
from voxgrep.cli.workflows import select_input_files
from voxgrep.cli.ngrams import select_ngrams_single_mode
```

## Benefits for Developers

### Easier Testing
```python
# Before: Had to test 1000+ line function
# After: Test focused 50-100 line functions

def test_open_file():
    """Test can now mock platform independently"""
    from voxgrep.cli.ui import open_file
    # Test just this function
    
def test_calculate_ngrams():
    """Test n-gram calculation in isolation"""
    from voxgrep.cli.commands import calculate_ngrams
    # No UI dependencies
```

### Easier Extension
```python
# Want to add a new workflow?
# Just create a function in workflows.py

def my_custom_workflow(args):
    """New custom workflow"""
    # Reuse existing components
    from .ui import console
    from .workflows import select_input_files
    
    files = select_input_files()
    console.print(f"Processing {len(files)} files...")
```

### Clearer Dependencies
```python
# Each module declares exactly what it needs
# No hidden dependencies in 1000-line files

# workflows.py only needs:
import questionary
from .ui import console, open_file

# commands.py only needs:
from ..core import logic as voxgrep
from ..core import transcriber
from .ui import console, print_ngrams_table
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'voxgrep.cli.ui'"

**Solution**: Make sure you're running from the correct directory
```bash
cd voxgrep  # Project root
python -m voxgrep.cli.main
```

### "AttributeError: module 'voxgrep.cli.main' has no attribute 'interactive_mode'"

**Solution**: Update your imports
```python
# Old
from voxgrep.cli.main import interactive_mode

# New
from voxgrep.cli.interactive import interactive_mode
```

### Tests failing after refactoring

**Solution**: Update test imports to use new module structure
```python
# Update imports in test files
from voxgrep.cli.commands import execute_args
from voxgrep.cli.interactive import interactive_mode
```

---

**Need help?** Check the [CLI_REFACTORING.md](./CLI_REFACTORING.md) for the full refactoring summary.
